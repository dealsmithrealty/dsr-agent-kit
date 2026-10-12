"""End-to-end tests on synthetic data: a fake chat.db + Contacts, a stub `claude`, a mock GoHighLevel.
Run from scripts/:  python3 -m unittest tests
"""
import json, os, socket, sqlite3, subprocess, sys, tempfile, threading, time, unittest, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPLE = 978307200
NS = 1000000000


def apple_ns(days_ago):
    return int((time.time() - days_ago * 86400 - APPLE) * NS)


def typedstream(text):
    b = text.encode()
    return b"\x04\x0bstreamtyped\x81\xe8\x03\x84\x01@\x84\x84\x84\x12NSAttributedString\x00\x84\x84\x08NSObject\x00\x85\x92\x84\x84\x84\x08NSString\x01\x94\x84\x01+" + bytes([len(b)]) + b


def make_chat_db(path):
    c = sqlite3.connect(path)
    c.executescript("""
    CREATE TABLE handle (ROWID INTEGER PRIMARY KEY, id TEXT, service TEXT);
    CREATE TABLE chat (ROWID INTEGER PRIMARY KEY, chat_identifier TEXT, style INTEGER, display_name TEXT);
    CREATE TABLE chat_handle_join (chat_id INTEGER, handle_id INTEGER);
    CREATE TABLE chat_message_join (chat_id INTEGER, message_id INTEGER);
    CREATE TABLE message (ROWID INTEGER PRIMARY KEY, text TEXT, attributedBody BLOB, handle_id INTEGER, date INTEGER,
                          is_from_me INTEGER, associated_message_type INTEGER DEFAULT 0, item_type INTEGER DEFAULT 0);
    """)
    handles = {1: "+15125550101", 2: "+15125550102", 3: "55512", 4: "pat@example.com", 5: "+15125550105"}
    for k, v in handles.items():
        c.execute("INSERT INTO handle VALUES (?,?,?)", (k, v, "iMessage"))
    chats = {1: ("+15125550101", 45, ""), 2: ("+15125550102", 45, ""), 3: ("55512", 45, ""),
             4: ("pat@example.com", 45, ""), 5: ("chat123", 43, "Closing crew"), 6: ("+15125550105", 45, "")}
    for k, (ident, style, name) in chats.items():
        c.execute("INSERT INTO chat VALUES (?,?,?,?)", (k, ident, style, name))
    c.executemany("INSERT INTO chat_handle_join VALUES (?,?)", [(5, 1), (5, 2)])
    msgs = [
        # Alice (1): past client, quiet 200 days; my sends have handle_id 0; one body only in attributedBody
        (1, "Keys are yours, congrats on the house!", None, 0, 400, 1),
        (1, "Thank you so much Derek!", None, 1, 399, 0),
        (1, None, typedstream("Quick question about the HOA"), 1, 200, 0),
        (1, "Sure, call me anytime", None, 0, 200, 1),
        # Bob (2): one-way, they never wrote back -> dropped
        (2, "Hey Bob, it's Derek", None, 0, 50, 1),
        # short code (3): 2FA -> dropped
        (3, "Your code is 1234", None, 3, 10, 0),
        (3, "STOP", None, 0, 10, 1),
        # Pat by email (4) and phone (6) are the SAME Contacts card -> merged
        (4, "Is the Elm St house still available?", None, 4, 100, 0),
        (4, "It is, want to see it Saturday?", None, 0, 100, 1),
        (6, "Thanks for the tour", None, 5, 90, 0),
        # group chat (5): only adds the group name
        (5, "Closing at 3pm everyone", None, 0, 30, 1),
        # a tapback: not a message
        (1, "Loved “Sure”", None, 1, 199, 0),
    ]
    for i, (chat, text, body, hid, days, me) in enumerate(msgs, 1):
        amt = 2000 if text and text.startswith("Loved") else 0
        c.execute("INSERT INTO message VALUES (?,?,?,?,?,?,?,0)", (i, text, body, hid, apple_ns(days), me, amt))
        c.execute("INSERT INTO chat_message_join VALUES (?,?)", (chat, i))
    c.commit()
    c.close()


def make_ab(path):
    c = sqlite3.connect(path)
    c.executescript("""
    CREATE TABLE ZABCDRECORD (Z_PK INTEGER PRIMARY KEY, ZFIRSTNAME TEXT, ZLASTNAME TEXT, ZORGANIZATION TEXT);
    CREATE TABLE ZABCDPHONENUMBER (Z_PK INTEGER PRIMARY KEY, ZOWNER INTEGER, ZFULLNUMBER TEXT);
    CREATE TABLE ZABCDEMAILADDRESS (Z_PK INTEGER PRIMARY KEY, ZOWNER INTEGER, ZADDRESS TEXT);
    CREATE TABLE ZABCDNOTE (Z_PK INTEGER PRIMARY KEY, ZCONTACT INTEGER, ZTEXT TEXT);
    INSERT INTO ZABCDRECORD VALUES (1, 'Alice', 'Ng', ''), (2, 'Pat', 'Lee', 'Buyer 400k');
    INSERT INTO ZABCDPHONENUMBER VALUES (1, 1, '(512) 555-0101'), (2, 2, '512.555.0105');
    INSERT INTO ZABCDEMAILADDRESS VALUES (1, 2, 'Pat@Example.com');
    INSERT INTO ZABCDNOTE VALUES (1, 1, 'Bought 12 Oak Ln 2025');
    """)
    c.commit()
    c.close()


STUB_CLAUDE = r'''#!/usr/bin/env python3
import json, re, sys
p = sys.stdin.read()
assert "--tools" in sys.argv and "-p" in sys.argv
out = []
for line in p.splitlines():
    if line.startswith('{"id"'):
        c = json.loads(line)
        rel = "past_client" if "Keys" in c["messages_newest_first"] else "lead"
        out.append({"id": c["id"], "relationship": rel, "opportunity": "buyer" if rel == "lead" else "nonsense",
                    "rel_conf": 0.9, "opp_conf": 2, "summary": "s" * 300,
                    "draft": "Hey %s — it's Derek, how's everything?" % c["first_name"]})
print("Here you go:\n" + json.dumps(out))
'''


class Mock(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, *a):
        pass

    def _do(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n)) if n else None
        Mock.calls.append((self.command, self.path, body, self.headers.get("Authorization")))
        out = {"contact": {"id": "ghl-%d" % len(Mock.calls)}} if self.path == "/contacts/upsert" else {"location": {"name": "Test Realty"}}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_DELETE = _do


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class ForgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        make_chat_db(os.path.join(cls.d, "chat.db"))
        make_ab(os.path.join(cls.d, "ab.abcddb"))
        stub = os.path.join(cls.d, "claude")
        open(stub, "w").write(STUB_CLAUDE)
        os.chmod(stub, 0o755)
        cfg = {"agent_name": "Derek Smith", "agent_first_name": "Derek", "quiet_days": 21,
               "ghl": {"enabled": False, "location_id": "LOC1"}}
        json.dump(cfg, open(os.path.join(cls.d, "config.json"), "w"))
        cls.env = dict(os.environ, FORGE_CONFIG=os.path.join(cls.d, "config.json"), FORGE_DB=os.path.join(cls.d, "forge.db"),
                       FORGE_CHAT_DB=os.path.join(cls.d, "chat.db"), FORGE_AB_DB=os.path.join(cls.d, "ab.abcddb"),
                       FORGE_CLAUDE_BIN=stub, FORGE_EXPORT_DIR=cls.d)
        cls.run_ok("scan.py")

    @classmethod
    def run_ok(cls, *args, env=None):
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, args[0])] + list(args[1:]), env=env or cls.env,
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("%s failed: %s %s" % (args, r.stdout, r.stderr))
        return r.stdout

    def db(self):
        c = sqlite3.connect(self.env["FORGE_DB"])
        c.row_factory = sqlite3.Row
        return c

    def test_1_scan_people(self):
        rows = {r["name"]: r for r in self.db().execute("SELECT * FROM contacts")}
        self.assertEqual(set(rows), {"Alice Ng", "Pat Lee"})          # Bob one-way, short code dropped
        a = rows["Alice Ng"]
        self.assertEqual((a["msgs_in"], a["msgs_out"]), (2, 2))      # tapback not counted; my handle_id 0 sends counted
        self.assertIn("Quick question about the HOA", a["excerpt"])  # attributedBody decoded
        self.assertEqual(a["ab_note"], "Bought 12 Oak Ln 2025")
        self.assertIn("Closing crew", json.loads(a["groups"]))
        p = rows["Pat Lee"]
        self.assertEqual(json.loads(p["phones"]), ["+15125550105"])  # email + phone merged into one person
        self.assertEqual(json.loads(p["emails"]), ["pat@example.com"])
        self.assertEqual(p["org"], "Buyer 400k")

    def test_2_classify_with_stub(self):
        out = self.run_ok("classify.py")
        self.assertIn("2 classified", out)
        rows = {r["name"]: r for r in self.db().execute("SELECT * FROM contacts")}
        a, p = rows["Alice Ng"], rows["Pat Lee"]
        self.assertEqual(a["relationship"], "past_client")
        self.assertEqual(a["opportunity"], "none")                   # invalid enum -> none
        self.assertEqual(a["opp_conf"], 1.0)                         # clamped
        self.assertLessEqual(len(a["summary"]), 240)
        self.assertNotIn("—", a["draft"])                       # dashes removed
        self.assertEqual(p["relationship"], "lead")
        self.assertEqual(self.run_ok("classify.py").strip(), "ok    nothing to classify")

    def test_3_dashboard_api(self):
        port = free_port()
        proc = subprocess.Popen([sys.executable, os.path.join(SCRIPTS, "dashboard.py"), "--port", str(port)], env=self.env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            base = "http://127.0.0.1:%d" % port
            for _ in range(50):
                try:
                    urllib.request.urlopen(base + "/api/contacts?view=all")
                    break
                except Exception:
                    time.sleep(0.1)
            data = json.load(urllib.request.urlopen(base + "/api/contacts?view=due"))
            names = [c["name"] for c in data["contacts"]]
            self.assertIn("Pat Lee", names)                         # lead, quiet 90 days, cadence 21 -> due
            self.assertIn("Alice Ng", names)                        # past client, quiet 200 days, cadence 90 -> due
            pat = [c for c in data["contacts"] if c["name"] == "Pat Lee"][0]
            self.assertTrue(pat["sms"].startswith("sms:+15125550105&body="))
            req = urllib.request.Request(base + "/api/contacts/%d" % pat["id"], method="POST",
                                         data=json.dumps({"draft": "Hi Pat!", "relationship": "friend"}).encode())
            self.assertTrue(json.load(urllib.request.urlopen(req))["ok"])
            req = urllib.request.Request(base + "/api/contacts/%d/action" % pat["id"], method="POST",
                                         data=json.dumps({"action": "sent"}).encode())
            urllib.request.urlopen(req)
            data = json.load(urllib.request.urlopen(base + "/api/contacts?view=due"))
            self.assertNotIn("Pat Lee", [c["name"] for c in data["contacts"]])
            r = self.db().execute("SELECT * FROM contacts WHERE id=?", (pat["id"],)).fetchone()
            self.assertEqual((r["draft"], r["relationship"], r["user_edited"]), ("Hi Pat!", "friend", 1))
            bad = urllib.request.Request(base + "/api/contacts?view=due", headers={"Host": "evil.example"})
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(bad)
            self.assertEqual(e.exception.code, 403)
            evil = urllib.request.Request(base + "/api/contacts/1/action", method="POST", data=b'{"action":"dnc"}',
                                          headers={"Origin": "https://evil.example"})
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(evil)
        finally:
            proc.terminate()
            proc.wait()

    def test_4_export_csv(self):
        self.run_ok("export_csv.py")
        rows = open(os.path.join(self.d, "deal-forge-contacts.csv")).read().splitlines()
        self.assertTrue(rows[0].startswith("First Name,Last Name,Phone,Email"))
        self.assertEqual(len(rows), 3)

    def test_5_ghl_sync_mock(self):
        port = free_port()
        srv = ThreadingHTTPServer(("127.0.0.1", port), Mock)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            cfg = json.load(open(self.env["FORGE_CONFIG"]))
            cfg["ghl"] = {"enabled": True, "location_id": "LOC1", "keychain_service": "deal-forge-test-%d" % os.getpid(),
                          "token_key": "tok"}
            cpath = os.path.join(self.d, "config-ghl.json")
            json.dump(cfg, open(cpath, "w"))
            env = dict(self.env, FORGE_CONFIG=cpath, FORGE_GHL_BASE="http://127.0.0.1:%d" % port)
            svc = cfg["ghl"]["keychain_service"]
            subprocess.run(["security", "add-generic-password", "-U", "-s", svc, "-a", "tok", "-w", "test-token"], check=True)
            try:
                self.assertIn("Test Realty", self.run_ok("ghl.py", "--check", env=env))
                self.assertIn("dry run", self.run_ok("ghl.py", env=env))
                self.assertFalse([c for c in Mock.calls if c[0] == "POST"])
                self.run_ok("ghl.py", "--apply", env=env)
                ups = [c for c in Mock.calls if c[1] == "/contacts/upsert"]
                self.assertEqual(len(ups), 2)
                self.assertTrue(all(c[3] == "Bearer test-token" for c in Mock.calls))
                self.assertTrue(all(u[2]["locationId"] == "LOC1" for u in ups))
                tags = [c[2]["tags"] for c in Mock.calls if c[1].endswith("/tags") and c[0] == "POST"]
                self.assertIn(["deal-forge", "df_relationship_past_client"], tags)
                n = len(Mock.calls)
                self.assertIn("plan  0 to create", self.run_ok("ghl.py", env=env))   # idempotent
                self.run_ok("ghl.py", "--apply", env=env)
                self.assertEqual(len(Mock.calls), n)
            finally:
                subprocess.run(["security", "delete-generic-password", "-s", svc, "-a", "tok"], capture_output=True)
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
