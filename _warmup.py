# ==============================================================================
#  ONE-TIME MODEL DOWNLOAD
#
#  Fetches the Kokoro voice model and the voice pack, and stores them inside
#  this folder so the studio never needs the internet again. Run automatically
#  by "START HERE.bat" during setup - you never have to run it yourself.
#
#  Sizes (measured, not guessed):
#       kokoro-v1.0.onnx    326 MB   the voice model
#       voices-v1.0.bin      27 MB   all 54 voices
#       ----------------------------
#       about 353 MB, one time only
#
#  If it is ever interrupted, run it again. A file that is already complete is
#  skipped, and a file that is only half there is deleted and restarted - a
#  half file that looks "present" is the one failure mode worth being careful
#  about, because the app would then fail at the worst possible moment.
# ==============================================================================

import hashlib
import os
import sys
import time
import urllib.error
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(APP_DIR, "models")

RELEASE = ("https://github.com/thewh1teagle/kokoro-onnx/releases/download/"
           "model-files-v1.1")

# name -> (bytes, sha256). Both come from the release page, and both are
# checked after every download. Without the hash a truncated transfer is
# indistinguishable from a good one until the app tries to speak.
FILES = {
    "kokoro-v1.0.onnx": (
        325505369,
        "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
    ),
    "voices-v1.0.bin": (
        28214398,
        "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
    ),
}


def sha256(path, chunk=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def verify(path, want_size, want_hash):
    """Return '' when the file is complete and correct, else why not."""
    if not os.path.exists(path):
        return "missing"
    have = os.path.getsize(path)
    if have != want_size:
        return "wrong size (%d bytes, expected %d)" % (have, want_size)
    got = sha256(path)
    if got != want_hash:
        return "checksum mismatch"
    return ""


def download(name, want_size, want_hash):
    dest = os.path.join(MODELS_DIR, name)
    url = "%s/%s" % (RELEASE, name)

    problem = verify(dest, want_size, want_hash)
    if not problem:
        print("   [ok] %-22s already downloaded" % name, flush=True)
        return True

    if problem != "missing":
        print("   [..] %-22s %s - starting over" % (name, problem), flush=True)
        try:
            os.remove(dest)
        except OSError:
            pass

    # Download to a separate file and only move it into place once the size is
    # right. A half-written file must never be visible under the real name,
    # because "the file exists" is what the app uses to decide it is offline.
    part = dest + ".part"
    started = time.time()
    last = [0.0, 0.0]      # [bytes, time] for the speed readout

    def hook(blocks, block_size, total):
        done = blocks * block_size
        now = time.time()
        if now - last[1] < 0.5 and done < (total or 1):
            return
        last[0], last[1] = done, now
        elapsed = max(now - started, 0.01)
        pct = (done / total * 100.0) if total else 0.0
        speed = done / elapsed / (1024 * 1024)
        eta = ((total - done) / (done / elapsed)) if done else 0
        sys.stdout.write(
            "\r   [..] %-22s %5.1f%%  %.1f MB/s  about %dm%02ds left   "
            % (name, pct, speed, int(eta // 60), int(eta % 60)))
        sys.stdout.flush()

    try:
        urllib.request.urlretrieve(url, part, hook)
    except (urllib.error.URLError, OSError) as exc:
        sys.stdout.write("\n")
        print("   [X]  %-22s download failed: %s" % (name, exc), flush=True)
        try:
            os.remove(part)
        except OSError:
            pass
        return False

    sys.stdout.write("\n")
    problem = verify(part, want_size, want_hash)
    if problem:
        print("   [X]  %-22s %s after download" % (name, problem), flush=True)
        try:
            os.remove(part)
        except OSError:
            pass
        return False

    os.replace(part, dest)
    print("   [ok] %-22s %.0f MB verified in %.0fs"
          % (name, want_size / 1e6, time.time() - started), flush=True)
    return True


def main():
    print("Downloading the AI voice model.")
    print("This happens once. After this the studio never needs internet.")
    print()

    os.makedirs(MODELS_DIR, exist_ok=True)

    failed = []
    for name, (size, digest) in FILES.items():
        if not download(name, size, digest):
            failed.append(name)

    print()
    print("-" * 64)
    total = sum(s for s, _ in FILES.values())
    print("  about %.0f MB stored in %s" % (total / 1e6, MODELS_DIR))
    if failed:
        print("  Could not fetch: %s" % ", ".join(failed))
        print("  Run this file again to retry just those.")
        print("-" * 64)
        # Report failure. Returning 0 would let setup write its "ready" marker
        # and tell the viewer everything is installed while the model is in
        # fact incomplete - and they would only find out later, offline.
        return 1
    print("  Everything the studio needs is now on this PC.")
    print("-" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
