# YouTube Editor for Claude Code

Turns a raw video you recorded (mistakes, retakes and all) into a finished 4K YouTube video: the cut, animated text
and cards in the Deal Smith Realty look, camera moves, sound, and a final check. It runs on **your** Mac, with **your**
Claude account. Your footage never leaves your computer unless you choose Google Drive delivery.

## What you need

- A Mac (Apple Silicon or Intel) with about 40 GB free disk. 16 GB of RAM or more renders much faster.
- Claude Code, signed in with **your own** Claude plan. Max is recommended; Pro runs out on long videos.
- About 10 minutes for setup, plus an 800 MB download (the video engine and the speech transcriber).
- Optional: Google Drive for desktop (to get finished videos in your Drive), your own OpusClip account (for Shorts).

Nothing here uses Derek's accounts, keys or Claude usage. Everything is set up under yours.

## Install (once)

In Claude Code, type these one at a time:

```
/plugin marketplace add dealsmithrealty/dsr-video-kit
/plugin install youtube-edit@dsr-video-kit
```

Restart Claude Code, then type:

```
/video-setup
```

Claude checks what your Mac needs and asks before installing anything. Then it asks for your name, your brokerage,
your IABS link, and where finished videos should go. Your answers are saved to `~/.config/youtube-edit/config.json` on
your Mac only.

## Edit a video

```
/yt-edit ~/Movies/my-video.mov
```

Claude stops twice for you:

1. **The cut.** It shows what it plans to remove (fluffed lines, retakes, long pauses). Answer in plain words, e.g.
   "keep the first take of the pricing line".
2. **The plan.** It shows a contact sheet of every card and caption. Say what to change.

Then it renders. A 10-minute video can take a few hours on an older Mac, so let it run overnight.

## Recording tips that make the edit better

- Record in 4K at 30 fps with the mic on.
- Fluff a line? Pause two seconds and restart the whole sentence. The last take wins.
- Say numbers in full ("a thousand dollars a month") and name tools out loud, so logos and cards appear.

## Rules it follows for you

- Your broker name appears on screen on any video that promotes real estate services (TREC).
- Every upload checklist includes your IABS link and the TREC Consumer Protection Notice.
- It never invents numbers, testimonials or clients, and never shows people from meetings without their permission.
- It never posts anything. You review and upload.

## Make it yours

When you give a note during an edit ("the text is too small"), add **"save this to the skill"**. Claude writes it into
`~/.config/youtube-edit/MY-RULES.md`, and every future edit follows it. Plugin updates never erase it.

## Updates and help

- Get the latest version: `/plugin marketplace update dsr-video-kit`
- Something broken? Run `/video-setup` again; it re-checks everything. Still stuck, send Derek the last screen of output.
