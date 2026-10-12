---
description: Edit a YouTube video with the youtube-edit skill (preflight, cut, compose, render, deliver)
argument-hint: <folder or video file>
---

Use the **youtube-edit** skill on: $ARGUMENTS

Run it in this order and do not skip steps:

1. **Config.** `python3 "$SK/scripts/ytconfig.py" check` (`SK` = the skill's base directory). Exit 1 = run
   `/video-setup` first and stop. Read `~/.config/youtube-edit/MY-RULES.md` when it exists.
2. **Locate the footage.** `$ARGUMENTS` is a file or a folder. Copy it into `<workdir>/videos/<project>/raw/` and confirm
   the copy (size + ffprobe duration) before touching it. Pick `<project>` as a short kebab-case slug and say it.
3. **Set the variables** from the skill's "First run" block and `cd` into the working folder.
4. **Preflight:** `bash "$SK/scripts/preflight.sh" "$W"`. If it prints `preflight: STOP`, report the FAIL lines and stop.
5. **Pick the route** from the skill's routes table.
6. **Checkpoint A (the cut):** produce `PAPER-CUT.md` and stop for the creator's answer before composing.
7. **Checkpoint B (the plan):** `storyboard.json` + `snaps/sheet.png` + `QA.md`; stop for the creator's answer before
   rendering. The brokerage rules apply: broker name on screen, nothing fabricated, no meeting attendees without
   permission, Fair Housing-safe B-roll.
8. **Render** with the config's render settings. On an 8 GB Mac anything over a minute of footage is an overnight job:
   say so and let it run.
9. **Verify** with `verify-render.py` (exit 1 = do not deliver).
10. **Deliver** with `deliver.py` and report where it landed. Include the description checklist (broker name, IABS
    link, TREC Consumer Protection Notice).
11. **Offer** OpusClip Shorts only when `connectors.opusclip` is true (never post or schedule without an explicit yes),
    and "save this to the skill" for any note worth keeping.
