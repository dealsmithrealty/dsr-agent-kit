#!/usr/bin/env python3
"""classify.py: sort contacts and draft reconnect texts with the user's OWN Claude (the `claude` CLI they are
signed into). Nothing goes to anyone else's account.

  python3 classify.py --estimate          how many contacts are waiting, and how many Claude calls that is
  python3 classify.py [--limit N]         classify up to N (default classify.limit), best prospects first
  python3 classify.py --ids 4,9           just these contacts (e.g. after the user asks for a fresh draft)

Only people you have NOT texted in quiet_days (default 21) are drafted: an active thread needs no reconnect,
and it gets classified once it goes quiet. Who goes first: people saved in Contacts, then the ones quiet for 60+ days (most likely due), then the ones you
have texted most: strong relationships that went dormant lead the first run. A contact is
reclassified when new messages arrive after its last classification, unless the user edited it by hand.
$FORGE_CLAUDE_BIN overrides the CLI (tests use a stub).
"""
import argparse, json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from forgeconfig import CFG, DB_PATH, SKILL, RELATIONSHIPS, OPPORTUNITIES
import forgedb

CLAUDE = os.environ.get("FORGE_CLAUDE_BIN") or "claude"
DASHES = re.compile(r"\s*[—–]\s*|\s+-\s+")


def pending(db, limit=None, ids=None):
    if ids:
        q = "SELECT * FROM contacts WHERE id IN (%s)" % ",".join("?" * len(ids))
        return db.execute(q, ids).fetchall()
    q = """SELECT * FROM contacts
           WHERE status NOT IN ('dnc', 'skipped') AND user_edited = 0 AND last_at < ?
             AND (classified_last_at IS NULL OR last_at > classified_last_at)
           ORDER BY (name != '') DESC, (last_at < ?) DESC, (msgs_in + msgs_out) DESC"""
    now = time.time()
    rows = db.execute(q, (now - CFG["quiet_days"] * 86400, now - 60 * 86400)).fetchall()
    return rows[:limit] if limit else rows


def build_prompt(db, batch):
    tpl = open(os.path.join(SKILL, "prompts", "classify.md")).read()
    samples = forgedb.meta_get(db, "voice_samples", []) or []
    notes = CFG.get("voice_notes", "").strip()
    fill = {
        "{{AGENT_NAME}}": CFG["agent_name"], "{{AGENT_FIRST}}": CFG["agent_first_name"],
        "{{BROKERAGE}}": CFG.get("brokerage", ""), "{{TODAY}}": time.strftime("%Y-%m-%d"),
        "{{VOICE_NOTES}}": ("- The agent's own notes on their voice: %s\n" % notes) if notes else "",
        "{{VOICE_SAMPLES}}": "\n".join("- " + s.replace("\n", " ") for s in samples) or "(none)",
    }
    for k, v in fill.items():
        tpl = tpl.replace(k, v)
    blocks = []
    now = time.time()
    for r in batch:
        blocks.append(json.dumps({
            "id": r["id"], "name": r["name"] or "(not in Contacts)", "first_name": r["first_name"] or "",
            "contacts_company": r["org"] or "", "contacts_note": r["ab_note"] or "",
            "group_chats": json.loads(r["groups"] or "[]"), "texts_from_them": r["msgs_in"],
            "texts_from_me": r["msgs_out"], "days_since_last": int((now - (r["last_at"] or now)) / 86400),
            "messages_newest_first": r["excerpt"] or "",
        }, ensure_ascii=False))
    return tpl + "\n" + "\n".join(blocks) + "\n"


def parse(text, ids):
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        raise ValueError("no JSON array in the reply")
    out = {}
    for o in json.loads(m.group(0)):
        try:
            cid = int(o["id"])
        except (KeyError, TypeError, ValueError):
            continue
        if cid not in ids:
            continue
        rel = o.get("relationship") if o.get("relationship") in RELATIONSHIPS else "acquaintance"
        opp = o.get("opportunity") if o.get("opportunity") in OPPORTUNITIES else "none"
        draft = DASHES.sub(", ", (o.get("draft") or "").strip())
        if "{{" in draft or rel == "family":
            draft = ""
        out[cid] = dict(relationship=rel, opportunity=opp,
                        rel_conf=max(0.0, min(1.0, float(o.get("rel_conf") or 0))),
                        opp_conf=max(0.0, min(1.0, float(o.get("opp_conf") or 0))),
                        summary=(o.get("summary") or "").strip()[:240], draft=draft[:400])
    return out


def call_claude(prompt):
    model = CFG["classify"]["model"]
    cmd = [CLAUDE, "-p", "--model", model, "--tools", "", "--strict-mcp-config", "--no-session-persistence",
           "--output-format", "text"]
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[:400] or "claude exited %d" % r.returncode)
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--ids", default="")
    ap.add_argument("--estimate", action="store_true")
    a = ap.parse_args()
    db = forgedb.connect(DB_PATH)
    bs = int(CFG["classify"]["batch_size"])
    ids = [int(x) for x in a.ids.split(",") if x.strip()]
    if a.estimate:
        total = len(pending(db))
        lim = a.limit or CFG["classify"]["limit"]
        n = min(total, lim)
        print("waiting %d; this run would classify %d in %d Claude calls (%s, about %d min)"
              % (total, n, -(-n // bs), CFG["classify"]["model"], max(1, -(-n // bs) * 40 // 60)))
        return 0
    rows = pending(db, a.limit or CFG["classify"]["limit"], ids)
    if not rows:
        print("ok    nothing to classify")
        return 0
    done = failed = 0
    for i in range(0, len(rows), bs):
        batch = rows[i:i + bs]
        want = {r["id"]: r for r in batch}
        try:
            res = parse(call_claude(build_prompt(db, batch)), set(want))
        except Exception as e:
            failed += len(batch)
            print("warn  batch %d failed: %s" % (i // bs + 1, e), file=sys.stderr)
            continue
        now = time.time()
        for cid, v in res.items():
            db.execute("""UPDATE contacts SET relationship=:relationship, opportunity=:opportunity, rel_conf=:rel_conf,
                          opp_conf=:opp_conf, summary=:summary, draft=:draft, classified_at=:now,
                          classified_last_at=last_at, classify_model=:model WHERE id=:id""",
                       dict(v, now=now, model=CFG["classify"]["model"], id=cid))
            forgedb.log(db, cid, "classified", {"relationship": v["relationship"], "opportunity": v["opportunity"]})
        db.commit()
        done += len(res)
        failed += len(batch) - len(res)
        print("ok    %d/%d classified" % (done, len(rows)), flush=True)
    print("done  %d classified, %d failed" % (done, failed))
    return 1 if done == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
