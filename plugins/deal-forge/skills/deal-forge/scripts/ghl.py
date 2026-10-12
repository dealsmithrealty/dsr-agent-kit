#!/usr/bin/env python3
"""ghl.py: push classified contacts into the user's OWN GoHighLevel sub-account.

  python3 ghl.py --check          the token and location work (prints the account name)
  python3 ghl.py                  dry run: what would be created or tagged
  python3 ghl.py --apply          do it

Each contact is upserted (matched by phone/email, so nothing is duplicated), tagged `deal-forge`,
`df_relationship_<x>` and `df_opportunity_<y>` (old df_ tags are swapped when a tag changes), and gets one note with
the summary. Skipped: do-not-contact, set-aside, and ghl.skip_relationships (family by default).
Token: the user's Private Integration token, read from THEIR Keychain (service/account in the config).
"""
import argparse, json, os, sys, time, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from forgeconfig import CFG, DB_PATH, secret
import forgedb

BASE = os.environ.get("FORGE_GHL_BASE") or "https://services.leadconnectorhq.com"


class GHL:
    def __init__(self, token, location):
        self.token, self.location = token, location

    def call(self, method, path, body=None, tries=4):
        data = json.dumps(body).encode() if body is not None else None
        for n in range(tries):
            req = urllib.request.Request(BASE + path, data=data, method=method, headers={
                "Authorization": "Bearer " + self.token, "Version": "2021-07-28", "Accept": "application/json",
                "Content-Type": "application/json", "User-Agent": "deal-forge-agent/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    raw = r.read()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                if e.code == 429 or e.code >= 500:
                    time.sleep(2 ** n)
                    continue
                raise RuntimeError("GHL %s %s -> %d %s" % (method, path, e.code, e.read()[:300].decode("utf-8", "replace")))
        raise RuntimeError("GHL %s %s kept failing (rate limit or server error)" % (method, path))


def client():
    g = CFG["ghl"]
    if not g.get("enabled"):
        sys.exit("GHL is off in the config (ghl.enabled). Run /forge-setup to connect it, or use export_csv.py.")
    tok = secret(g["token_key"])
    if not tok:
        sys.exit("No GHL token in your Keychain. Run: python3 store_secret.py %s" % g["token_key"])
    return GHL(tok, g["location_id"])


def tags_for(r):
    t = ["deal-forge", "df_relationship_" + (r["relationship"] or "acquaintance")]
    if r["opportunity"] and r["opportunity"] != "none":
        t.append("df_opportunity_" + r["opportunity"])
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    api = client()
    if a.check:
        loc = api.call("GET", "/locations/" + api.location).get("location", {})
        print("ok    GHL connected: %s (%s)" % (loc.get("name") or "?", api.location))
        return 0
    db = forgedb.connect(DB_PATH)
    skip = set(CFG["ghl"].get("skip_relationships") or [])
    rows = [r for r in db.execute("""SELECT * FROM contacts WHERE classified_at IS NOT NULL
                                     AND status NOT IN ('dnc', 'skipped')""").fetchall()
            if r["relationship"] not in skip]
    todo = [r for r in rows if not r["ghl_id"] or sorted(tags_for(r)) != sorted(json.loads(r["ghl_tags"] or "[]"))]
    new = sum(1 for r in todo if not r["ghl_id"])
    print("plan  %d to create or match in GHL, %d to retag (of %d eligible)" % (new, len(todo) - new, len(rows)))
    if not a.apply:
        print("dry run: nothing sent. Add --apply to do it.")
        return 0
    ok = failed = 0
    for r in todo:
        try:
            phones, emails = json.loads(r["phones"] or "[]"), json.loads(r["emails"] or "[]")
            first = r["first_name"] or (r["name"] or "").split(" ")[0]
            last = (r["name"] or "")[len(first):].strip() if (r["name"] or "").startswith(first) else ""
            cid = r["ghl_id"]
            if not cid:
                body = {"locationId": api.location, "source": "Deal Forge"}
                if first: body["firstName"] = first
                if last: body["lastName"] = last
                if phones: body["phone"] = phones[0]
                if emails: body["email"] = emails[0]
                cid = api.call("POST", "/contacts/upsert", body)["contact"]["id"]
            want, had = tags_for(r), json.loads(r["ghl_tags"] or "[]")
            stale = [t for t in had if t not in want]
            if stale:
                api.call("DELETE", "/contacts/%s/tags" % cid, {"tags": stale})
            api.call("POST", "/contacts/%s/tags" % cid, {"tags": want})
            if not r["ghl_note_at"] and r["summary"]:
                api.call("POST", "/contacts/%s/notes" % cid, {"body": "Deal Forge: " + r["summary"]})
                db.execute("UPDATE contacts SET ghl_note_at=? WHERE id=?", (time.time(), r["id"]))
            db.execute("UPDATE contacts SET ghl_id=?, ghl_tags=?, ghl_synced_at=? WHERE id=?",
                       (cid, json.dumps(want), time.time(), r["id"]))
            forgedb.log(db, r["id"], "ghl_sync", {"ghl_id": cid, "tags": want})
            db.commit()
            ok += 1
            time.sleep(0.15)
        except Exception as e:
            failed += 1
            print("warn  %s: %s" % (r["name"] or r["key"], e), file=sys.stderr)
            if failed >= 5 and ok == 0:
                print("stop  5 failures in a row: check the token scopes (contacts read + write) and location id")
                return 1
    print("done  %d synced to GHL, %d failed" % (ok, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
