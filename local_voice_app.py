# ==============================================================================
#  LOCAL AI VOICE STUDIO  (100% Offline / Free / No GPU / No API Key)
#  Powered by Kokoro-82M  |  Tech Tips Dhanwala MH
#
#  Normal way to start:  double-click "START HERE.bat"
#  Manual way:           env\Scripts\python.exe local_voice_app.py
#
#  Verified against: kokoro 0.9.4, gradio 5.x, soundfile 0.14, torch 2.x (CPU)
#  NOTE: requirements.txt pins gradio to <6 on purpose. The UI here only uses
#  calls that exist in both 5 and 6, but 5.x is the version actually tested.
# ==============================================================================

import os
import re
import sys
import time
import socket
import logging
import warnings
import datetime
import subprocess
import webbrowser
import collections
import urllib.request

# Keep everything local and quiet: no telemetry, no phone-home.
os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Torch prints harmless deprecation warnings on load, and the model downloader
# prints a token notice. Hide all of it so the terminal stays readable on camera.
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="torch")
warnings.filterwarnings("ignore", message=".*unauthenticated requests.*")
warnings.filterwarnings("ignore", message=".*dropout option adds dropout.*")
for _noisy in ("huggingface_hub", "urllib3", "filelock", "httpx"):
    logging.getLogger(_noisy).setLevel(logging.ERROR)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(APP_DIR, "output")
PORT = 7860

REPO_ID = "hexgrad/Kokoro-82M"
SAMPLE_RATE = 24000          # Kokoro v1.0 always renders 24 kHz mono
CHUNK_CHARS = 280            # keep each synthesis chunk short and stable

VOICES = {
    "af_heart    -  US Female, warm documentary":  "af_heart",
    "af_bella    -  US Female, expressive":        "af_bella",
    "af_nicole   -  US Female, soft audiobook":    "af_nicole",
    "am_adam     -  US Male, deep commercial":     "am_adam",
    "am_michael  -  US Male, podcast narrator":    "am_michael",
    "bf_emma     -  UK Female, crisp newsreader":  "bf_emma",
    "bf_isabella -  UK Female, calm and elegant":  "bf_isabella",
    "bm_george   -  UK Male, classic British":     "bm_george",
    "bm_lewis    -  UK Male, deep authoritative":  "bm_lewis",
}


def line(msg):
    print(msg, flush=True)


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def model_is_cached():
    """True if the model + voices were already fetched by the setup file."""
    home = os.path.expanduser("~")
    roots = [os.path.join(home, ".cache", "huggingface", "hub")]
    hf_home = os.environ.get("HF_HOME")
    if hf_home:
        roots.append(os.path.join(hf_home, "hub"))
    for root in roots:
        if os.path.isdir(os.path.join(root, "models--hexgrad--Kokoro-82M")):
            return True
    return False


# ------------------------------------------------------------------ text prep
def split_into_chunks(text, max_len=CHUNK_CHARS):
    """Break a script into speakable chunks and keep paragraph pauses.

    Kokoro renders one chunk at a time. Without this, a long script is sent
    as a single block, which is slower and drifts in prosody.

    Returns a list of (chunk_text, pause_after_seconds).
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    chunks = []

    for para in re.split(r"\n\s*\n", text):
        para = " ".join(para.split())
        if not para:
            continue

        buf = ""
        for sent in re.split(r"(?<=[.!?:;])\s+", para):
            # A single monster sentence still has to be cut somewhere.
            while len(sent) > max_len:
                cut = sent.rfind(", ", 0, max_len)
                if cut < max_len // 2:
                    cut = sent.rfind(" ", 0, max_len)
                if cut <= 0:
                    # -1, because head below takes sent[:cut + 1]. Using max_len
                    # here would emit max_len + 1 characters and break the cap.
                    cut = max_len - 1
                head, sent = sent[:cut + 1].strip(), sent[cut + 1:].strip()
                if buf:
                    chunks.append((buf, 0.22))
                    buf = ""
                if head:
                    chunks.append((head, 0.22))

            if not buf:
                buf = sent
            elif len(buf) + len(sent) + 1 <= max_len:
                buf += " " + sent
            else:
                chunks.append((buf, 0.22))
                buf = sent

        if buf:
            chunks.append((buf, 0.55))   # longer pause between paragraphs

    return chunks


def build_audio(pipeline, text, voice, speed):
    """Render text into one numpy waveform, chunk by chunk."""
    import numpy as np

    chunks = split_into_chunks(text)
    if not chunks:
        raise ValueError("There is nothing speakable in that text.")

    # Load the voice file ONCE. Kokoro reloads it on every call otherwise,
    # which slows long scripts down a lot.
    voice_pack = pipeline.load_voice(voice)

    pieces = []
    for chunk_text, pause in chunks:
        produced = False
        for _, _, audio in pipeline(chunk_text, voice=voice_pack, speed=speed,
                                    split_pattern=None):
            arr = (audio.detach().cpu().numpy()
                   if hasattr(audio, "detach") else np.asarray(audio))
            pieces.append(arr.astype("float32").reshape(-1))
            produced = True
        if not produced:
            continue
        if pause > 0:
            pieces.append(np.zeros(int(SAMPLE_RATE * pause), dtype="float32"))

    if not pieces:
        raise ValueError("The model returned no audio for that text.")

    wav = np.concatenate(pieces)
    peak = float(np.max(np.abs(wav))) if wav.size else 0.0
    if peak > 0:
        wav = wav / peak * 0.95     # keep it at a usable, non-clipping level
    return wav, len(chunks)


# ------------------------------------------------------------------------ UI
def build_ui():
    import gradio as gr

    with gr.Blocks(title="Local AI Voice Studio") as demo:
        gr.Markdown(
            "# Local AI Voice Studio\n"
            "**Runs 100% on this PC. No internet. No API key. No GPU.**  \n"
            "Powered by Kokoro-82M - about 330 MB, runs on a normal CPU."
        )

        with gr.Row():
            with gr.Column(scale=3):
                text_input = gr.Textbox(
                    label="Your script",
                    placeholder="Paste your voiceover script here...",
                    lines=9,
                    value=("In a world driven by artificial intelligence, you don't need "
                           "expensive cloud subscriptions. This studio quality voice is "
                           "running 100 percent offline, right on my laptop."),
                )
                voice_dropdown = gr.Dropdown(
                    choices=list(VOICES.keys()),
                    value=list(VOICES.keys())[0],
                    label="Voice",
                )
                speed = gr.Slider(0.7, 1.4, value=1.0, step=0.05,
                                  label="Speaking speed")
                btn = gr.Button("GENERATE VOICE  (OFFLINE)",
                                variant="primary", size="lg")

            with gr.Column(scale=2):
                audio_output = gr.Audio(label="Your voiceover", type="filepath")
                stats_box = gr.Textbox(label="Benchmark", lines=2, max_lines=3,
                                       interactive=False)
                file_box = gr.Textbox(label="Saved file", lines=1, max_lines=1,
                                      interactive=False)
                gr.Markdown(
                    "Files are saved in the **output** folder next to this app, "
                    "ready to drag straight into CapCut or Premiere Pro."
                )

        btn.click(fn=generate_speech,
                  inputs=[text_input, voice_dropdown, speed],
                  outputs=[audio_output, stats_box, file_box])

        with gr.Accordion("Which voice should I pick?", open=False):
            gr.Markdown(
                "- **am_adam** - deep and punchy. Tech reviews, faceless video essays.\n"
                "- **af_heart** - warm and natural. Documentary and story narration.\n"
                "- **bm_george** - classic British narrator. Explainer channels.\n"
                "- **bf_emma** - crisp newsreader. Corporate and news style.\n\n"
                "Tip: generate the same line in two voices, then pick the one that "
                "fits your edit."
            )

    return demo


def generate_speech(text, voice_label, speed):
    import gradio as gr
    import numpy as np
    import soundfile as sf

    text = (text or "").strip()
    if not text:
        raise gr.Error("Type something in the script box first.")

    if not model_is_cached():
        raise gr.Error(
            "The voice model is not on this PC yet. Run the setup file once "
            "while you have internet - after that it works offline forever."
        )

    voice = VOICES.get(voice_label, "af_heart")
    pipeline = PIPELINES["b" if voice.startswith("b") else "a"]

    started = time.time()
    try:
        wav, n_chunks = build_audio(pipeline, text, voice, float(speed))
    except Exception as exc:                            # noqa: BLE001
        raise gr.Error("Could not generate audio: %s" % exc)

    elapsed = time.time() - started
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = "%s_%s.wav" % (stamp, voice)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    sf.write(path, wav, SAMPLE_RATE)

    audio_len = len(wav) / float(SAMPLE_RATE)
    speedup = (audio_len / elapsed) if elapsed > 0 else 0
    stats = ("%s  |  %.1fs of audio generated in %.1fs  |  %.1fx real time  |  "
             "%d chunks  |  %d Hz mono"
             % (voice, audio_len, elapsed, speedup, n_chunks, SAMPLE_RATE))

    line("  -> %s  (%.1fs of audio in %.1fs)" % (filename, audio_len, elapsed))
    return path, stats, path


# ------------------------------------------------------- launching the window
def find_app_browser():
    """Return a browser that can run in chromeless "app mode".

    Edge ships with Windows 10 and 11, so it is almost always present. Chrome
    is the fallback. Both support --app=, which opens a normal window with no
    address bar and no tabs - it looks and behaves like a desktop application.
    """
    for vendor in (("Microsoft", "Edge", "Application", "msedge.exe"),
                   ("Google", "Chrome", "Application", "chrome.exe")):
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if not base:
                continue
            path = os.path.join(base, *vendor)
            if os.path.exists(path):
                return path
    return None


# How the studio knows the app window is still open. "proc" is the launcher
# stub (it exits within a second or two, so it cannot be waited on). "port" is
# a private localhost debugging port the browser keeps open for exactly as long
# as our window exists - that is the signal we actually trust.
Window = collections.namedtuple("Window", "proc port")


def open_app_window(url):
    """Open the studio as a chromeless app window.

    --app= gives a normal window with no address bar and no tabs, which is what
    makes it look like an installed program instead of a web page.
    """
    exe = find_app_browser()
    if not exe:
        webbrowser.open(url)
        return None

    # A dedicated profile keeps the window standalone: no extensions, no
    # existing session, no "restore pages" prompt, and a predictable start.
    profile = os.path.join(APP_DIR, "app-window")
    marker = None
    try:
        os.makedirs(profile, exist_ok=True)
        marker = os.path.join(profile, "DevToolsActivePort")
    except Exception:
        profile = None

    # The browser writes DevToolsActivePort on launch but does NOT delete it on
    # exit (verified). So whatever is on disk right now may describe a browser
    # that is long gone. Remember it, then clear it, so that the value we read
    # afterwards can only have come from the launch we are about to do.
    previous = _peek_devtools_port(marker)
    if marker and os.path.exists(marker):
        try:
            os.remove(marker)
        except Exception:
            marker = None

    # These flags are not decoration - each one was measured on a real Edge:
    #   --disable-sync            without it Edge opens a second window called
    #                             "We are now syncing your browser", which is
    #                             user-visible and looks broken on camera
    #   --disable-extensions      without it Edge loads 5 built-in extension
    #                             background pages that keep the browser alive
    #                             after our window closes, so the studio would
    #                             never notice the user quitting
    #   --disable-background-mode same reason: no "keep running in background"
    #   --disable-component-update no update nags on a throwaway profile
    args = [exe, "--app=" + url, "--no-first-run",
            "--no-default-browser-check",
            "--disable-sync",
            "--disable-extensions",
            "--disable-background-mode",
            "--disable-component-update",
            "--window-size=1180,860"]
    if profile:
        args.append("--user-data-dir=" + profile)
    if marker:
        # Port 0 = let the browser choose a free port. It listens on 127.0.0.1
        # only, and only while the studio is open.
        args.append("--remote-debugging-port=0")

    try:
        proc = subprocess.Popen(args)
    except Exception:
        webbrowser.open(url)
        return None

    port = _read_devtools_port(marker, time.time() + 20) if marker else None

    # If no fresh port appeared, a browser left over from an earlier run is
    # still alive and took the window instead of us getting a new one. Its old
    # port is still answering, so watch that: otherwise the studio would sit
    # there forever and never notice the user closing the window.
    if port is None and previous and _window_still_open(previous):
        port = previous

    return Window(proc=proc, port=port)


def _peek_devtools_port(marker):
    """Read a port number if the file happens to hold one. Never waits."""
    if not marker:
        return None
    try:
        with open(marker, "r", encoding="utf-8", errors="replace") as fh:
            first = fh.readline().strip()
        return int(first) if first.isdigit() else None
    except Exception:
        return None


def _read_devtools_port(marker, deadline):
    """Wait for the browser to publish its debugging port, or give up."""
    while time.time() < deadline:
        port = _peek_devtools_port(marker)
        if port is not None:
            return port
        time.sleep(0.2)
    return None


def _window_still_open(port):
    """True while the browser hosting our window answers on its debug port."""
    try:
        with urllib.request.urlopen(
                "http://127.0.0.1:%d/json/version" % port, timeout=2.0):
            return True
    except Exception:
        return False


def wait_until_window_closes(window):
    """Block until the user closes the app window.

    Returns True when the window really closed, and False when there was no
    reliable signal and we are simply staying alive. Three missed polls in a
    row (about six seconds) are required before believing the window is gone,
    so a momentary hiccup can never stop the studio mid-sentence.
    """
    if window is None:
        _idle_forever()          # no browser at all, so nothing to watch
        return False
    if not window.port:
        line("")
        line("  This window cannot tell when you close it, so it stays open.")
        line("  Close this black window to stop the studio.")
        _idle_forever()
        return False

    misses = 0
    while True:
        try:
            time.sleep(2.0)
        except KeyboardInterrupt:
            return False
        if _window_still_open(window.port):
            misses = 0
            continue
        misses += 1
        if misses >= 3:
            return True


def _idle_forever():
    while True:
        try:
            time.sleep(3600)
        except KeyboardInterrupt:
            return


# ---------------------------------------------------------------------- main
PIPELINES = {}


def main():
    line("=" * 68)
    line("  LOCAL AI VOICE STUDIO  -  100% OFFLINE  -  Tech Tips Dhanwala MH")
    line("=" * 68)

    if port_in_use(PORT):
        line("")
        line("  The studio is ALREADY RUNNING - opening it for you.")
        line("  (To stop it, close the other studio window.)")
        line("")
        open_app_window("http://127.0.0.1:%d" % PORT)
        return 0

    if not model_is_cached():
        line("")
        line("  NOTE: this is the first run, so the voice model downloads now")
        line("  (about 330 MB, one time only). After this it is fully offline.")
        line("")

    line("")
    line("  Starting up. This takes about 40 to 60 seconds, because it loads")
    line("  a real AI model into memory. It is NOT frozen - please wait.")
    line("")

    started_all = time.time()

    line("Loading the AI engine...")
    from kokoro import KPipeline
    line("  [ok] engine loaded           (%.1fs)" % (time.time() - started_all))

    # Kokoro's KPipeline auto-selects CUDA whenever a GPU is present. We force
    # CPU deliberately. This app promises "no graphics card needed", and if it
    # silently used a GPU on some machines then the on-camera speed test would
    # not be reproducible for anyone without one. Forcing CPU makes the promise
    # true and the benchmark honest.
    #
    # Measured on the real install: pip gives Windows a CPU-only torch
    # (2.14.0+cpu, torch.version.cuda is None), so a GPU could not be used even
    # if we asked. The pin is still worth keeping - it guarantees CPU on any
    # machine, including one where somebody has installed a CUDA build by hand.
    try:
        import torch as _torch
        _cuda_present = bool(_torch.cuda.is_available())
        _cuda_built = _torch.version.cuda is not None
    except Exception:
        _cuda_present = False
        _cuda_built = False

    line("")
    line("Running on CPU only - no graphics card used.")
    if _cuda_present:
        line("  (a CUDA GPU is present but is deliberately left unused)")
    elif not _cuda_built:
        line("  (the engine installed here has no GPU support at all, so every")
        line("   PC gets exactly the same result - graphics card or not)")
    else:
        line("  (this PC has no CUDA GPU, and it does not need one)")
    line("")

    t0 = time.time()
    PIPELINES["a"] = KPipeline(lang_code="a", repo_id=REPO_ID, device="cpu")
    line("  [ok] American voices ready   (%.1fs)" % (time.time() - t0))

    t1 = time.time()
    PIPELINES["b"] = KPipeline(lang_code="b", repo_id=REPO_ID, device="cpu")
    line("  [ok] British voices ready    (%.1fs)" % (time.time() - t1))

    line("Model loaded! Starting local web interface...")

    demo = build_ui()
    icon = os.path.join(APP_DIR, "voice.ico")

    line("")
    line("Studio ready in %.0f seconds." % (time.time() - started_all))
    line("")

    # prevent_thread_lock returns control here immediately after the server
    # starts, so we can open the app window ourselves and then watch it. That
    # way closing the window really stops the studio, instead of leaving a
    # server running invisibly in the background holding the port.
    demo.queue().launch(
        server_name="127.0.0.1",
        server_port=PORT,
        inbrowser=False,
        prevent_thread_lock=True,
        favicon_path=icon if os.path.exists(icon) else None,
    )

    line("Opening the studio window...")
    window = open_app_window("http://127.0.0.1:%d" % PORT)
    if window is None:
        line("  (no Edge or Chrome found, so it opened in your default browser)")
    line("")
    line("Closing the studio window stops the studio.")
    line("")

    if wait_until_window_closes(window):
        line("")
        line("  App window closed. Shutting the studio down.")
        line("  You can close this black window too.")

    # The Gradio server lives in its own thread, so exit hard: the studio must
    # never linger invisibly and keep holding the port after the window is gone.
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    sys.exit(main())
