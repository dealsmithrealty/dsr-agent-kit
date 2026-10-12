# Deal Forge for Claude Code

Finds everyone you've ever texted, sorts them (past clients, leads, referral partners, agents, vendors, friends,
family), writes a short "been a while" text for each one in your voice, and shows you who to reach out to today.
One tap opens the text in Messages; you hit send.

It runs on **your** Mac with **your** Claude account. Your messages never leave your computer except to your own
Claude for the sorting. Nothing is ever sent without you pressing send.

## What you need

- A Mac with your texts on it: turn on **Messages in iCloud** on your iPhone and on the Mac
  (iPhone: Settings > your name > iCloud > Messages).
- Claude Code, signed in with your own Claude plan.
- Recommended: a GoHighLevel account, so these people land in your CRM. Don't have one? The Deal Smith Realty Agent
  Package includes it, with a 30-day free trial: https://buy.stripe.com/14AaEQ2eM6hZ4Wu96a2VG0e
  No GHL yet is fine: you get a spreadsheet instead, and can import it later.

## Install (once)

In Claude Code:

```
/plugin marketplace add dealsmithrealty/dsr-agent-kit
/plugin install deal-forge@dsr-agent-kit
```

Restart Claude Code, then type `/forge-setup`. It walks you through:

1. Letting Claude read your Messages (one switch in System Settings > Privacy & Security > Full Disk Access).
2. Your name and brokerage.
3. Connecting GoHighLevel (a token you paste into a private pop-up, never into the chat), or skipping it.

## Use it

Type `/forge`. The first run reads your texts (seconds), sorts up to 300 people (a few minutes of your Claude
usage), and opens your dashboard. Each card shows who the person is, how long it's been, and a draft text:

- **Open in Messages**: the text is filled in, you press send.
- Change the tags or the text right on the card; your edits are kept.
- **Mark sent**, **Snooze 30d**, **Skip**, or **Do not contact** (they will never show up again).

Run `/forge` every week or so. It picks up new texts and tells you who's due.

## Privacy

Your contact list lives in one file on your Mac (`~/.local/share/deal-forge/forge.db`). The dashboard only answers
on your own computer. Your GHL token sits in your Mac's Keychain.
