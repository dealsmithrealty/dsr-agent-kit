---
description: Set up the YouTube editor on this Mac with YOUR accounts (tools, brand, broker, delivery, optional connectors)
---

Use the **youtube-edit** skill. Set it up for the person at this keyboard, on this Mac, with **their own** accounts only.
Talk to them in plain English: they are a real estate agent, not a developer. One question at a time; offer the default.

Ground rules:
- Never use, copy or ask for anyone else's keys, Drive folders, Keychain entries or accounts. If you find a config,
  Keychain service or connector that belongs to someone else (e.g. Keychain service `claude-creds`, a Drive folder they
  did not create, an OpusClip account that is not theirs), stop and tell them.
- Never install anything without a yes. Never paste a secret into chat or a file: secrets go into THEIR Keychain with
  `security add-generic-password -U -s youtube-edit -a <key> -w` (run it so the prompt asks them, never echo the value).
- `SK` = this skill's base directory. Config path: `python3 "$SK/scripts/ytconfig.py" path`.

Steps:

1. **Claude account.** Confirm they are signed into Claude Code with their own Claude plan (a Max plan is recommended;
   Pro runs out on long videos). This editor uses their usage, nobody else's.
2. **Tools.** Run `bash "$SK/scripts/setup-toolchain.sh" --check`. For each `MISS` line, say what it is in one sentence
   and ask before running its install command, one at a time. Homebrew asks for their Mac password in the terminal.
3. **Their details** (write `config.json` from `$SK/config.example.json`):
   - `creator_name`: their name as it should appear.
   - `compliance.broker_name`: the brokerage they are licensed under (ask; e.g. "Deal Smith Realty" or "Interweb
     Realty"). `compliance.enabled` stays true for any real estate content.
   - `compliance.iabs_url`: the link to THEIR Information About Brokerage Services form. If they do not have one handy,
     leave it empty; the skill asks again before the first upload. Never make one up.
   - `compliance.consumer_protection_url`: keep the TREC default.
   - `brand`: keep the Deal Smith Realty gold unless they want their own colours (three hex colours: highlight, anchor,
     punchline).
4. **Where finished videos go** (`delivery.mode`):
   - `local` (default): a folder on this Mac, `~/Movies/YouTube Renders/<video>/`.
   - `drive-folder` (recommended if they use Google Drive): look for `~/Library/CloudStorage/GoogleDrive-*`. If it
     exists, make `<that>/My Drive/YouTube Renders` and set `delivery.drive_folder_path` to it. If not, offer Google
     Drive for desktop (google.com/drive/download), signed in with THEIR Google account, then come back. No keys needed.
   - `drive-api`: only for someone who already runs their own Google Cloud OAuth app. Store their three keys in their
     Keychain under service `youtube-edit` and fill `delivery.drive_api`.
5. **Render settings.** Read RAM with `sysctl -n hw.memsize`: 8 GB or less = workers 1, heap_mb 6144; 16 GB = 2, 8192;
   32 GB or more = 4, 12288. Leave `gpu` false.
6. **Optional accounts, all off by default** (ask about each; each is THEIR account or nothing):
   - OpusClip, for Shorts: they connect their own OpusClip in Claude (claude.ai > Settings > Connectors). Check with
     `opusclip_whoami` that it is their account, then set `connectors.opusclip` true.
   - Epidemic Sound or Tella: same pattern, only if they already pay for one. The free sound library needs no account.
7. **Build the working folder:** ask, then run `bash "$SK/scripts/setup-toolchain.sh"` (downloads about 800 MB: the
   video engine and the 640 MB transcriber; it ends by running the tests, which must say OK).
8. **Create `~/.config/youtube-edit/MY-RULES.md`** if missing, with a one-line header: "My saved editing notes. Say
   'save this to the skill' during an edit and Claude adds a rule here."
9. **Check:** `python3 "$SK/scripts/ytconfig.py" check` and `bash "$SK/scripts/preflight.sh"` must both pass. Report
   what is set up in five lines or fewer, then: "Drop a video file in and say /yt-edit <file> to start."
