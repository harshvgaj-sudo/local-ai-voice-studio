# ==============================================================================
#  ONE-TIME MODEL DOWNLOAD
#
#  This is the part that makes the studio work with the internet switched off.
#  It fetches the Kokoro-82M model plus every voice in the app's dropdown and
#  stores them on this PC. It is run automatically by "START HERE.bat"
#  during setup - you never have to run it yourself.
#
#  If it is ever interrupted, just run it again. Already-downloaded files
#  are skipped, so it resumes where it left off.
# ==============================================================================

import os
import sys
import time

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

# Passed explicitly so Kokoro does not print a "Defaulting repo_id" warning
# into the setup output. Same value the app itself uses.
REPO_ID = "hexgrad/Kokoro-82M"

VOICES = {
    "a": ("American English", [
        "af_heart", "af_bella", "af_nicole",
        "am_adam", "am_michael",
    ]),
    "b": ("British English", [
        "bf_emma", "bf_isabella",
        "bm_george", "bm_lewis",
    ]),
}


def main():
    print("Downloading the Kokoro-82M model and voice packs.")
    print("This happens once. After this the studio never needs internet.")
    print()

    try:
        from kokoro import KPipeline
    except ImportError as exc:
        print("  [X] The voice engine is not installed yet: %s" % exc)
        return 1

    done = 0
    missing = []
    overall = time.time()

    for lang_code, (label, voices) in VOICES.items():
        print("%s:" % label, flush=True)
        try:
            pipeline = KPipeline(lang_code=lang_code, repo_id=REPO_ID)
        except Exception as exc:                       # noqa: BLE001
            print("  [X] could not load %s: %s" % (label, exc))
            return 1

        for voice in voices:
            started = time.time()
            try:
                # A short line is enough - it is what pulls the voice pack down.
                for _ in (pipeline("Ready.", voice=voice, split_pattern=r"\n+") or []):
                    pass
                print("   [ok] %-12s  (%.1fs)" % (voice, time.time() - started), flush=True)
                done += 1
            except Exception as exc:                   # noqa: BLE001
                print("   [X]  %-12s  failed: %s" % (voice, exc), flush=True)
                missing.append(voice)
        print()

    print("-" * 64)
    print("  %d of %d voices stored on this PC (%.0fs)."
          % (done, done + len(missing), time.time() - overall))
    if missing:
        print("  Could not fetch: %s" % ", ".join(missing))
        print("  Run this file again to retry just those.")
        print("-" * 64)
        # Report failure. Returning 0 here would let the setup write its
        # "ready" marker and tell the viewer everything is installed while
        # some voices are still missing - and they would only discover that
        # later, offline, with the voice refusing to generate.
        return 1
    print("-" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
