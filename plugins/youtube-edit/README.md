# YouTube Editor

- Turns a raw video you recorded into a finished 4K YouTube video: cuts, captions, animated cards, sound.
- Runs on your Mac with your own Claude plan. **Plan on the Max plan:** editing a video uses a lot of Claude, and
  Pro will likely hit its limit partway through.
- Needs about 40 GB free disk and an 800 MB download at setup. Long renders run overnight on older Macs.
- Nothing is posted for you. You review the video and upload it.
- **Full install and how-to guide:** https://github.com/dealsmithrealty/dsr-agent-kit#readme
- Quick version, inside Claude Code:
  - `/plugin marketplace add dealsmithrealty/dsr-agent-kit`
  - `/plugin install youtube-edit@dsr-agent-kit`, then restart Claude Code
  - `/video-setup` once, then `/yt-edit <your video file>`
