#!/usr/bin/env python3
"""store_secret.py <account> [prompt]: ask for a secret in a private macOS dialog and save it in the user's OWN
Keychain (service from the config, default "deal-forge"). The value never appears in the chat, the shell history
or the process list. Prints only ok/cancelled.
"""
import os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from forgeconfig import CFG

acct = sys.argv[1] if len(sys.argv) > 1 else CFG["ghl"]["token_key"]
prompt = sys.argv[2] if len(sys.argv) > 2 else "Paste your GoHighLevel Private Integration token"
svc = CFG["ghl"]["keychain_service"]
script = ('display dialog "%s" with title "Deal Forge" default answer "" with hidden answer '
          'buttons {"Cancel", "Save"} default button "Save"\ntext returned of result') % prompt.replace('"', "'")
r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
val = r.stdout.strip()
if r.returncode != 0 or not val:
    print("cancelled: nothing saved")
    sys.exit(1)
if any(c in val for c in '"\\\n'):
    print("that value has characters a token never has; nothing saved")
    sys.exit(1)
# security -i reads the command from stdin, so the secret is never a command-line argument
cmd = 'add-generic-password -U -s "%s" -a "%s" -w "%s"\n' % (svc, acct, val)
r = subprocess.run(["security", "-i"], input=cmd, capture_output=True, text=True)
if r.returncode != 0:
    print("could not save to Keychain: %s" % (r.stderr.strip() or r.returncode))
    sys.exit(1)
print("ok    saved to your Keychain (service %s, account %s)" % (svc, acct))
