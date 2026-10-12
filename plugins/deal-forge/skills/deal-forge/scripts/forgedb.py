#!/usr/bin/env python3
"""forgedb.py: the local contact database (SQLite, on this Mac only)."""
import json, os, sqlite3, time

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,          -- 'ab:<record>' when the person is in Contacts, else the normalized handle
  name TEXT, first_name TEXT, org TEXT, ab_note TEXT,
  phones TEXT DEFAULT '[]', emails TEXT DEFAULT '[]', groups TEXT DEFAULT '[]',
  msgs_in INTEGER DEFAULT 0, msgs_out INTEGER DEFAULT 0,
  first_at REAL, last_at REAL, last_from_me INTEGER,
  excerpt TEXT,                       -- recent 1:1 messages, newest first, for classification
  scanned_at REAL,
  relationship TEXT, opportunity TEXT, rel_conf REAL, opp_conf REAL,
  summary TEXT, draft TEXT, classified_at REAL, classified_last_at REAL, classify_model TEXT,
  user_edited INTEGER DEFAULT 0,      -- 1 once the user changes tags or the draft: reclassify never overwrites it
  status TEXT DEFAULT 'active',       -- active | snoozed | skipped | dnc
  snooze_until REAL, sent_at REAL,
  ghl_id TEXT, ghl_synced_at REAL, ghl_note_at REAL, ghl_tags TEXT DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY, contact_id INTEGER, at REAL, kind TEXT, detail TEXT
);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""


def connect(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


def log(c, contact_id, kind, detail=""):
    c.execute("INSERT INTO events(contact_id, at, kind, detail) VALUES (?,?,?,?)",
              (contact_id, time.time(), kind, detail if isinstance(detail, str) else json.dumps(detail)))


def meta_get(c, k, default=None):
    r = c.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
    return json.loads(r["v"]) if r else default


def meta_set(c, k, v):
    c.execute("INSERT INTO meta(k, v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, json.dumps(v)))


def due_at(row, cadence):
    """When this person is next due for a reconnect (epoch seconds), or None if never."""
    days = cadence.get(row["relationship"] or "acquaintance", 180)
    if not days:
        return None
    base = max(row["last_at"] or 0, row["sent_at"] or 0)
    return base + days * 86400


PRIORITY = {"seller": 0, "buyer": 0, "investor": 1, "referral": 2}
REL_PRIORITY = {"past_client": 0, "lead": 0, "referral_partner": 1, "agent": 2, "friend": 3, "vendor": 4,
                "acquaintance": 5, "family": 9}


def rank(row):
    """Lower sorts first: opportunities, then relationship strength, then how much you have talked."""
    return (PRIORITY.get(row["opportunity"] or "none", 3), REL_PRIORITY.get(row["relationship"] or "acquaintance", 5),
            -((row["msgs_in"] or 0) + (row["msgs_out"] or 0)))
