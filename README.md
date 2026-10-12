# Deal Smith Realty Agent Kit

Two AI tools that run on **your own Mac** with **your own accounts**:

- **Deal Forge**: reads your text history, sorts everyone you've texted (past clients, leads, referral partners,
  agents, vendors, friends, family), drafts a short "been a while" text for each one, and shows you who to reach out
  to today.
- **YouTube Editor**: turns a raw video you recorded into a finished 4K YouTube video (cuts, captions, animated
  cards, sound).

This guide covers everything from a blank Mac. Follow it top to bottom.

---

## Before you start

- **You need a Mac.** These tools don't run on Windows or an iPad.
- **You need a paid Claude plan** (claude.ai > your name > Settings > Billing). Pick based on what you'll use:
  - **Deal Forge only:** the **Pro** plan is usually enough. The first scan uses the most; weekly runs after that
    are light.
  - **YouTube Editor:** plan on the **Max** plan. Editing a video uses a lot of Claude, and Pro will likely hit its
    limit partway through a video.
  - Both run on your plan and your usage only. Nothing is billed to anyone else.
- **Disk space:** Deal Forge needs almost none. The YouTube Editor needs about 40 GB free.
- **Time:** about 15 minutes for setup.

---

## Step 1: Open Terminal

- Press **Cmd + Space**, type **Terminal**, press **Return**.
- A window with a text prompt opens. That's where you'll paste the commands below.
- To paste: **Cmd + V**, then press **Return**.

## Step 2: Install Claude Code

- Paste this into Terminal and press Return:
  ```
  curl -fsSL https://claude.ai/install.sh | bash
  ```
- Wait for it to say it's finished (about a minute).
- **Close Terminal completely (Cmd + Q) and open it again.**
- Check it worked: type `claude --version` and press Return. You should see a version number.
  - If you see "command not found", close and reopen Terminal once more, then try again.

## Step 3: Sign in to Claude

- In Terminal, type `claude` and press Return.
- Pick a color theme (any is fine) and press Return.
- Choose **Claude account with subscription** (your Pro or Max plan).
- Your browser opens. Sign in with your Claude account and click **Authorize**.
- Go back to Terminal. You're now inside Claude Code; you'll see a box where you can type.
- If it asks whether you trust the folder, choose **Yes**.

## Step 4: Add the Agent Kit

- Inside Claude Code (the box from Step 3), paste this and press Return:
  ```
  /plugin marketplace add dealsmithrealty/dsr-agent-kit
  ```
- Then install the tools you want (one line at a time):
  - Deal Forge:
    ```
    /plugin install deal-forge@dsr-agent-kit
    ```
  - YouTube Editor:
    ```
    /plugin install youtube-edit@dsr-agent-kit
    ```
- **Quit Claude Code** (type `/exit` and press Return), then type `claude` and press Return to start it again.
  The tools load on restart.

---

## Deal Forge

### Set it up (once)

- In Claude Code, type `/forge-setup` and press Return. Claude walks you through each step and waits for you.
- **Letting Claude read your texts.** macOS asks you to allow this once:
  - Open **System Settings > Privacy & Security > Full Disk Access**.
  - Turn on **Terminal** (or whichever app you run Claude Code in). If it's not listed, click **+**, open
    **Applications > Utilities**, pick **Terminal**.
  - **Quit Terminal (Cmd + Q) and reopen it**, type `claude`, then `/forge-setup` again.
- **Make sure your Mac has your full text history:**
  - iPhone: **Settings > [your name] > iCloud > Messages > On**.
  - Mac: **Messages app > Settings > iMessage > Enable Messages in iCloud**.
  - A first sync can take an hour or more. Run setup again afterward if it found very few texts.
- **Your details:** your name, how you sign your texts, and your brokerage.
- **GoHighLevel (recommended):**
  - **Have GHL?** In your GHL account go to **Settings > Private Integrations > Create new integration**, name it
    **Deal Forge**, check **View Contacts**, **Edit Contacts** and **View Locations**, click create, and copy the
    token. Claude opens a private pop-up; paste the token there (never into the chat). Then paste your GHL web
    address when asked; Claude takes the account ID from it.
  - **No GHL?** Get it through the Deal Smith Realty Agent Package, with a 30-day free trial:
    https://buy.stripe.com/14AaEQ2eM6hZ4Wu96a2VG0e
  - Not ready for GHL yet? Skip it. Deal Forge still works and saves a spreadsheet you can import into GHL later.

### Use it

- Type `/forge` and press Return.
- **First run:** reads your texts (seconds), then sorts up to 300 people and drafts their texts (about 20 to 40
  minutes). Leave it running.
- Your **dashboard** opens in your browser when it's ready. Each card shows:
  - who the person is to you, and how long since you last texted
  - a draft text, written in your voice
- On each card:
  - **Open in Messages**: the text is filled in. Read it, change anything, press send.
  - Change the tags or the text right on the card. Your changes are kept.
  - **Mark sent**, **Snooze 30d**, **Skip**, or **Do not contact** (they never come back).
- **Always read a draft before sending.** If you're in the middle of a deal with someone, the draft may mention it.
  Make sure it says what you mean.
- **Run `/forge` about once a week.** It picks up new texts and shows who's due.
- **Who comes up when** (after your last text either way): leads 21 days, referral partners 60, friends 75, past
  clients 90, agents 120, vendors and acquaintances 180, family never.
- **Nothing is ever sent for you.** You press send in Messages every time.
- **Spreadsheet:** `Documents > Deal Forge > deal-forge-contacts.csv` (updated when you run `/forge`).

---

## YouTube Editor

### Set it up (once)

- In Claude Code, type `/video-setup` and press Return.
- Claude checks what your Mac needs and **asks before installing anything**. Say yes to each one. If Homebrew asks
  for your Mac password in Terminal, type it (you won't see the letters) and press Return.
- It asks for your name, your brokerage, your IABS link (the Information About Brokerage Services form link from
  your email signature), and where finished videos should go:
  - a folder on your Mac (default), or
  - your Google Drive, if you have **Google Drive for desktop** installed and signed in.
- It downloads about 800 MB the first time.

### Recording tips

- Record in **4K at 30 fps**, with the mic on.
- **Messed up a line?** Pause two seconds and say the whole sentence again from the start. The last take wins.
- Say numbers in full ("a thousand dollars a month") and say tool names out loud.

### Use it

- Type `/yt-edit ` followed by your video's location, then press Return. Easy way: type `/yt-edit `, then drag the
  video file from Finder into the Terminal window.
- Claude stops twice for you:
  - **The cut:** what it plans to remove. Answer in plain words, e.g. "keep the first take of the pricing line".
  - **The plan:** a sheet of every card and caption. Say what to change, or "looks good".
- Then it renders. **A 10-minute video can take several hours on an older Mac.** Start it before bed.
- Your broker name goes on screen, and you get an upload checklist (broker name, IABS link, TREC Consumer
  Protection Notice).
- **Nothing is posted for you.** You review the video and upload it yourself.
- Want a change to stick for every future video? Say **"save this to the skill"** after your note.

---

## If something goes wrong

- **Ask Claude first.** In Claude Code, describe what happened or paste the error and say "help me fix this". It
  can see your setup and usually fixes it on the spot.
- **"command not found: claude":** quit Terminal (Cmd + Q), reopen it, try again.
- **"Can't read your Messages":** Full Disk Access is off for the app you're using (see Deal Forge setup), or you
  didn't quit and reopen Terminal after turning it on.
- **Very few people found:** Messages in iCloud is off on your iPhone or Mac, or the history is still downloading.
- **"Usage limit reached":** your Claude plan ran out for now. Wait until it resets (Claude tells you when), or move
  up a plan. For video, that usually means Max.
- **Tools don't show up after installing:** type `/exit`, then `claude` to restart.
- **Get the latest version:** in Claude Code, type `/plugin marketplace update dsr-agent-kit`, then restart.
- **Start setup over:** run `/forge-setup` or `/video-setup` again. It re-checks everything and keeps what's
  already done.

---

## Privacy

- Everything runs on your Mac under your own accounts: your Claude plan, your Messages, your GoHighLevel, your
  Google Drive.
- Your texts are only read on your Mac and sent to **your own** Claude to sort them. They're never shared with
  Deal Smith Realty or anyone else.
- Tokens and passwords go into your Mac's Keychain, never into a file or the chat.
- These tools are provided as-is.
