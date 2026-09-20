<img src="assets/banner.svg" alt="Local AI Voice Studio - free offline AI voice generator for Windows" width="100%">

# Local AI Voice Studio

**A free offline AI voice generator for Windows.** Paste a script, click one button, get a broadcast-quality voiceover WAV file. No GPU, no API key, no account, no monthly fee, and no internet connection after the one-time setup.

![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white)
![GPU](https://img.shields.io/badge/GPU-not%20required-2ea44f)
![Internet](https://img.shields.io/badge/internet-needed%20once%2C%20then%20never-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Model](https://img.shields.io/badge/model-Kokoro--82M%20(Apache--2.0)-orange)
![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)

---

## Download

### ➡️ **[Download `Install-Local-AI-Voice.bat`](https://github.com/harshvgaj-sudo/local-ai-voice-studio/releases/latest/download/Install-Local-AI-Voice.bat)**

One file, about 58 KB. Double-click it. That is the whole install.

Or browse the [latest release](https://github.com/harshvgaj-sudo/local-ai-voice-studio/releases/latest) if you would rather read the notes first.

> **Windows will warn you.** The file is not code-signed (code signing costs money every year, and this project is free). Your browser may say *"This file isn't commonly downloaded"* and SmartScreen may say *"Windows protected your PC"*. Click **Keep** and **More info → Run anyway**. This is normal for any free, unsigned tool.

---

## How to use it

1. **Download** `Install-Local-AI-Voice.bat` from the link above.
2. **Double-click it.** A black window appears and sets everything up by itself. This downloads about 540 MB and takes roughly 3 to 10 minutes depending on your internet speed. You do not need Python, and you do not need to install anything else.
3. **Wait for `READY TO RECORD`.** The studio window opens. Paste your script, pick a voice, press **GENERATE VOICE**. Your WAV file lands in the `output` folder next to the app.

After the first time, you never repeat the setup. Just double-click the **Local AI Voice Studio** desktop shortcut and the app window is on screen in about **7 seconds** — with no black window at any point, not even for a moment. That is true from the very first launch: setup pre-compiles every library while it is installing, so the app never has to do it while you wait.

---

## Why this exists

Cloud AI voice services charge a subscription, cap your characters, and require you to upload your script to somebody else's server. Most local alternatives assume you are comfortable with a terminal, a GPU, and a stack of Python errors.

This project removes all of that:

- **One file to download.** No `pip install`, no `git clone`, no terminal, no virtual environment to activate by hand.
- **No GPU.** It runs on an ordinary laptop CPU. A graphics card is not detected, not needed, and deliberately not used — see [Why it does not use your GPU](#why-it-does-not-use-your-gpu).
- **No account, no key, no tracking.** The app makes no outbound connections once setup finishes. You can install it, turn off your Wi-Fi, and it still works.
- **Your script never leaves your computer.** It is processed locally, always.
- **Unlimited.** No character counter, no monthly quota, no watermark.

---

## What you get

| | |
|---|---|
| **Voices** | 9 hand-picked English voices — 3 US female, 2 US male, 2 UK female, 2 UK male |
| **Audio format** | 24 kHz mono WAV (16-bit PCM), ready to drop into CapCut, Premiere Pro, DaVinci Resolve or Audacity |
| **Speed control** | 0.7× to 1.4×, adjustable per generation |
| **Script length** | No hard limit. Long scripts are split into safe chunks and stitched back together automatically, with natural pauses at paragraph breaks |
| **Engine** | [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) — 82M parameters, Apache-2.0 weights, running on ONNX Runtime |
| **Interface** | A real application window, not a browser tab |

### The voices

| Voice | Accent | Character |
|---|---|---|
| `af_heart` | US Female | Warm documentary |
| `af_bella` | US Female | Expressive |
| `af_nicole` | US Female | Soft audiobook |
| `am_adam` | US Male | Deep commercial |
| `am_michael` | US Male | Podcast narrator |
| `bf_emma` | UK Female | Crisp newsreader |
| `bf_isabella` | UK Female | Calm and elegant |
| `bm_george` | UK Male | Classic British narrator |
| `bm_lewis` | UK Male | Deep, authoritative |

Kokoro-82M itself ships 54 voices across 8 languages. This app deliberately exposes only the 9 English ones, because a nine-item dropdown is usable and a fifty-four-item dropdown is not.

---

## System requirements

| | |
|---|---|
| **OS** | Windows 10 **version 1803 (2018) or newer**, or Windows 11 — 64-bit |
| **CPU** | 64-bit (x86-64) Intel or AMD |
| **RAM** | 8 GB recommended (works on less, but generation slows down) |
| **Disk** | About 2 GB free on `C:` (final footprint after setup is about 1 GB) |
| **GPU** | **Not required.** No NVIDIA, AMD or Intel graphics needed |
| **Python** | **Not required.** The setup installs its own private copy |
| **Admin rights** | **Not required.** Nothing is installed system-wide |
| **Internet** | Needed once, during setup. Never again |
| **Browser** | Edge or Chrome for the app window — both are preinstalled on Windows 10/11 |

**Why Windows 10 1803 is the floor:** the installer uses `curl.exe` and `tar.exe`, which
Microsoft only shipped with Windows starting at build 17063. On anything older the setup
stops with "could not download the setup tool".

**Does not work on:** 32-bit Windows (the bundled `uv` has no 32-bit Windows build),
Windows 8.1 or earlier, macOS, or Linux.

**If you have no Edge or Chrome** (Firefox-only setup, or a stripped Windows image), the
studio still works completely — it just opens in an ordinary browser tab with an address
bar instead of its own app window.

---

## What actually gets downloaded

The setup downloads about 540 MB the first time and nothing after that.

| Component | Approx. size | What it is |
|---|---|---|
| Voice model (`kokoro-v1.0.onnx`) | ~326 MB | The actual AI voice — downloaded once, yours forever |
| Python libraries (71 packages) | ~150 MB | ONNX Runtime (the maths engine) plus Gradio and the web stack |
| Voices file (`voices-v1.0.bin`) | ~28 MB | The 9 voice "personalities" |
| Python 3.12 (private copy) | ~22 MB | Installed inside the app folder, never system-wide |
| `uv` + setup tooling | ~17 MB | The installer's own tooling |

Everything lives inside one folder: `C:\Users\<you>\LocalVoiceStudio`. Nothing is installed system-wide, no registry keys are written, and no PATH entries are added.

**Measured footprint on a clean install — about 1 GB:**

| Folder | Size | Notes |
|---|---|---|
| `env\` | 550 MB | The 71 Python packages, including pre-compiled bytecode |
| `models\` | 337 MB | The voice model and the voices file |
| `python\` | 121 MB | Python 3.12 itself — **required at run time** |
| app files | 1 MB | The app, the docs, the icon |

There is **no Hugging Face cache** to clean up, because the model is downloaded straight into `models\` rather than into a shared cache directory. The setup also deletes its own download cache when it finishes, so it does not leave a second copy of everything on your disk.

> **Do not delete the `python\` folder.** It looks like a leftover and it is not. A Python virtual environment does not contain the standard library — `env\pyvenv.cfg` points at this copy of Python 3.12, and `env\Scripts\pythonw.exe` is only a launcher that starts it. Remove it and the studio stops working completely and silently. `Uninstall.bat` removes it for you, together with `env\`.

---

## Why it does not use your GPU

This is worth explaining, because "no GPU required" is usually code for "the developer never tried".

It was tried. The development machine has an Intel Iris Xe integrated GPU, and DirectML — Microsoft's GPU backend for ONNX Runtime — was wired up and benchmarked. It **does not work** on this model:

- Seven `ConvTranspose` nodes in Kokoro's decoder fail to initialise with `80070057 The parameter is incorrect`. This happens in fp32, in fp16, and after hand-pinning all 1,988 `/decoder` nodes to the GPU. The graph simply does not compile on DirectML.
- An int8-quantised build will not load at all — DirectML rejects the `ConvInteger(10)` operator.

So GPU acceleration here would be a crash, not a speed-up. CPU is not a compromise; it is the correct choice for this model.

The good news is that CPU is genuinely fast enough. Measured on the same text, same 21.0 seconds of audio:

| Engine | Speed (RTF) | Installed size | RAM while generating |
|---|---|---|---|
| ONNX Runtime (what ships now) | **0.295** | ~1 GB | ~350 MB |
| PyTorch CPU (the original build) | 0.495 | ~1.3 GB | ~2 GB |

RTF is seconds of wall clock per second of finished audio, so lower is better — **1.7× faster, in about a third less disk space, using under a fifth of the memory.** On a laptop with 7.2 GB of RAM the old PyTorch build spent its time paging to disk, which is what "it takes too long" actually looked like.

One more measured detail: ONNX Runtime defaults to using **all** logical processors, which is the *slowest* configuration on a shared machine. A thread sweep gave 4→0.339, 6→0.312, 8→0.316, 12→0.301, **16→0.382**. The app caps the thread count at 75% of your logical cores (maximum 12) instead of leaving it at the default.

---

## FAQ

**Does it really work without a GPU?**
Yes, and [the section above](#why-it-does-not-use-your-gpu) explains exactly why — including the benchmark numbers from the failed attempt to use one. On a mid-range laptop CPU the app's own Benchmark box reports about **2.5× real time** — measured on an 867-character script that produced 50 seconds of audio in 19 seconds. A 1,000-word script (about 6–7 minutes of finished audio) takes about two and a half minutes.

**Is it really free?**
Yes. The app is MIT licensed and the voice model is Apache-2.0. There is no paid tier, no account, and nothing to buy.

**Can I use the audio commercially — YouTube, client work, monetised videos?**
The model weights are released under Apache-2.0, which permits commercial use. Do check the licence yourself for your own situation; this is a description of the licence, not legal advice.

**Does my text get sent anywhere?**
No. Your script never leaves your PC — it is turned into audio in local memory. The app also makes **no outbound requests at all** while you use it: it sets `HF_HUB_OFFLINE=1` so the model library never phones home to check for updates, and it uses system fonts instead of fetching a web font. The honest test is to disconnect from the internet and use it — that is exactly how it was verified: a real browser's network traffic was captured while generating audio, and all 66 requests went to your own PC, zero to the internet.

**Why does the launch take about 7 seconds?**
Because importing the interface library alone takes about 6 of those seconds, and the app opens its window *before* loading the 326 MB neural network, then loads that network in the background while you are reading the page and typing your script. The old build loaded the model first, which is why it used to take about 20 seconds to show anything. Nothing is skipped — the work just happens after the window appears instead of before it. The first **Generate** of a session may wait a moment longer while that finishes; every one after it is immediate.

**How long a script can it handle?**
There is no built-in limit. Scripts are split at paragraph and sentence boundaries and rejoined with natural pauses, so a 5,000-word script works. It just takes longer and produces a bigger WAV.

**Which languages?**
English only — American and British. The nine voices cover those two accents. Kokoro-82M itself is multilingual (Japanese, Mandarin, French, Spanish, Hindi and more), but this app deliberately ships only the English voices so the download stays manageable instead of several gigabytes.

**Why does Windows warn me when I run the installer?**
Because the file is unsigned. Signing certificates cost a few hundred dollars a year, which a free project does not have. The source is right here in this repository if you want to read exactly what it does before running it.

**Can I delete the installer after it runs?**
Yes. Once setup says `READY TO RECORD`, the installer has done its job and nothing reads from it again. You can delete `Install-Local-AI-Voice.bat`, or even the whole `LocalVoiceStudio` folder, and the desktop icon still works. The desktop shortcut points at the app directly, not at the setup file.

**Do I have to keep a black window open while I use it?**
No — and this was a real bug that got fixed. The app is started detached from the setup process, so closing the terminal, closing the folder, or closing the installer has no effect on a running studio. There is no console window at any point when you launch from the desktop icon.

**What if I double-click the icon twice?**
The second copy detects the first and exits with a message box saying the studio is already running. You cannot end up with two studios fighting over the same port. This is enforced with a Windows kernel mutex rather than a lock file, so a crash can never leave you permanently locked out.

**How do I uninstall it?**
Run `Uninstall.bat` inside the app folder. It removes the engine and Python (about 550 MB) and offers to remove the voice model too (about 340 MB). Your generated audio is kept.

---

## How it works

```
Install-Local-AI-Voice.bat   (one file, self-contained, ~58 KB)
        |
        |  decodes an embedded ZIP to %USERPROFILE%\LocalVoiceStudio
        v
START HERE.bat
        |
        |  1. downloads uv              (the installer's tooling)
        |  2. uv python install 3.12    (a private Python, inside the app folder)
        |  3. uv venv --seed            (an isolated environment)
        |  4. uv pip install -r requirements.txt   (71 packages)
        |  5. downloads the voice model + voices into models\
        |  6. writes .ready and upgrades the desktop icon
        v
local_voice_app.py
        |
        |  Kokoro-82M on ONNX Runtime (CPU)  ->  24 kHz WAV
        v
   a real application window (Edge/Chrome in --app mode)
```

Five details worth knowing if you are reading the source:

- **Setup pre-compiles the Python bytecode.** Without it, the very first launch spends about 14 extra seconds compiling 6,198 `.py` files, so the window takes 21 seconds to appear instead of 8 — and 13 of those seconds look like the app doing nothing at all. It costs 27 seconds of unattended install time and about 100 MB of disk, and it is skipped silently if it fails.
- **The window opens first, the model loads second.** `main()` builds the UI, starts the server, opens the window, and only then warms the engine on a background thread. The warm-up is guarded by a double-checked lock, so clicking Generate during those few seconds reuses the same session instead of building a second 350 MB copy of the model.
- **The GPU is deliberately pinned off.** ONNX Runtime would otherwise try to use an available GPU provider, which crashes on this model (see above). The CPU execution provider is selected explicitly, so results are identical on every machine.
- **The app never assumes it has a console.** Launched from the desktop icon it runs under `pythonw.exe`, which means `sys.stdout` is `None`. Uvicorn's logging formatter calls `sys.stdout.isatty()` and dies with `AttributeError: 'NoneType' object has no attribute 'isatty'`. The app therefore installs its own log streams — into `studio-server.log` — before anything else imports, which is what lets it run with no console window at all.
- **The window owns the studio's lifetime.** The app opens its own window and watches a private localhost debugging port that lives exactly as long as that window. Close the window and the studio shuts down — no invisible server left holding the port.
- **Setup keeps the base interpreter on purpose.** `python\` is not a leftover; the venv's `pyvenv.cfg` points at it. Deleting it makes the app fail to start with no log and no error the user can act on, so the launcher documents the reason in-line and never removes it.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Setup stopped partway | Double-click `START HERE.bat` inside the app folder, or `Repair Setup.bat` — it resumes where it left off |
| "Could not install the voice engine" | Almost always an interrupted download. Re-run `START HERE.bat` |
| A message box says the studio is already running | You double-clicked twice. The second click just brought the existing window forward. Nothing is wrong |
| A message box says setup is not finished | The voice model is missing or incomplete. Run `START HERE.bat` once with internet |
| The app window is blank | Close it and re-run `START HERE.bat`. Give it 7 seconds |
| The window never opens | Open your browser by hand and go to `http://127.0.0.1:7860`. If it is still not there, read `studio.log` in the app folder — it records what happened |
| `Repair Setup.bat` says files could not be removed | The studio window is still open. Close it, then run the file again |
| Antivirus flagged something | The installer is an unsigned download that unpacks a Python environment. Add the `LocalVoiceStudio` folder to your antivirus exclusions |
| Generation is very slow | Close other heavy programs. This app is far more limited by free memory than by CPU speed, and a full browser eats memory fast |
| Everything is broken | Run `Uninstall.bat`, then the installer again. Your audio files are never touched |

---

## Credits and licence

- **Kokoro-82M** by [hexgrad](https://huggingface.co/hexgrad) — Apache-2.0. The voice quality is entirely their work.
- **StyleTTS 2** architecture by [@yl4579](https://github.com/yl4579).
- **kokoro-onnx** for the ONNX export path, and **ONNX Runtime** by Microsoft for the inference engine.
- **eSpeak NG** for phonemisation, shipped inside the `espeakng-loader` wheel.
- **Gradio** for the interface layer.
- **uv** by [Astral](https://astral.sh) for the self-contained Python setup.

The application code in this repository is released under the **MIT licence** — see [LICENSE](LICENSE).

---

## Keywords

`free ai voice generator` · `offline text to speech` · `local tts` · `kokoro tts` · `ai voiceover` · `text to speech windows` · `no gpu tts` · `elevenlabs alternative free` · `ai voice generator without subscription` · `offline ai voice for youtube` · `python tts gui` · `kokoro 82m windows` · `onnx tts`

---

If this saved you a subscription, a ⭐ on the repository helps other people find it.
