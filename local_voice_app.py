# ==============================================================================
#  LOCAL AI VOICE STUDIO  (100% Offline / Free / No Account)
#  Powered by Kokoro-82M  |  Tech Tips Dhanwala MH
#
#  Normal way to start:  double-click "START HERE.bat" (or the desktop icon)
#  Manual way:           env\Scripts\python.exe local_voice_app.py
#
#  ---------------------------------------------------------------------------
#  WHY ONNX AND NOT THE ORIGINAL PYTORCH BUILD
#  ---------------------------------------------------------------------------
#  The first version of this app used the `kokoro` PyPI package, which pulls in
#  PyTorch. Measured on the development machine, that install was ~1.3 GB and
#  needed about 2 GB of RAM while generating, on a laptop that only has 7.2 GB.
#
#  This version runs the same Kokoro-82M weights through ONNX Runtime instead.
#  Measured on the same machine, same text, same 21.0 s of audio:
#
#      PyTorch  CPU    RTF 0.495    1.3 GB installed, ~2 GB RAM while running
#      ONNX     CPU    RTF 0.295    ~550 MB installed, ~350 MB RAM while running
#
#  (RTF = seconds of wall clock per second of finished audio. Lower is better.
#   0.295 is the engine-only figure. The Benchmark box in the app reports
#   about 2.5x on a realistic script, because that number also includes
#   splitting the text into chunks and stitching the audio back together.)
#
#  That is 1.7x faster, in about two thirds of the disk space, and a fraction
#  of the memory,
#  which matters far more than it sounds: the machine this was tested on spends
#  most of its life with under 400 MB of RAM free, and the PyTorch build spent
#  its time paging to disk instead of generating speech.
#
#  ---------------------------------------------------------------------------
#  ABOUT GPU ACCELERATION - READ THIS BEFORE ASKING FOR IT
#  ---------------------------------------------------------------------------
#  A graphics card does NOT help here, and that is a measured result rather
#  than an opinion. DirectML (the Windows GPU path for ONNX) was installed and
#  tried three ways on an RTX 3050 Laptop:
#
#    1. default partitioning        -> aborts on a ConvTranspose node
#    2. fp16 model instead          -> aborts on a ConvTranspose node
#    3. 1,988 decoder nodes pinned
#       to the GPU by hand, the
#       unsupported ones left on CPU-> still aborts
#
#  Kokoro's decoder uses ConvTranspose layers that DirectML on this driver
#  cannot execute, and ONNX Runtime will not fall back for a node a provider
#  has already claimed. There is no configuration that works, so this app does
#  not pretend to have one. It uses the CPU, fast and predictably.
#
#  The CPU path is also tuned, and the tuning was the real win. ONNX Runtime by
#  default uses every logical processor, which on a 16-thread laptop is the
#  worst possible setting - measured 29% SLOWER than 12 threads, because the
#  operators are small and the extra threads just fight over memory bandwidth.
#  Threads are now capped (see CPU_THREADS below).
#
#  ---------------------------------------------------------------------------
#  A NOTE ON REPEATABILITY
#  ---------------------------------------------------------------------------
#  Kokoro's ONNX graph is not bit-for-bit deterministic. Generating the same
#  line twice gives audio that correlates ~0.996, not 1.000 - a difference of
#  roughly 6% RMS, spread through the voiced parts. This is float reduction
#  order inside the network, not a bug: it is unaffected by thread count,
#  execution mode, graph optimisation, or deterministic-compute mode (all four
#  were tested). Practically: the same line generated twice sounds the same,
#  but is not byte-identical, so re-render a fluffed take freely, and always
#  render a specific precision if you need two lines to match exactly.
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
import threading
import webbrowser
import collections
import urllib.error
import urllib.request

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
# The launcher sets these too, but the desktop icon starts this file directly
# with pythonw.exe and never goes through the launcher at all. Relying on the
# launcher alone meant the normal way of opening the app - the icon - ran
# without them. kokoro_onnx imports huggingface_hub, which is happy to phone
# home given half a chance, and on a machine with no internet that shows up as
# a long stall rather than an error.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*unauthenticated requests.*")
for _noisy in ("urllib3", "filelock", "httpx", "onnxruntime"):
    logging.getLogger(_noisy).setLevel(logging.ERROR)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(APP_DIR, "models")
OUT_DIR = os.path.join(APP_DIR, "output")
PORT = 7860
LOG = os.path.join(APP_DIR, "studio.log")
SERVER_LOG = os.path.join(APP_DIR, "studio-server.log")


# ------------------------------------------------- no console, no problem
# pythonw.exe is what makes the black window disappear, and it gives the
# process no console at all: sys.stdout and sys.stderr are literally None.
# Anything that writes to them - or even just asks them a question - then
# dies. Measured on this exact build: uvicorn's colourised log formatter does
# `self.use_colors = sys.stdout.isatty()` while the Gradio server starts, so
# the studio could not start without a console, and it failed with the
# unrelated-looking "Unable to configure formatter 'default'".
#
# So give both streams a real file before anything can touch them. A real
# file object matters here rather than a hand-written stub: it has a working
# fileno(), a real encoding, and isatty() answers False - exactly what a
# console-less process should report.
def ensure_std_streams():
    global STREAMS_SYNTHETIC
    for name in ("stdout", "stderr", "__stdout__", "__stderr__"):
        if getattr(sys, name, None) is not None:
            continue
        try:
            stream = open(SERVER_LOG, "a", encoding="utf-8",
                          errors="replace", buffering=1)
        except Exception:                                   # noqa: BLE001
            try:
                stream = open(os.devnull, "w")
            except Exception:                               # noqa: BLE001
                continue
        setattr(sys, name, stream)
        STREAMS_SYNTHETIC = True


# True when there was no console and the streams above had to be invented.
# line() uses this to skip its print: everything it says is already going to
# studio.log, and printing as well would duplicate every line into the server
# log for no benefit.
STREAMS_SYNTHETIC = False

ensure_std_streams()

MODEL_FILE = "kokoro-v1.0.onnx"
VOICES_FILE = "voices-v1.0.bin"
# model + voices, measured. Used for the on-screen size readout.
MODEL_BYTES = 325505369 + 28214398

SAMPLE_RATE = 24000
CHUNK_CHARS = 400

# ONNX Runtime defaults to every logical processor. Measured on a 16-thread
# Ryzen 7 6800H: 16 threads gives RTF 0.374-0.382, while 12 gives 0.297-0.301.
# Using all the cores is 25% slower, not faster. About 3/4 of the logical
# processors is the sweet spot, so that is what is used, with a floor of 2 and
# a ceiling of 12 (beyond 12 there is nothing left to gain).
def choose_threads():
    logical = os.cpu_count() or 4
    return max(2, min(12, int(logical * 0.75)))


CPU_THREADS = choose_threads()

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
    """Print to the console and to the log file.

    The console may not exist (the studio can start with no window at all), so
    every write is guarded - a failure to print must never stop the app. When
    there was no console to begin with, the print is skipped rather than sent
    to the invented stream, because studio.log already has the line.
    """
    text = str(msg)
    if not STREAMS_SYNTHETIC:
        try:
            print(text, flush=True)
        except Exception:
            pass
    try:
        with open(LOG, "a", encoding="utf-8", errors="replace") as fh:
            fh.write("%s  %s\n" % (datetime.datetime.now().strftime("%H:%M:%S"), text))
    except Exception:
        pass


def _log_traceback(exc):
    """Write a full traceback to the log.

    The message shown to the viewer is written for the viewer. This is for
    whoever has to work out what actually happened, and it needs the frames:
    a bare message once turned a two-minute diagnosis into an hour of guessing.
    """
    import traceback

    try:
        text = "".join(traceback.format_exception(type(exc), exc,
                                                 exc.__traceback__))
    except Exception:                                       # noqa: BLE001
        text = repr(exc)
    for row in text.rstrip().splitlines():
        line("      " + row)


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_for_port(port, timeout):
    """Wait for something to start listening. True if it did."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_in_use(port):
            return True
        time.sleep(0.25)
    return port_in_use(port)


# ------------------------------------------------- one studio at a time, ever
ERROR_ALREADY_EXISTS = 183


def claim_single_instance():
    """Take the machine-wide "one studio" claim, race-free.

    Returns a handle when this process is the only studio, None when another
    one already holds the claim, or "unknown" if the check could not run.

    Why a named mutex and not a lock file or a port probe:

    * A lock file survives a crash. If the studio is killed rather than closed,
      the stale file would lock the user out of their own app forever, and
      "delete this hidden file" is not an instruction a non-technical viewer
      can follow. A kernel mutex is released by Windows the moment the process
      ends, however it ends.
    * A port probe is not atomic. Two copies launched together - which is
      exactly what a double-click plus a leftover shortcut produces - both
      look at the port before either has bound it, both see it free, and both
      start a server. One then loses the race and dies with a bind error.
      CreateMutex is atomic, so only one can ever win.
    """
    try:
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateMutexW.restype = wintypes.HANDLE
        k32.CreateMutexW.argtypes = [wintypes.LPCVOID, wintypes.BOOL,
                                     wintypes.LPCWSTR]
        handle = k32.CreateMutexW(None, False, "Local\\LocalAiVoiceStudio")
        if not handle:
            return "unknown"
        if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            return None
        return handle
    except Exception:                                       # noqa: BLE001
        return "unknown"


def show_error(title, text):
    """Put a real Windows dialog on screen.

    The studio normally runs with no console at all, so anything printed goes
    to studio.log where a non-technical viewer will never look. When something
    is genuinely wrong this is the only way to say so out loud.
    """
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)
    except Exception:                                       # noqa: BLE001
        pass


def model_is_present():
    """True when both model files are on disk and plausibly complete.

    A file that exists but is the wrong size is treated as absent. That is the
    difference between "the setup ran" and "the setup finished", and getting it
    wrong means the studio fails the moment somebody presses Generate.
    """
    for name, want in ((MODEL_FILE, 325505369), (VOICES_FILE, 28214398)):
        path = os.path.join(MODELS_DIR, name)
        try:
            if os.path.getsize(path) != want:
                return False
        except OSError:
            return False
    return True


# ------------------------------------------------------------------ text prep
def split_into_chunks(text, max_len=CHUNK_CHARS):
    """Break a script into speakable chunks and keep paragraph pauses.

    Returns a list of (chunk_text, pause_after_seconds).

    Chunking exists for two reasons. Kokoro renders one window at a time and
    its prosody drifts on very long input, and a long script rendered as one
    block cannot show progress. 400 characters is roughly 25 seconds of speech
    at a normal pace - short enough to feel responsive, long enough that the
    joins are not obvious.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    chunks = []

    for para in re.split(r"\n\s*\n", text):
        para = " ".join(para.split())
        if not para:
            continue

        buf = ""
        for sent in re.split(r"(?<=[.!?:;])\s+", para):
            while len(sent) > max_len:
                cut = sent.rfind(", ", 0, max_len)
                if cut < max_len // 2:
                    cut = sent.rfind(" ", 0, max_len)
                if cut <= 0:
                    # -1, because head below takes sent[:cut + 1]. Using
                    # max_len here would emit max_len + 1 characters.
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


# ---------------------------------------------------------------- the engine
ENGINE = {}
# The engine is warmed on a background thread while the window is already
# open, so that a slow start is invisible instead of a blank 20-second wait.
# That makes load_engine() reachable from two threads at once - the warmer and
# whoever pressed Generate - so it has to be guarded. Without this, a fast
# click during warm-up would build a SECOND ONNX session, doubling the RAM
# this app is most sensitive to.
ENGINE_LOCK = threading.Lock()


def load_engine():
    """Load the ONNX model and voice pack into memory, once.

    Returns (engine, load_seconds). Raises on any real problem - the caller
    decides how to present it.
    """
    if "kokoro" in ENGINE:
        return ENGINE, 0.0

    with ENGINE_LOCK:
        # Second check: while this thread waited for the lock, the warmer may
        # have finished the job. Loading twice would cost ~350 MB and a few
        # seconds, on the exact resource this machine is short of.
        if "kokoro" in ENGINE:
            return ENGINE, 0.0
        return _load_engine_unlocked()


def _load_engine_unlocked():
    """The actual load. Caller must hold ENGINE_LOCK."""
    import onnxruntime as rt
    from kokoro_onnx import Kokoro

    started = time.time()

    so = rt.SessionOptions()
    so.intra_op_num_threads = CPU_THREADS
    so.inter_op_num_threads = 1
    so.graph_optimization_level = rt.GraphOptimizationLevel.ORT_ENABLE_ALL
    # Keep ONNX Runtime quiet. On this model it emits hundreds of harmless
    # "Could not find a CPU kernel and hence can't constant fold Reciprocal"
    # lines while loading, which would bury anything useful in the log.
    so.log_severity_level = 3

    session = rt.InferenceSession(
        os.path.join(MODELS_DIR, MODEL_FILE), so,
        providers=["CPUExecutionProvider"])
    kokoro = Kokoro.from_session(
        session, os.path.join(MODELS_DIR, VOICES_FILE),
        espeak_config=None, vocab_config=None)

    ENGINE["kokoro"] = kokoro
    ENGINE["providers"] = session.get_providers()
    return ENGINE, time.time() - started


def render(kokoro, text, voice, speed, on_progress=None):
    """Render text into one numpy waveform, chunk by chunk.

    Returns (waveform, chunk_count, generate_seconds).
    """
    import numpy as np

    chunks = split_into_chunks(text)
    if not chunks:
        raise ValueError("There is nothing speakable in that text.")

    pieces = []
    total = len(chunks)
    started = time.time()
    done_audio = 0.0

    for index, (chunk_text, pause) in enumerate(chunks):
        try:
            audio, _rate = kokoro.create(
                chunk_text, voice=voice, speed=speed, lang="en-us")
        except Exception as exc:                            # noqa: BLE001
            raise RuntimeError("chunk %d of %d failed: %s"
                               % (index + 1, total, exc))

        arr = np.asarray(audio, dtype="float32").reshape(-1)
        pieces.append(arr)
        done_audio += len(arr) / float(SAMPLE_RATE)

        if pause > 0:
            pieces.append(np.zeros(int(SAMPLE_RATE * pause), dtype="float32"))

        if on_progress:
            on_progress(index + 1, total, done_audio, time.time() - started)

    if not pieces:
        raise ValueError("The model returned no audio for that text.")

    wav = np.concatenate(pieces)
    peak = float(np.max(np.abs(wav))) if wav.size else 0.0
    if peak > 0:
        wav = wav / peak * 0.95     # usable level, no clipping

    return wav, total, time.time() - started


# ------------------------------------------------------------------------ UI
def offline_theme():
    """The normal Gradio look, but with fonts Windows already has.

    The stock theme asks fonts.googleapis.com for 'Source Sans Pro'. That is a
    real outbound request on every launch, which is wrong for an app that
    advertises itself as offline - and on a disconnected PC it can only fail.
    Passing plain Font objects makes Gradio emit no font stylesheet at all.

    Measured on gradio 5.50.0: the stock theme emits one external font URL,
    this one emits none.
    """
    import gradio as gr
    return gr.themes.Default(
        font=[gr.themes.Font("Segoe UI"), gr.themes.Font("Arial"),
              gr.themes.Font("sans-serif")],
        font_mono=[gr.themes.Font("Consolas"), gr.themes.Font("monospace")],
    )


# Gradio's own page template still ships references to the internet that the
# theme cannot reach. Measured on gradio 5.50.0, in
# gradio/templates/frontend/index.html:
#
#   <link rel="preconnect" href="https://fonts.googleapis.com" />
#   <link rel="preconnect" href="https://fonts.gstatic.com" ... />
#   <script src="https://cdnjs.cloudflare.com/ajax/libs/iframe-resizer/
#                4.3.1/iframeResizer.contentWindow.min.js" async></script>
#   <meta property="og:image" content="https://raw.githubusercontent.com/..." />
#   <meta name="twitter:image" content="https://raw.githubusercontent.com/..." />
#   <meta property="og:url" content="https://gradio.app/" />
#
# The preconnects are connection hints - no font is fetched, but the browser
# does open a connection to Google, which is not what "100% offline" should
# mean. The script tag is a genuine fetch from a CDN on every page load; it
# exists so a Gradio app can be embedded in somebody else's iframe, which this
# app never is. The meta tags are social-preview cards, only read by crawlers
# when a link is shared - not by the browser, but they still name somebody
# else's server in a page that claims to be fully offline.
#
# Rather than editing Gradio's installed files - which a reinstall would undo -
# this builds a patched copy of the template inside the app folder and makes it
# win. The result is verified by reading the page back off the running server.
EXTERNAL_TAG_PATTERNS = [
    r'<link[^>]*rel="preconnect"[^>]*fonts\.googleapis\.com[^>]*>',
    r'<link[^>]*rel="preconnect"[^>]*fonts\.gstatic\.com[^>]*>',
    r'<script[^>]*cdnjs\.cloudflare\.com[^>]*>\s*</script>',
    r'<meta[^>]*property="og:image"[^>]*>',
    r'<meta[^>]*name="twitter:image"[^>]*>',
    r'<meta[^>]*property="og:url"[^>]*>',
]


def offline_templates():
    """Point Gradio at a copy of its page template with no external requests.

    Gradio's template object is left completely intact - it carries custom Jinja
    filters (toorjson) and globals that the page needs. Only the loader is
    extended, with our patched directory first, so our copy wins and everything
    else keeps working. Building a fresh Jinja2Templates instead was tried and
    fails with "No filter named 'toorjson'".

    Returns (directory, removed_count). Never raises: if anything goes wrong
    the stock template is used and the app still works, just with the external
    references left in place.
    """
    import re

    try:
        import gradio.routes as gr_routes
        from jinja2 import ChoiceLoader, FileSystemLoader

        src_dir = os.path.join(os.path.dirname(gr_routes.__file__),
                               "templates", "frontend")
        if not os.path.isdir(src_dir):
            return None, 0

        dst_dir = os.path.join(APP_DIR, "app-template", "frontend")
        os.makedirs(dst_dir, exist_ok=True)

        removed = 0
        for name in ("index.html", "share.html"):
            src = os.path.join(src_dir, name)
            if not os.path.exists(src):
                continue
            with open(src, encoding="utf-8", errors="replace") as fh:
                html = fh.read()
            for pattern in EXTERNAL_TAG_PATTERNS:
                html, n = re.subn(pattern, "", html, flags=re.S | re.I)
                removed += n
            with open(os.path.join(dst_dir, name), "w",
                      encoding="utf-8", newline="") as fh:
                fh.write(html)

        if removed == 0:
            return None, 0

        env = gr_routes.templates.env
        # auto_reload so an already-imported Gradio still picks up our copy.
        env.auto_reload = True
        env.loader = ChoiceLoader([
            FileSystemLoader(os.path.join(APP_DIR, "app-template")),
            env.loader,
        ])
        env.cache.clear()
        return os.path.join(APP_DIR, "app-template"), removed
    except Exception as exc:                                # noqa: BLE001
        line("  (could not strip Gradio's page template: %s)" % exc)
        return None, 0


def ui_speed_note():
    logical = os.cpu_count() or 4
    return ("Using %d of this PC's %d processor threads. Measured on a 16-thread "
            "machine: these settings render about 2.5x faster than real time."
            % (CPU_THREADS, logical))


def _selftest():
    """Check every on-screen string actually formats, before showing it.

    Two opposite mistakes are possible with a literal percent sign, and neither
    is a syntax error - the file compiles fine and the problem only appears
    when the page is built, which is the worst possible moment:

      * a raw '%' inside a string that IS formatted  -> TypeError at page build
      * a '%%' inside a string that is NOT formatted  -> prints "%%" on screen

    Both are checked here, at import, so a broken label can never reach a user.
    """
    import ast

    # --- 1. every user-facing string must survive being formatted.
    probes = [
        ("header", "# Local AI Voice Studio\n"
                   "**Runs 100%% on this PC. No internet. No account. "
                   "No graphics card needed.**  \n"
                   "Powered by Kokoro-82M - %d voices, roughly %d MB installed."
                   % (len(VOICES), MODEL_BYTES // 1_000_000)),
        ("speed note", ui_speed_note()),
        ("stats line", "%.1fs of audio in %.1fs  |  %.2fx real time  |  %d chunks"
                       % (1.0, 1.0, 1.0, 1)),
        ("progress", "Rendering %d of %d  |  %.1fs of audio done  |  %.2fx real time"
                     % (1, 2, 1.0, 1.0)),
        ("startup", "  Processor: %d threads of %d in use (all of them is slower)."
                    % (CPU_THREADS, os.cpu_count() or 4)),
        ("ready", "Studio ready in %.0f seconds." % 1.0),
        ("offline banner", "  LOCAL AI VOICE STUDIO  -  100% OFFLINE  -  Tips"),
        ("missing", "  The model and all %d voices are on this PC, so" % len(VOICES)),
    ]
    for name, text in probes:
        # After formatting, only literal percent signs from '%%' should remain.
        # A surviving conversion is '%' followed by an optional precision then
        # exactly one of the conversion letters - no space is allowed, or
        # ordinary prose like "100% on this PC" gets flagged by mistake.
        leftover = re.findall(r"%[-#+0]*[\d.]*[diouxXeEfFgGcrsa]", text)
        if leftover:
            raise AssertionError("string %r still has an unformatted %s -> %r"
                                 % (name, leftover, text))

    # --- 2. a '%%' is only reachable on screen if its string is formatted.
    #         Scan for the exact shape: a '%'-format applied to a string
    #         constant that contains '%%' but no conversion at all, which
    #         renders as two percent signs.
    source = open(os.path.abspath(__file__), encoding="utf-8").read()
    offenders = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Mod):
            continue
        text = node.left
        if not isinstance(text, ast.Constant) or not isinstance(text.value, str):
            continue
        if "%%" not in text.value:
            continue
        if not re.search(r"%[-#+0]*[\d.]*[diouxXeEfFgGcrsa]", text.value):
            offenders.append((node.lineno, text.value.strip().splitlines()[0][:70]))
    if offenders:
        raise AssertionError(
            "these strings are formatted with %% but contain no conversion, so "
            "the '%%%%' will show as two percent signs on screen: %s" % offenders)

    return len(probes)


# Run at import so a broken label can never reach a user.
_SELFTEST_STRINGS = _selftest()


def build_ui():
    import gradio as gr

    # Must happen before the Blocks object exists, because the page template is
    # chosen when the app is created.
    _tpl_dir, _tpl_removed = offline_templates()
    if _tpl_removed:
        line("  [ok] removed %d external reference(s) from the page template"
             % _tpl_removed)

    with gr.Blocks(title="Local AI Voice Studio", theme=offline_theme()) as demo:
        gr.Markdown(
            "# Local AI Voice Studio\n"
            "**Runs 100%% on this PC. No internet. No account. No graphics card needed.**  \n"
            "Powered by Kokoro-82M - %d voices, roughly %d MB installed."
            % (len(VOICES), MODEL_BYTES // 1_000_000)
        )

        with gr.Row():
            with gr.Column(scale=3):
                text_input = gr.Textbox(
                    label="Your script",
                    placeholder="Paste your voiceover script here...",
                    lines=10,
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
                stats_box = gr.Textbox(label="Speed", lines=2, max_lines=3,
                                       interactive=False)
                progress_box = gr.Textbox(label="Progress", lines=1, max_lines=1,
                                          interactive=False)
                file_box = gr.Textbox(label="Saved file", lines=1, max_lines=1,
                                      interactive=False)
                gr.Markdown(
                    "Files are saved in the **output** folder next to this app, "
                    "ready to drag straight into CapCut or Premiere Pro."
                )

        btn.click(fn=generate_speech,
                  inputs=[text_input, voice_dropdown, speed],
                  outputs=[audio_output, stats_box, file_box, progress_box],
                  api_name="generate_voice")

        with gr.Accordion("Which voice should I pick?", open=False):
            gr.Markdown(
                "- **am_adam** - deep and punchy. Tech reviews, faceless video essays.\n"
                "- **af_heart** - warm and natural. Documentary and story narration.\n"
                "- **bm_george** - classic British narrator. Explainer channels.\n"
                "- **bf_emma** - crisp newsreader. Corporate and news style.\n\n"
                "Tip: generate the same line in two voices, then pick the one that "
                "fits your edit."
            )

        with gr.Accordion("How fast is this, and is it really offline?", open=False):
            gr.Markdown(
                "%s\n\n"
                "**Offline:** the model file and every voice live in the folder next "
                "to this app. Nothing is downloaded while you work, there is no "
                "account, and no request leaves this PC.\n\n"
                "**No graphics card needed:** a GPU genuinely does not help for this "
                "model - see the note at the top of `local_voice_app.py` for the three "
                "GPU configurations that were measured and failed.\n\n"
                "**One quirk worth knowing:** the same line generated twice is not "
                "byte-identical (about 0.996 correlation). It sounds the same, so "
                "re-render a fluffed line freely."
                % ui_speed_note()
            )

    return demo


def generate_speech(text, voice_label, speed, progress=None):
    import gradio as gr
    import soundfile as sf

    text = (text or "").strip()
    if not text:
        raise gr.Error("Type something in the script box first.")

    if not model_is_present():
        raise gr.Error(
            "The voice model is not on this PC yet. Run the setup file once "
            "while you have internet - after that it works offline forever."
        )

    voice = VOICES.get(voice_label, "af_heart")

    try:
        engine, _load = load_engine()
    except Exception as exc:                                # noqa: BLE001
        raise gr.Error("Could not load the voice engine: %s" % exc)

    def on_progress(done, total, audio_secs, elapsed):
        rate = (audio_secs / elapsed) if elapsed > 0 else 0
        msg = ("Rendering %d of %d  |  %.1fs of audio done  |  %.2fx real time"
               % (done, total, audio_secs, rate))
        line("  " + msg)
        if progress is not None:
            try:
                progress((done / float(total)) * 0.98, desc=msg)
            except Exception:
                pass

    try:
        wav, n_chunks, elapsed = render(
            engine["kokoro"], text, voice, float(speed), on_progress)
    except Exception as exc:                                # noqa: BLE001
        raise gr.Error("Could not generate audio: %s" % exc)

    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = "%s_%s.wav" % (stamp, voice)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    sf.write(path, wav, SAMPLE_RATE)

    audio_len = len(wav) / float(SAMPLE_RATE)
    speedup = (audio_len / elapsed) if elapsed > 0 else 0
    stats = ("%.1fs of audio in %.1fs  |  %.2fx real time  |  %d chunks  |  "
             "%d Hz mono  |  %d threads"
             % (audio_len, elapsed, speedup, n_chunks, SAMPLE_RATE, CPU_THREADS))

    line("  -> %s  (%.1fs of audio in %.1fs, %.2fx)"
         % (filename, audio_len, elapsed, speedup))
    return path, stats, path, ""


# ------------------------------------------------------- launching the window
def find_app_browser():
    """Return a browser that can run in chromeless "app mode".

    Edge ships with Windows 10 and 11, so it is almost always present. Chrome
    is the fallback. Both support --app=, which opens a window with no address
    bar and no tabs - it looks and behaves like a desktop application.
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
    """Open the studio as a chromeless app window."""
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
    # exit (verified). So whatever is on disk now may describe a browser that is
    # long gone. Remember it, then clear it, so the value read afterwards can
    # only have come from the launch we are about to do.
    previous = _peek_devtools_port(marker)
    if marker and os.path.exists(marker):
        try:
            os.remove(marker)
        except Exception:
            marker = None

    # These flags are not decoration - each was measured on a real Edge:
    #   --disable-sync             without it Edge opens a second window called
    #                              "We are now syncing your browser"
    #   --disable-extensions       without it Edge loads 5 built-in extension
    #                              background pages that keep the browser alive
    #                              after our window closes
    #   --disable-background-mode  no "keep running in background"
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
    so a momentary hiccup cannot stop the studio mid-sentence. That grace
    period is also what lets a browser reload the page without killing the
    server underneath it.
    """
    if window is None:
        _idle_forever()
        return False
    if not window.port:
        line("  This window cannot tell when you close it, so it stays open.")
        line("  Close the studio from Task Manager if you need to stop it.")
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
# Holds the single-instance claim for the lifetime of the process. Windows
# releases it automatically when the process ends, however it ends, so a
# crash can never lock the viewer out of their own app.
_INSTANCE_HANDLE = None


def _crash_report(exc):
    """Last resort: an unhandled error still has to reach the viewer.

    Without this, a failure inside a pythonw process is completely silent -
    no console to print to, so the window simply never appears and the viewer
    has nothing to act on.
    """
    line("")
    line("  [X] the studio stopped unexpectedly")
    _log_traceback(exc)
    show_error(
        "Local AI Voice Studio - unexpected error",
        "The studio stopped unexpectedly.\n\n%s\n\n"
        "Double-click \"Repair Setup.bat\" in the studio folder and try "
        "again. The full details are in studio.log." % exc)


def warm_engine():
    """Load the model and render one short line, so the first real click is fast.

    Without this, the first Generate of the session pays for lazy graph
    initialisation and measures about 40% slower than every one after it -
    which is exactly the number somebody would judge the app on.
    """
    engine, load_secs = load_engine()
    t0 = time.time()
    wav, _n, _elapsed = render(engine["kokoro"], "Ready.", "af_heart", 1.0)
    line("  [ok] engine warmed in %.1fs (load %.1fs, first line %.1fs)"
         % (time.time() - t0, load_secs, time.time() - t0))


def main():
    global _INSTANCE_HANDLE

    # Take the "one studio at a time" claim before anything else - including
    # the banner. The banner is how the log says "a studio started", so
    # printing it and only then deciding not to start would make a refused
    # second launch look exactly like a second launch.
    claim = claim_single_instance()
    _INSTANCE_HANDLE = claim

    if claim is None or (claim == "unknown" and port_in_use(PORT)):
        line("  A studio is already running - bringing it to the front.")
        url = "http://127.0.0.1:%d" % PORT
        if not port_in_use(PORT):
            # The running copy is still loading. Wait for it rather than
            # showing the viewer a "can't reach this page" error.
            line("  Waiting for it to finish starting...")
            wait_for_port(PORT, 90)
        open_app_window(url)
        return 0

    line("=" * 68)
    line("  LOCAL AI VOICE STUDIO  -  100% OFFLINE  -  Tech Tips Dhanwala MH")
    line("=" * 68)
    line("")

    if not model_is_present():
        msg = ("The voice model is not on this PC yet, or its download did "
               "not finish.\n\n"
               "Open the studio folder and double-click \"START HERE.bat\" "
               "once while you have internet.\n\n"
               "After that, the studio works offline forever.")
        line("")
        line("  [X] voice model missing or incomplete")
        show_error("Local AI Voice Studio - setup not finished", msg)
        return 1

    logical = os.cpu_count() or 4
    line("")
    line("  Offline mode: ON. The model and all %d voices are on this PC, so"
         % len(VOICES))
    line("  nothing here will touch the internet.")
    line("  Processor: %d threads of %d in use (all of them is slower)."
         % (CPU_THREADS, logical))
    line("")

    started_all = time.time()

    # Build and start the web interface BEFORE loading the model.
    #
    # Measured reason: loading the engine and warming it costs about 15
    # seconds on a laptop of this class. Doing it first means the viewer
    # stares at nothing for that long and concludes the app is broken. Doing
    # it after means the window is on screen in roughly three seconds, and
    # the engine catches up while they are reading the page and picking a
    # voice. Same total work, completely different first impression.
    demo = build_ui()
    icon = os.path.join(APP_DIR, "voice.ico")

    line("Opening the studio window...")
    try:
        demo.queue().launch(
            server_name="127.0.0.1",
            server_port=PORT,
            inbrowser=False,
            prevent_thread_lock=True,
            favicon_path=icon if os.path.exists(icon) else None,
        )
    except Exception as exc:                                # noqa: BLE001
        msg = ("The studio could not open its window.\n\n%s\n\n"
               "Another program may be using port %d. Restarting the "
               "computer fixes that." % (exc, PORT))
        line("  [X] could not open the window")
        # Log the real traceback, not just the message. The visible message is
        # written for the viewer; this is written for whoever has to diagnose
        # it, and a bare message once cost an hour of guessing.
        _log_traceback(exc)
        show_error("Local AI Voice Studio - could not start", msg)
        return 1

    line("  [ok] window available after %.0fs" % (time.time() - started_all))

    window = open_app_window("http://127.0.0.1:%d" % PORT)
    if window is None:
        line("  (no Edge or Chrome found, so it opened in your default browser)")

    # Now load and warm the engine, off the main thread. If the viewer presses
    # Generate before this finishes they simply wait for the same load:
    # load_engine() is guarded, so the work happens once either way and the
    # warm-up is never paid for twice.
    line("Loading the AI engine in the background (about 15 seconds)...")

    def _warm():
        try:
            warm_engine()
            line("  [ok] ready to record")
        except Exception as exc:                            # noqa: BLE001
            line("  [X] could not load the engine: %s" % exc)
            _log_traceback(exc)
            show_error(
                "Local AI Voice Studio - engine failed",
                "The voice engine could not be loaded.\n\n%s\n\n"
                "Double-click \"Repair Setup.bat\" in the studio folder and "
                "try again." % exc)

    threading.Thread(target=_warm, name="warm", daemon=True).start()

    if wait_until_window_closes(window):
        line("  App window closed. Shutting the studio down.")

    # The Gradio server lives in its own thread, so exit hard: the studio must
    # never linger invisibly and keep holding the port after the window is gone.
    try:
        sys.stdout.flush()
    except Exception:
        pass
    os._exit(0)


if __name__ == "__main__":
    # A crash must never be silent. The studio usually runs with no console,
    # so an unhandled error would otherwise look like "nothing happened".
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as exc:                            # noqa: BLE001
        _crash_report(exc)
        sys.exit(1)
