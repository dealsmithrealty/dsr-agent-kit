#!/usr/bin/env python3
"""scan.py: read this Mac's Messages history (read-only) and build the list of people you actually text.

  python3 scan.py --check     can we read Messages? (exit 2 = Full Disk Access is missing, with the fix)
  python3 scan.py             scan into the local database; prints a summary

What counts as a person: a 1:1 thread where BOTH sides wrote (min_messages in total), inside lookback_days.
Short codes (2FA, alerts, businesses) and one-way blasts drop out by that rule. People saved in Contacts are
merged across their phone numbers and emails. Group chats only add the group names to the person's record.

chat.db rules (each one cost a real bug before):
- join messages to chats through chat_message_join: your own sent messages have handle_id 0
- bind the date cutoff as an Apple-epoch nanosecond NUMBER; never compare m.date to a strftime string
- the text often lives only in attributedBody
- open with mode=ro (never immutable, which hides the newest messages in the WAL)
- tapbacks (associated_message_type != 0) and group events (item_type != 0) are not messages
"""
import argparse, json, os, re, sqlite3, sys, time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from forgeconfig import CFG, DB_PATH
import forgedb

HOME = os.path.expanduser("~")
CHAT_DB = os.environ.get("FORGE_CHAT_DB") or os.path.join(HOME, "Library/Messages/chat.db")
AB_ROOT = os.path.join(HOME, "Library/Application Support/AddressBook")
APPLE_EPOCH = 978307200
NS = 1000000000
FDA_HELP = """Claude can't read your Messages yet. macOS needs to allow it once:
  1. Open System Settings > Privacy & Security > Full Disk Access.
  2. Turn it on for the app you run Claude Code in (Terminal, iTerm, Visual Studio Code, Cursor or Claude).
     If it is not listed, click +, find it in Applications, and add it.
  3. Quit that app completely (Cmd+Q) and open it again, then run this step again.
Also: on your iPhone, Settings > [your name] > iCloud > Messages should be ON, and the same on this Mac
(Messages > Settings > iMessage > Enable Messages in iCloud), so this Mac has your full texting history."""


def open_ro(path):
    return sqlite3.connect("file:%s?mode=ro" % path, uri=True)


def norm_handle(h):
    """+15125550100 for US phones, lowercase for emails, '' for short codes."""
    h = (h or "").strip()
    if "@" in h:
        return h.lower()
    d = re.sub(r"\D", "", h)
    if len(d) == 10:
        return "+1" + d
    if len(d) == 11 and d.startswith("1"):
        return "+" + d
    if len(d) > 11:
        return "+" + d
    return ""


def last10(h):
    d = re.sub(r"\D", "", h or "")
    return d[-10:] if len(d) >= 10 else ""


def decode_attributed_body(blob):
    if not blob:
        return ""
    try:
        s = bytes(blob).split(b"NSString", 1)[1][5:]
        if s[0] == 0x81:
            n = int.from_bytes(s[1:3], "little")
            s = s[3:3 + n]
        else:
            s = s[1:1 + s[0]]
        return s.decode("utf-8", "replace").replace("￼", "").strip()
    except Exception:
        return ""


def find_ab_db():
    if os.environ.get("FORGE_AB_DB"):
        return os.environ["FORGE_AB_DB"]
    best = (0, None)
    for root, _dirs, files in os.walk(AB_ROOT):
        if "AddressBook-v22.abcddb" in files:
            p = os.path.join(root, "AddressBook-v22.abcddb")
            try:
                with open_ro(p) as c:
                    n = c.execute("SELECT count(*) FROM ZABCDPHONENUMBER").fetchone()[0]
                best = max(best, (n, p), key=lambda x: x[0])
            except sqlite3.Error:
                continue
    return best[1]


def load_book(path):
    """phone last-10 / email -> record id, and record id -> {first, last, org, note}."""
    by_handle, people = {}, {}
    if not path:
        return by_handle, people
    with open_ro(path) as c:
        for pk, first, last, org in c.execute(
                "SELECT Z_PK, COALESCE(ZFIRSTNAME,''), COALESCE(ZLASTNAME,''), COALESCE(ZORGANIZATION,'') FROM ZABCDRECORD"):
            people[pk] = {"first": first.strip(), "last": last.strip(), "org": org.strip(), "note": ""}
        for num, owner in c.execute("SELECT ZFULLNUMBER, ZOWNER FROM ZABCDPHONENUMBER"):
            k = last10(num)
            if k and owner in people:
                by_handle.setdefault(k, owner)
        try:
            for addr, owner in c.execute("SELECT ZADDRESS, ZOWNER FROM ZABCDEMAILADDRESS"):
                if addr and owner in people:
                    by_handle.setdefault(addr.strip().lower(), owner)
        except sqlite3.Error:
            pass
        try:
            for owner, text in c.execute("SELECT ZCONTACT, ZTEXT FROM ZABCDNOTE WHERE ZTEXT IS NOT NULL"):
                if owner in people:
                    people[owner]["note"] = text.strip()[:500]
        except sqlite3.Error:
            pass
    return by_handle, people


def check():
    try:
        with open_ro(CHAT_DB) as c:
            n = c.execute("SELECT count(*) FROM message").fetchone()[0]
    except sqlite3.Error as e:
        print("FAIL  cannot read %s (%s)\n\n%s" % (CHAT_DB, e, FDA_HELP))
        return 2
    if n == 0:
        print("FAIL  Messages history is empty on this Mac.\n\n" + FDA_HELP.split("Also: ", 1)[1])
        return 2
    print("ok    Messages readable: %d messages on this Mac" % n)
    ab = find_ab_db()
    print("ok    Contacts: %s" % ("found" if ab else "none found (names will show as phone numbers)"))
    return 0


def scan():
    cutoff_unix = time.time() - CFG["lookback_days"] * 86400
    cutoff_apple_ns = int((cutoff_unix - APPLE_EPOCH) * NS)
    by_handle, people = load_book(find_ab_db())

    def person_key(handle):
        k = handle if "@" in handle else last10(handle)
        rec = by_handle.get(k)
        return ("ab:%d" % rec, rec) if rec is not None else (handle, None)

    agg = defaultdict(lambda: {"in": 0, "out": 0, "first": None, "last": None, "last_from_me": None,
                               "msgs": [], "phones": set(), "emails": set(), "groups": set(), "rec": None})
    voice = []
    with open_ro(CHAT_DB) as c:
        handles = dict(c.execute("SELECT ROWID, id FROM handle"))
        group_members = defaultdict(list)
        for chat_id, hid in c.execute("SELECT chat_id, handle_id FROM chat_handle_join"):
            group_members[chat_id].append(handles.get(hid, ""))
        rows = c.execute(
            """SELECT m.date, m.is_from_me, m.text, m.attributedBody, ch.ROWID, ch.chat_identifier, ch.style,
                      COALESCE(ch.display_name, '')
               FROM message m
               JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
               JOIN chat ch ON ch.ROWID = cmj.chat_id
               WHERE m.date > ? AND COALESCE(m.associated_message_type, 0) = 0 AND COALESCE(m.item_type, 0) = 0
               ORDER BY m.date""", (cutoff_apple_ns,))
        seen_groups = set()
        for date, from_me, text, body, chat_id, ident, style, gname in rows:
            ts = date / NS + APPLE_EPOCH if date > 1e12 else date + APPLE_EPOCH
            if style == 43:   # group chat: remember the group on each member, nothing more
                if chat_id not in seen_groups:
                    seen_groups.add(chat_id)
                    label = gname or "group of %d" % (len(group_members[chat_id]) + 1)
                    for h in group_members[chat_id]:
                        nh = norm_handle(h)
                        if nh:
                            agg[person_key(nh)[0]]["groups"].add(label)
                continue
            nh = norm_handle(ident)
            if not nh:
                continue
            key, rec = person_key(nh)
            a = agg[key]
            a["rec"] = rec
            (a["emails"] if "@" in nh else a["phones"]).add(nh)
            msg = (text or "").strip() or decode_attributed_body(body)
            if not msg:
                continue
            a["out" if from_me else "in"] += 1
            a["first"] = a["first"] or ts
            a["last"] = ts
            a["last_from_me"] = 1 if from_me else 0
            a["msgs"].append((ts, from_me, msg))
            if len(a["msgs"]) > 40:
                del a["msgs"][0]
            if from_me and 25 <= len(msg) <= 220 and "http" not in msg:
                voice.append((ts, msg))

    db = forgedb.connect(DB_PATH)
    now = time.time()
    kept = new = 0
    for key, a in agg.items():
        if a["in"] < 1 or a["out"] < 1 or a["in"] + a["out"] < CFG["min_messages"]:
            continue
        kept += 1
        p = people.get(a["rec"], {}) if a["rec"] is not None else {}
        name = " ".join(x for x in (p.get("first"), p.get("last")) if x) or p.get("org") or ""
        lines, size = [], 0
        for ts, me, msg in reversed(a["msgs"][-30:]):
            line = "%s %s: %s" % (time.strftime("%Y-%m-%d", time.localtime(ts)), "Me" if me else "Them", msg[:300])
            size += len(line)
            if size > 4000:
                break
            lines.append(line)
        vals = dict(key=key, name=name, first_name=p.get("first") or "", org=p.get("org") or "",
                    ab_note=p.get("note") or "", phones=json.dumps(sorted(a["phones"])),
                    emails=json.dumps(sorted(a["emails"])), groups=json.dumps(sorted(a["groups"])[:10]),
                    msgs_in=a["in"], msgs_out=a["out"], first_at=a["first"], last_at=a["last"],
                    last_from_me=a["last_from_me"], excerpt="\n".join(lines), scanned_at=now)
        if name and name.lower() == (CFG.get("agent_name") or "").strip().lower():
            continue   # the agent's own number or email (notes-to-self, forwarded lead alerts)
        cur = db.execute("SELECT id FROM contacts WHERE key=?", (key,)).fetchone()
        if cur:
            sets = ", ".join("%s=:%s" % (k, k) for k in vals if k != "key")
            db.execute("UPDATE contacts SET %s WHERE key=:key" % sets, vals)
        else:
            new += 1
            cols = ", ".join(vals)
            db.execute("INSERT INTO contacts(%s) VALUES (%s)" % (cols, ", ".join(":" + k for k in vals)), vals)
    voice.sort(reverse=True)
    forgedb.meta_set(db, "voice_samples", [m for _t, m in voice[:15]])
    forgedb.meta_set(db, "last_scan", {"at": now, "people": kept, "new": new})
    db.commit()
    stale = db.execute("SELECT count(*) FROM contacts WHERE classified_last_at IS NULL OR last_at > classified_last_at"
                       ).fetchone()[0]
    print("ok    scanned %d people you text (%d new); %d need classifying" % (kept, new, stale))
    print("db    %s" % DB_PATH)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        sys.exit(check())
    rc = check()
    if rc:
        sys.exit(rc)
    sys.exit(scan())
