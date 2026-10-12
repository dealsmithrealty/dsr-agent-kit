#!/usr/bin/env python3
"""Resolve plan.json (phrase-anchored beats) against the flat-cut transcript into one storyboard per section.
Usage: python3 build-storyboards.py [--transcript transcript.json] [--cut-map cut-map.json] [--slice]
--slice also cuts each section's footage out of public/input-video.mp4 into sections/<id>/public/input-video.mp4."""
import argparse, difflib, json, os, re, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("--transcript", default="transcript.json"); ap.add_argument("--cut-map", default="cut-map.json")
ap.add_argument("--plan", default="plan.json"); ap.add_argument("--slice", action="store_true")
a = ap.parse_args()

W = json.load(open(a.transcript)); W = W["words"] if isinstance(W, dict) else W
CM = json.load(open(a.cut_map)); JOINS = [float(x) for x in CM["cuts"]]; FLAT = float(CM["flat_duration"])
P = json.load(open(a.plan))
NUM = {"three thousand": "3000"}

def norm(s):
    s = s.lower().replace(",", "").replace("'", "").replace("\u2019", "")
    for k, v in NUM.items(): s = s.replace(k, v)
    return re.sub(r"[^a-z0-9$ ]", " ", s).split()
TOK = [(norm(w["text"]) or [""])[0] for w in W]
problems = []

def find(phrase, after=0.0, before=1e9):
    q = norm(phrase); n = len(q); best = (0, None)
    for i in range(len(TOK) - n + 1):
        if W[i]["start"] < after - 0.01 or W[i]["start"] > before: continue
        if TOK[i:i + n] == q: return W[i]["start"]
        r = difflib.SequenceMatcher(None, TOK[i:i + n], q).ratio()
        if r > best[0]: best = (r, i)
    if best[1] is not None and best[0] >= 0.75: return W[best[1]]["start"]
    problems.append("anchor not found: %r (after %.1f, best %.2f)" % (phrase, after, best[0])); return None

def end_of(phrase, after=0.0):
    t = find(phrase, after)
    if t is None: return None
    n = len(norm(phrase)); i = next(k for k, w in enumerate(W) if w["start"] == t)
    return W[min(i + n - 1, len(W) - 1)]["end"]

def sentence_start(t):
    """Back up from an anchor word to the first word of its sentence, so a section never strands "So" in the last one."""
    i = next((k for k, w in enumerate(W) if abs(w["start"] - t) < 0.01), None)
    if i is None: return t
    while i > 0 and not W[i - 1]["text"].rstrip().endswith((".", "?", "!")) and t - W[i - 1]["start"] < 6.0: i -= 1
    return W[i]["start"]

def snap_join(t, back=1.5):
    t = sentence_start(t)
    c = [j for j in JOINS if t - back <= j <= t + 0.015]   # never past the sentence onset
    return max(c) if c else max(0.0, t - 0.25)

# ---- section boundaries ----
secs = P["sections"]; bounds = {}
body = [s for s in secs if s["id"] != "cold"]
starts = []
for s in body:
    t = 0.0 if s["start"] == body[0]["start"] else find(s["start"])
    starts.append(0.0 if t is None or s is body[0] else snap_join(t))
for k, s in enumerate(body):
    bounds[s["id"]] = (starts[k], starts[k + 1] if k + 1 < len(body) else FLAT)
cold = next((s for s in secs if s["id"] == "cold"), None)
if cold:
    t0 = find(cold["start"]); t1 = end_of(cold["end_after"], t0 or 0)
    if t0 is not None and t1 is not None:
        # end in the gap after the last word, never on the next sentence's first syllable ("...tokens. Could I")
        nxt = [w["start"] for w in W if w["start"] > t1 - 0.01]
        bounds["cold"] = (snap_join(t0), min(FLAT, t1 + 0.3, (nxt[0] - 0.08) if nxt else t1 + 0.3))

def lt(t, S): return None if t is None else round(t - S, 3)

out_dirs = []
for s in secs:
    if s["id"] not in bounds: problems.append("section %s unresolved" % s["id"]); continue
    S, E = bounds[s["id"]]; D = round(E - S, 3)
    F = lambda ph, after=S: lt(find(ph, after, E), S)
    beats = []
    for b in s["beats"]:
        b = json.loads(json.dumps(b)); t = F(b.pop("anchor"))
        if t is None: continue
        b["in"] = max(0.05, round(t - 0.2, 3))
        if "until" in b: u = F(b.pop("until"), S + t); b["out"] = round((u - 0.45) if u else b["in"] + 6, 3)
        elif b.pop("until_end", False): b["out"] = round(D - 0.05, 3)
        else: b["out"] = round(b["in"] + b.pop("dur", 5.0), 3)
        b["out"] = min(b["out"], round(D - 0.05, 3)); b["anchor"] = "-"
        def at(ph): x = F(ph, S + b["in"] - 1.0); return x if x is not None else b["in"] + 0.3
        if b["type"] in ("list", "bullets", "popout"): b["items"] = [[txt, round(at(ph), 3), "-"] for txt, ph in b["items"]]
        if b["type"] == "pills":
            for it in b["items"]: it["at"] = round(at(it["at"]), 3); it["anchor"] = "-"
        if b["type"] == "pipeline":
            for st in b["steps"]: st["at"] = round(at(st["at"]), 3)
        if b["type"] == "stats":
            for it in b["items"]: it["at"] = round(at(it["at"]), 3)
        if b["type"] == "bars":
            for r in b["rows"]: r["at"] = round(at(r["at"]), 3)
        if b["type"] == "deck":
            for k in ("focus_at", "recap_at"):
                if k in b: b[k] = round(at(b[k]), 3)
        if b["type"] == "chat": b["messages"] = [[who, txt, round(at(ph), 3), "-"] for who, txt, ph in b["messages"]]
        if b["type"] == "logo": b["pop"] = round(b["in"] + 0.07, 3)
        beats.append(b)
    beats.sort(key=lambda b: b["in"])
    FULL = {"pipeline", "deck", "bars", "world", "flow", "hub", "masktitle"}
    full = [(b["in"], b["out"]) for b in beats if b["type"] in FULL or (b["type"] == "stats" and b.get("layout") == "row")]
    kept_b, last_bottom = [], None
    for b in beats:
        isfull = (b["in"], b["out"]) in full
        if not isfull and any(fi - 0.3 < b["in"] < fo + 0.2 or fi - 0.3 < b["out"] and b["in"] < fi for fi, fo in full):
            problems.append("%s: %s dropped (inside a full-frame beat)" % (s["id"], b["id"])); continue
        if b["type"] in ("line", "chip", "pointer"):
            if last_bottom and b["in"] < last_bottom["out"] + 0.2:
                if b["in"] - 0.25 - last_bottom["in"] >= 2.0: last_bottom["out"] = round(b["in"] - 0.25, 3)
                else: problems.append("%s: %s dropped (lower slot busy)" % (s["id"], b["id"])); continue
            last_bottom = b
        kept_b.append(b)
    beats = kept_b
    joins = [round(j - S, 3) for j in JOINS if S + 0.05 < j < E - 0.05]
    cam = []
    for op, ph, sc in s.get("camera", []):
        t = F(ph)
        if t is None: continue
        nxt = [j for j in joins if j > t]
        if nxt and nxt[0] - t < 1.2: problems.append("%s: punch on %r skipped (cut %.2fs later)" % (s["id"], ph, nxt[0] - t)); continue
        cam.append(["punch", round(t, 3), sc]); cam.append(["set", round((nxt[0] - 0.003) if nxt else D - 0.1, 3), 1.0])
    # quiet-stretch filler: a gentle punch where nothing has moved for 14 s (long-form pacing), never near a cut
    marks = sorted([b["in"] for b in beats] + [c[1] for c in cam] + [0.0, D])
    starts_ = [round(w["start"] - S, 3) for k, w in enumerate(W) if S <= w["start"] < E and (k == 0 or W[k-1]["text"].endswith((".", "?", "!", ",")))]
    for x, y in zip(marks, marks[1:]):
        t = x + 7.0
        while t < y - 5.0:
            c = [w for w in starts_ if t <= w <= t + 6.0]
            ok = None
            for w in c:
                nxt = [j for j in joins if j > w]; prv = [j for j in joins if j <= w]
                if (not nxt or nxt[0] - w >= 1.5) and (not prv or w - prv[-1] >= 0.25): ok = (w, nxt[0] if nxt else D - 0.1); break
            if ok:
                cam.append(["punch", ok[0], 1.06]); cam.append(["set", round(ok[1] - 0.003, 3), 1.0]); t = ok[1] + 7.0
            else: t += 6.0
    cam.sort(key=lambda c: c[1])
    sb = {"id": "zero-to-100-" + s["id"], "duration": D, "video": "input-video.mp4", "origin": "52% 0%", "glass_bg": "rgba(17,17,17,0.55)", "beats": beats, "camera": cam,
          "raw_html": "", "raw_js": "", "flat_range": [round(S, 3), round(E, 3)]}
    if s.get("n"): sb["tag"] = {"n": s["n"], "of": 7, "label": s["label"], "in": 0.25, "out": 5.0, "pos": "tr", "anchor": "-"}
    d = os.path.join("sections", s["id"]); os.makedirs(os.path.join(d, "public"), exist_ok=True)
    json.dump(sb, open(os.path.join(d, "storyboard.json"), "w"), indent=1)
    out_dirs.append((s["id"], S, E, len(beats)))
    if a.slice:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % S, "-to", "%.3f" % E, "-i", "public/input-video.mp4",
                        "-map", "0:v:0", "-map", "0:a:0", "-r", "30", "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-g", "30",
                        "-keyint_min", "30", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-colorspace", "bt709", "-color_range", "tv", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "256k",
                        "-ar", "48000", os.path.join(d, "public", "input-video.mp4")], check=True)
        # section transcript in section time, for beat-check
        json.dump([{**w, "start": round(w["start"] - S, 3), "end": round(w["end"] - S, 3)} for w in W if S <= w["start"] < E],
                  open(os.path.join(d, "transcript.json"), "w"), indent=1)
for sid, S, E, n in out_dirs: print("%-5s %8.2f-%8.2f  %6.1fs  %d beats" % (sid, S, E, E - S, n))
print("\n".join(problems) if problems else "all anchors resolved")
