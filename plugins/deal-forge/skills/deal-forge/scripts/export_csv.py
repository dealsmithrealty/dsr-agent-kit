#!/usr/bin/env python3
"""export_csv.py: every classified contact as a spreadsheet (opens in Numbers, Excel or Google Sheets, and imports
straight into GoHighLevel later: Contacts > Import). For agents without GHL, and as a backup for everyone.

  python3 export_csv.py [--out FILE]      default ~/Documents/Deal Forge/deal-forge-contacts.csv
"""
import argparse, csv, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from forgeconfig import CFG, DB_PATH, EXPORT_DIR
import forgedb

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(EXPORT_DIR, "deal-forge-contacts.csv"))
a = ap.parse_args()
db = forgedb.connect(DB_PATH)
rows = db.execute("SELECT * FROM contacts WHERE classified_at IS NOT NULL AND status != 'dnc'").fetchall()
rows = sorted(rows, key=forgedb.rank)
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
now = time.time()
with open(a.out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["First Name", "Last Name", "Phone", "Email", "Relationship", "Opportunity", "Tags", "Summary",
                "Last Texted", "Next Reconnect", "Draft Text", "Status"])
    for r in rows:
        first = r["first_name"] or (r["name"] or "").split(" ")[0]
        last = (r["name"] or "")[len(first):].strip() if (r["name"] or "").startswith(first) else ""
        due = forgedb.due_at(r, CFG["cadence_days"])
        tags = ["deal-forge", "df_relationship_" + (r["relationship"] or "acquaintance")]
        if r["opportunity"] and r["opportunity"] != "none":
            tags.append("df_opportunity_" + r["opportunity"])
        w.writerow([first, last, ", ".join(json.loads(r["phones"] or "[]")), ", ".join(json.loads(r["emails"] or "[]")),
                    r["relationship"], r["opportunity"], ", ".join(tags), r["summary"] or "",
                    time.strftime("%Y-%m-%d", time.localtime(max(r["last_at"] or 0, r["sent_at"] or 0))),
                    "never" if due is None else ("now" if due <= now else time.strftime("%Y-%m-%d", time.localtime(due))),
                    r["draft"] or "", r["status"]])
print("ok    %d contacts -> %s" % (len(rows), a.out))
