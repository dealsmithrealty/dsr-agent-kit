#!/usr/bin/env python3
"""dashboard.py: the reconnect dashboard, served on this Mac only (127.0.0.1).

  python3 dashboard.py [--port N] [--open]

Reads and writes the local database. "Open in Messages" hands the draft to the Messages app on this Mac; the user
presses send there. Nothing is ever sent from here.
"""
import argparse, json, os, re, sys, threading, time, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from forgeconfig import CFG, DB_PATH, RELATIONSHIPS, OPPORTUNITIES
import forgedb

HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")
LOCK = threading.Lock()


def shape(r, now):
    phones, emails = json.loads(r["phones"] or "[]"), json.loads(r["emails"] or "[]")
    to = (phones or emails or [""])[0]
    due = forgedb.due_at(r, CFG["cadence_days"])
    return {
        "id": r["id"], "name": r["name"] or to, "first_name": r["first_name"], "org": r["org"],
        "to": to, "phones": phones, "emails": emails, "relationship": r["relationship"],
        "opportunity": r["opportunity"], "rel_conf": r["rel_conf"], "summary": r["summary"] or "",
        "draft": r["draft"] or "", "status": r["status"], "user_edited": r["user_edited"],
        "days_since": int((now - max(r["last_at"] or 0, r["sent_at"] or 0)) / 86400),
        "last_from_me": r["last_from_me"], "msgs": (r["msgs_in"] or 0) + (r["msgs_out"] or 0),
        "due_in_days": None if due is None else int((due - now) / 86400),
        "sms": "sms:%s&body=%s" % (to, quote(r["draft"] or "")) if to else "",
        "ghl": bool(r["ghl_id"]),
    }


def listing(view, rel, opp, q):
    now = time.time()
    with LOCK:
        db = forgedb.connect(DB_PATH)
        rows = db.execute("SELECT * FROM contacts WHERE classified_at IS NOT NULL").fetchall()
    out, counts = [], {"due": 0, "upcoming": 0, "all": 0, "hidden": 0}
    by_rel = {}
    for r in rows:
        hidden = r["status"] in ("skipped", "dnc") or (r["status"] == "snoozed" and (r["snooze_until"] or 0) > now)
        due = forgedb.due_at(r, CFG["cadence_days"])
        bucket = "hidden" if hidden else ("due" if due is not None and due <= now else
                                          "upcoming" if due is not None and due <= now + 30 * 86400 else "later")
        counts["hidden" if hidden else "all"] += 1
        if bucket in ("due", "upcoming"):
            counts[bucket] += 1
        if bucket == "due":
            by_rel[r["relationship"]] = by_rel.get(r["relationship"], 0) + 1
        if view == "all" and hidden:
            continue
        if view in ("due", "upcoming", "hidden") and bucket != view:
            continue
        if rel and r["relationship"] != rel:
            continue
        if opp and r["opportunity"] != opp:
            continue
        if q and q.lower() not in " ".join([r["name"] or "", r["summary"] or "", r["phones"] or "",
                                            r["emails"] or "", r["org"] or ""]).lower():
            continue
        out.append(r)
    out.sort(key=forgedb.rank)
    return {"contacts": [shape(r, now) for r in out[:300]], "total": len(out), "counts": counts,
            "due_by_relationship": by_rel, "relationships": RELATIONSHIPS, "opportunities": OPPORTUNITIES,
            "agent": CFG["agent_first_name"], "ghl": CFG["ghl"]["enabled"],
            "last_scan": None}


def update(cid, body):
    sets, vals = [], {"id": cid}
    if "relationship" in body and body["relationship"] in RELATIONSHIPS:
        sets.append("relationship=:relationship"); vals["relationship"] = body["relationship"]
    if "opportunity" in body and body["opportunity"] in OPPORTUNITIES:
        sets.append("opportunity=:opportunity"); vals["opportunity"] = body["opportunity"]
    if "draft" in body and isinstance(body["draft"], str):
        sets.append("draft=:draft"); vals["draft"] = body["draft"][:1000]
    if not sets:
        return False
    with LOCK:
        db = forgedb.connect(DB_PATH)
        db.execute("UPDATE contacts SET %s, user_edited=1 WHERE id=:id" % ", ".join(sets), vals)
        forgedb.log(db, cid, "edited", {k: v for k, v in vals.items() if k != "id"})
        db.commit()
    return True


def action(cid, act):
    now = time.time()
    q = {"sent": ("UPDATE contacts SET sent_at=?, status='active' WHERE id=?", (now, cid)),
         "snooze": ("UPDATE contacts SET status='snoozed', snooze_until=? WHERE id=?", (now + 30 * 86400, cid)),
         "skip": ("UPDATE contacts SET status='skipped' WHERE id=?", (cid,)),
         "dnc": ("UPDATE contacts SET status='dnc' WHERE id=?", (cid,)),
         "restore": ("UPDATE contacts SET status='active', snooze_until=NULL WHERE id=?", (cid,))}.get(act)
    if not q:
        return False
    with LOCK:
        db = forgedb.connect(DB_PATH)
        db.execute(*q)
        forgedb.log(db, cid, act)
        db.commit()
    return True


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def local_only(self):
        # refuse anything not addressed to this Mac (DNS rebinding) and cross-site posts
        host = (self.headers.get("Host") or "").split(":")[0]
        origin = self.headers.get("Origin")
        ok = host in ("127.0.0.1", "localhost") and (not origin or re.match(r"https?://(127\.0\.0\.1|localhost)(:\d+)?$", origin))
        if not ok:
            self.send(403, {"error": "local only"})
        return ok

    def do_GET(self):
        if not self.local_only():
            return
        u = urlparse(self.path)
        if u.path == "/":
            return self.send(200, open(HTML, "rb").read(), "text/html; charset=utf-8")
        if u.path == "/api/contacts":
            p = {k: v[0] for k, v in parse_qs(u.query).items()}
            return self.send(200, listing(p.get("view", "due"), p.get("rel"), p.get("opp"), p.get("q")))
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if not self.local_only():
            return
        m = re.match(r"^/api/contacts/(\d+)(/action)?$", urlparse(self.path).path)
        if not m:
            return self.send(404, {"error": "not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except ValueError:
            return self.send(400, {"error": "bad json"})
        cid = int(m.group(1))
        ok = action(cid, body.get("action")) if m.group(2) else update(cid, body)
        self.send(200 if ok else 400, {"ok": ok})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(CFG.get("dashboard_port") or 8765))
    ap.add_argument("--open", action="store_true")
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    url = "http://127.0.0.1:%d/" % a.port
    print("Deal Forge dashboard: %s  (Ctrl+C to stop)" % url, flush=True)
    if a.open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
