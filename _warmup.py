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


def fetch(name, url, part, want_size, resume):
    """Fetch url into part. True if the transfer reached the end.

    With resume=True an existing part file is continued with a Range request.
    GitHub's release CDN answers those with 206 and a real Content-Range, so a
    download that died at 300 MB of 326 MB only has 26 MB left to fetch.

    If the server ignores the Range and answers 200 with the whole file, the
    part is rewritten from the start rather than appended to: appending a full
    body onto a partial one produces a file of exactly the right size and
    entirely the wrong bytes, which is the one failure the size check cannot
    catch on its own.

    The part file is deliberately LEFT IN PLACE when the transfer fails, so the
    next run can carry on from further along. It is removed only when the
    caller has decided the contents are no good.
    """
    start = 0
    mode = "wb"
    if resume and os.path.exists(part):
        start = os.path.getsize(part)
        if start >= want_size:
            # Already as big as it should be. Fetching nothing and letting the
            # caller verify is the only safe move: asking for `bytes=<size>-`
            # makes the server answer 416, which would abort a download that
            # just needs its existing bytes checked.
            return True
        if start > 0:
            mode = "ab"

    headers = {"User-Agent": "curl/8"}
    if start:
        headers["Range"] = "bytes=%d-" % start

    started = time.time()
    last = [0.0]
    done = start
    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            if start and response.status != 206:
                start = 0
                done = 0
                mode = "wb"
            with open(part, mode) as handle:
                while True:
                    block = response.read(256 * 1024)
                    if not block:
                        break
                    handle.write(block)
                    done += len(block)
                    now = time.time()
                    if now - last[0] < 0.5 and done < want_size:
                        continue
                    last[0] = now
                    elapsed = max(now - started, 0.01)
                    sent = done - start
                    speed = (sent / elapsed / (1024 * 1024)) if sent else 0.0
                    pct = (done / want_size * 100.0) if want_size else 0.0
                    left = ((want_size - done) / (sent / elapsed)) if sent else 0
                    sys.stdout.write(
                        "\r   [..] %-22s %5.1f%%  %.1f MB/s  about %dm%02ds left   "
                        % (name, pct, speed, int(left // 60), int(left % 60)))
                    sys.stdout.flush()
    except (urllib.error.URLError, OSError) as exc:
        sys.stdout.write("\n")
        got = os.path.getsize(part) if os.path.exists(part) else 0
        print("   [X]  %-22s download failed: %s" % (name, exc), flush=True)
        if got:
            print("        Got %.0f MB so far. Run this file again and it will"
                  % (got / 1e6), flush=True)
            print("        carry on from there instead of starting over.",
                  flush=True)
        return False

    sys.stdout.write("\n")
    return True


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

    # Download to a separate file and only move it into place once the size AND
    # the hash are right. A half-written file must never be visible under the
    # real name, because "the file exists" is what the app uses to decide it is
    # offline.
    part = dest + ".part"
    started = time.time()

    # First continue whatever an earlier run left behind, then - only if that
    # did not produce a good file - fetch the whole thing again. The size and
    # sha256 are checked either way, so a bad resume can never reach the app;
    # it costs one extra download at worst, which is the old behaviour.
    for attempt, resume in enumerate((True, False)):
        if not fetch(name, url, part, want_size, resume):
            if resume and attempt == 0:
                # Could not continue. That is not the same as the network being
                # down, so drop the unusable part and try the whole file.
                print("   [..] %-22s could not continue - starting over"
                      % name, flush=True)
                try:
                    os.remove(part)
                except OSError:
                    pass
                continue
            return False
        problem = verify(part, want_size, want_hash)
        if not problem:
            os.replace(part, dest)
            print("   [ok] %-22s %.0f MB verified in %.0fs"
                  % (name, want_size / 1e6, time.time() - started), flush=True)
            return True
        if attempt == 0:
            print("   [..] %-22s %s after continuing - starting over"
                  % (name, problem), flush=True)
            try:
                os.remove(part)
            except OSError:
                pass

    print("   [X]  %-22s %s after download" % (name, problem), flush=True)
    try:
        os.remove(part)
    except OSError:
        pass
    return False


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
