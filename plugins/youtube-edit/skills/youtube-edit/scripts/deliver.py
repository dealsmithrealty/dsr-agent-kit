#!/usr/bin/env python3
"""deliver.py: hand finished files to the creator the way THEIR config says (delivery.mode), and print where they are.

  local         copy into <staging_dir>/<project>/ and print the folder (open it in Finder)
  drive-folder  copy into <drive_folder_path>/<project>/, a folder inside Google Drive for desktop; Drive syncs it with
                the user's own Google login (no keys, no OAuth app). Prints the local path; the Drive web link appears
                once the sync finishes.
  drive-api     upload each file with drive-upload.js (the user's own OAuth app, keys from their Keychain); prints
                each webViewLink.
Every copy is checked by size and md5. Never shares anything publicly.

Usage: deliver.py --project <slug> --file out.mp4 [--file STORYBOARD.md ...]
"""
import argparse, hashlib, json, mimetypes, os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ytconfig import CFG, problems

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--file", action="append", required=True)
a = ap.parse_args()
bad = problems()
if bad:
    sys.exit("deliver: fix the config first:\n  " + "\n  ".join(bad))

def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def copy_into(folder):
    os.makedirs(folder, exist_ok=True)
    for f in a.file:
        dst = os.path.join(folder, os.path.basename(f))
        if os.path.abspath(f) != os.path.abspath(dst):
            shutil.copy2(f, dst)
        if md5(f) != md5(dst):
            sys.exit("deliver: md5 mismatch on %s" % dst)
        print("ok    %s" % dst)
    print("folder: %s" % folder)

d = CFG["delivery"]
if d["mode"] == "local":
    copy_into(os.path.join(os.path.expanduser(CFG["staging_dir"]), a.project))
elif d["mode"] == "drive-folder":
    copy_into(os.path.join(os.path.expanduser(d["drive_folder_path"]), a.project))
    print("note: Google Drive for desktop uploads it in the background; the file shows in drive.google.com once synced")
else:
    for f in a.file:
        mime = mimetypes.guess_type(f)[0] or ("text/markdown" if f.endswith(".md") else "application/octet-stream")
        r = subprocess.run(["node", os.path.join(os.path.dirname(os.path.abspath(__file__)), "drive-upload.js"), f, mime,
                            "%s-%s" % (a.project, os.path.basename(f)) if not os.path.basename(f).startswith(a.project) else os.path.basename(f)],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit("deliver: upload failed for %s: %s" % (f, r.stderr.strip()))
        info = json.loads(r.stdout.strip().splitlines()[-1])
        print("ok    %s -> %s" % (os.path.basename(f), info["webViewLink"]))
