#!/usr/bin/env python3
"""pre-render-qa.py: the gate that runs AFTER the flat cut and storyboards exist and BEFORE any render.
A render on a slow machine costs ~10x real time, so every defect this catches saves hours. Exit 1 = do not render.

Checks, on the flat cut (the words the viewer will actually hear):
  1. STUMBLES   word repeats ("the the"), restarts ("all of my previous, all of the leads"), fillers (um/uh),
                leftover take markers ("cut that", "let me redo"), abandoned sentences (no end punctuation, then a pause).
  2. BOUNDARIES every section / cold-open / segment must start on the first word of a sentence and end after the
                last word of one, with no word onset in the final 0.35 s (that is a clipped next sentence: "...tokens. Could I").
  3. JOINS      every jump cut in the flat cut (from cut-map.json next to the transcript): the flat audio must be quiet
                just outside apply-cut's 20 ms fades on BOTH sides of the join (a "So" clipped at its first syllable, a
                word chopped mid-way), and no kept segment may be shorter than 0.5 s (a leftover sliver of another take,
                "a random half second clip of nothing"). Connected-speech joins the editor reviewed pass with --accept.
  4. SOUND PLAN every planned sound, the graphic it belongs to, and the words being spoken there, so a human can
                read it like a cue sheet; flags counters without ticks, money without a register, sounds with no graphic.

Usage: python3 pre-render-qa.py --project videos/<p> [--sections cold,s1,...] [--sfx-plan videos/<p>/sound/plan.json]
       Reads <p>/transcript.json (flat), <p>/sections/<id>/storyboard.json (each carries flat_range), writes <p>/QA.md.
"""
import argparse, json, os, re, sys

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--transcript", default=None)
ap.add_argument("--sections", default=None, help="comma list of section ids in play order (default: every sections/* dir)")
ap.add_argument("--sfx-plan", default=None, help="JSON list of [time, sound, beat_id] from build-sfx.py --plan")
ap.add_argument("--audio", default=None, help="flat audio for the JOINS check (default: audio.wav next to the transcript)")
ap.add_argument("--cut-map", default=None, help="flat cut-map.json (default: cut-map.json next to the transcript); 'none' skips JOINS")
ap.add_argument("--join-threshold", type=float, default=300, help="RMS (int16) above which a join edge counts as in sound")
ap.add_argument("--accept", action="append", default=[], help="flat time (s) of a flag you reviewed and accept, e.g. 512.3")
a = ap.parse_args()
P = a.project
W = json.load(open(a.transcript or os.path.join(P, "transcript.json"))); W = W["words"] if isinstance(W, dict) else W
norm = lambda s: re.sub(r"[^a-z0-9']", "", s.lower())
T = [norm(w["text"]) for w in W]
END = lambda w: w["text"].rstrip().endswith((".", "?", "!"))
accepted = [float(x) for x in a.accept]
def ok(t): return any(abs(t - x) < 1.0 for x in accepted)
def ctx(i, before=6, after=8): return " ".join(w["text"] for w in W[max(0, i - before): i + after])
def mmss(t): return "%d:%02d.%d" % (t // 60, t % 60, int((t * 10) % 10))
flags = []

# ---- 1. stumbles -----------------------------------------------------------------------------------------------
LEGIT_DOUBLE = {"that", "had", "is", "do", "you"}
FILLER = {"um", "uh", "uhh", "umm", "erm", "hmm"}
MARKERS = ["cut that", "scratch that", "let me redo", "let me try that again", "start over", "take two", "one more time"]
for i in range(1, len(W)):
    if T[i] and T[i] == T[i - 1] and T[i] not in LEGIT_DOUBLE and not END(W[i - 1]) and W[i]["start"] - W[i - 1]["end"] < 1.2:
        flags.append(("STUMBLE", W[i - 1]["start"], "word repeat \"%s %s\"" % (W[i - 1]["text"], W[i]["text"]), ctx(i)))
    if T[i] in FILLER:
        flags.append(("STUMBLE", W[i]["start"], "filler \"%s\"" % W[i]["text"], ctx(i)))
for i in range(len(W)):  # restarts: a 2-4 word phrase said again within 4 s, the first copy cut short (comma or fragment)
    for n in (4, 3, 2):
        if i + n > len(W) or not all(T[i:i + n]): continue
        for j in range(i + 1, min(len(W) - n + 1, i + 14)):
            if W[j]["start"] - W[i]["start"] > 4.0: break
            if T[j:j + n] == T[i:i + n]:
                between = W[i + n:j]          # words said between the two copies
                # a restart abandons the first copy within a word or two ("all of my previous, all of the leads");
                # parallel lists ("keeps track of my deals, keeps track of my leads") carry a full phrase between
                cut_short = len(between) <= 2 and (not between or between[-1]["text"].endswith((",", "-")) or len(between) == 0)
                if cut_short and not any(END(w) for w in W[i:j]):
                    flags.append(("STUMBLE", W[i]["start"], "restart: \"%s\" said again %.1f s later" % (" ".join(w["text"] for w in W[i:i + n]), W[j]["start"] - W[i]["start"]), ctx(j, 8, 6)))
                break
        else: continue
        break
low = " ".join(T)
for m in MARKERS:
    for hit in re.finditer(re.escape(m.replace("'", "")), low):
        k = low[: hit.start()].count(" ")
        flags.append(("STUMBLE", W[k]["start"], "take marker left in: \"%s\"" % m, ctx(k)))
for i in range(len(W) - 1):  # abandoned sentence: no end punctuation, then a long pause, then a capitalised restart
    if not END(W[i]) and W[i + 1]["start"] - W[i]["end"] > 0.9 and W[i + 1]["text"][:1].isupper() and not W[i]["text"].endswith(","):
        flags.append(("STUMBLE", W[i]["start"], "sentence abandoned before \"%s\"" % W[i + 1]["text"], ctx(i)))

# ---- 2. boundaries ---------------------------------------------------------------------------------------------
secdir = os.path.join(P, "sections")
ids = a.sections.split(",") if a.sections else sorted(d for d in os.listdir(secdir) if os.path.isfile(os.path.join(secdir, d, "storyboard.json")))
ranges = []
for sid in ids:
    sb = json.load(open(os.path.join(secdir, sid, "storyboard.json")))
    if "flat_range" not in sb: flags.append(("BOUNDARY", 0, "%s has no flat_range" % sid, "")); continue
    S, E = sb["flat_range"]; ranges.append((sid, S, E, sb))
    inside = [k for k, w in enumerate(W) if S - 0.05 <= w["start"] < E - 0.03]   # ASR onsets run ~30 ms early
    if not inside: flags.append(("BOUNDARY", S, "%s holds no words" % sid, "")); continue
    first, last = inside[0], inside[-1]
    if first > 0 and not END(W[first - 1]) and S > 0.5:
        flags.append(("BOUNDARY", S, "%s STARTS mid-sentence at \"%s\"" % (sid, W[first]["text"]), ctx(first, 8, 4)))
    if not END(W[last]):
        flags.append(("BOUNDARY", E, "%s ENDS mid-sentence after \"%s\"" % (sid, W[last]["text"]), ctx(last, 8, 4)))
    late = [k for k in inside if W[k]["start"] > E - 0.35 and k != first]
    if late and late[0] > 0 and END(W[late[0] - 1]):
        flags.append(("BOUNDARY", E, "%s ends on the first word(s) of the NEXT sentence: \"%s\"" % (sid, " ".join(W[k]["text"] for k in late)), ctx(late[0], 6, 3)))

# ---- 3. joins --------------------------------------------------------------------------------------------------
tdir = os.path.dirname(os.path.abspath(a.transcript or os.path.join(P, "transcript.json")))
cmp_ = a.cut_map or os.path.join(tdir, "cut-map.json"); aud = a.audio or os.path.join(tdir, "audio.wav")
if cmp_ != "none" and os.path.exists(cmp_) and os.path.exists(aud):
    import wave
    import numpy as np
    wv = wave.open(aud); sr = wv.getframerate(); xa = np.frombuffer(wv.readframes(wv.getnframes()), dtype=np.int16).astype(float)
    if wv.getnchannels() > 1: xa = xa.reshape(-1, wv.getnchannels()).mean(axis=1)
    def jrms(s0, e0): i0, i1 = max(0, int(s0 * sr)), max(int(e0 * sr), int(s0 * sr) + 1); return float(np.sqrt(np.mean(xa[i0:i1] ** 2))) if i1 <= len(xa) else 0.0
    segs = json.load(open(cmp_))["segments"]
    inplay = lambda t: any(S - 0.01 <= t <= E + 0.01 for _, S, E, _ in ranges) if ranges else True
    nj = 0
    for k, g in enumerate(segs):
        if not inplay(g["flat_start"]): continue
        if g["flat_end"] - g["flat_start"] < 0.5:
            flags.append(("JOIN", g["flat_start"], "%.2f s segment (src %.2f-%.2f): sliver of another take?" % (g["flat_end"] - g["flat_start"], g["src_start"], g["src_end"]), ctx(min(range(len(W)), key=lambda i: abs(W[i]["start"] - g["flat_start"])))))
        if k + 1 < len(segs) and abs(segs[k + 1]["src_start"] - g["src_end"]) > 0.01:      # a real jump cut
            t = g["flat_end"]; nj += 1
            pre_, post_ = jrms(t - 0.05, t - 0.02), jrms(t + 0.02, t + 0.05)          # outside the 20 ms fades
            if max(pre_, post_) > a.join_threshold:
                side = "both sides" if min(pre_, post_) > a.join_threshold else ("before" if pre_ > post_ else "after")
                near = min(range(len(W)), key=lambda i: abs(W[i]["start"] - t)) if W else 0
                flags.append(("JOIN", t, "join in sound (%s; rms %d / %d): clipped word or sliver? listen at it" % (side, pre_, post_), ctx(near, 6, 6)))
    print("JOINS: %d jump cuts checked (%s)" % (nj, os.path.relpath(cmp_)))

# ---- 4. sound plan ---------------------------------------------------------------------------------------------
cue = []
plan = json.load(open(a.sfx_plan)) if a.sfx_plan and os.path.exists(a.sfx_plan) else []
beats = {}
for sid, S, E, sb in ranges:
    for b in sb["beats"]: beats[b["id"]] = (S, b)
for sid, S, E, sb in ranges:
    if sb.get("tag"): beats["tag-" + sid] = (S, {"type": "tag", "id": "tag-" + sid, "text": sb["tag"].get("label", "")})
for t, snd, bid in plan:
    said = " ".join(w["text"] for w in W if t - 0.8 <= w["start"] <= t + 0.6)
    S_b = beats.get(bid)
    what = "-"
    if S_b:
        b = S_b[1]; what = b["type"] + ": " + str(b.get("text") or b.get("title") or b.get("head") or b.get("eyebrow") or "")[:40]
    else:
        flags.append(("SOUND", t, "\"%s\" has no graphic behind it" % snd, said))
    cue.append((t, snd, what, said))
for sid, S, E, sb in ranges:
    if sb.get("tag"): beats["tag-" + sid] = (S, {"type": "tag", "text": sb["tag"].get("label", "")})
for bid, (S, b) in beats.items():
    if b["type"] == "stats" and plan:
        for it in b.get("items", []):
            land = S + it["at"] + 0.1 + float(it.get("dur", 1.1))
            near = [s for t, s, x in plan if x == bid and abs(t - land) < 1.6]
            want = "cash-register" if str(it.get("prefix", "")).strip() == "$" else "chime"
            if want not in near: flags.append(("SOUND", land, "%s %s lands with no %s" % (bid, it.get("label", ""), want), ""))

# ---- report ----------------------------------------------------------------------------------------------------
flags = [f for f in flags if not ok(f[1])]
flags.sort(key=lambda f: ({"BOUNDARY": 0, "JOIN": 1}.get(f[0], 2), f[1]))
L = ["# Pre-render QA: %s" % os.path.basename(os.path.abspath(P)), "",
     "%d issue(s). Exit 1 until every one is fixed in the cut list or reviewed and passed with --accept <time>." % len(flags), "",
     "This gate is a net, not the review. Also READ the whole flat transcript (`transcript.json`) sentence by sentence as an",
     "editor before rendering: rules miss stumbles that a reader hears instantly.", ""]
for kind in ("BOUNDARY", "JOIN", "STUMBLE", "SOUND"):
    fs = [f for f in flags if f[0] == kind]
    if not fs: continue
    L += ["## %s (%d)" % (kind, len(fs)), "", "| Flat time | Problem | Context |", "|---|---|---|"]
    L += ["| %s | %s | %s |" % (mmss(t), why, c.replace("|", "/")) for _, t, why, c in fs] + [""]
if cue:   # one row per run: a counter's 27 ticks read as "tick x27"
    rows = []
    for t, s_, w_, said in sorted(cue):
        if rows and rows[-1][1] == s_ and rows[-1][2] == w_ and t - rows[-1][4] < 0.25: rows[-1][3] += 1; rows[-1][4] = t; continue
        rows.append([t, s_, w_, 1, t, said])
    L += ["## Cue sheet (%d sounds)" % len(cue), "", "| Time | Sound | Graphic | Being said |", "|---|---|---|---|"]
    L += ["| %s | %s%s | %s | %s |" % (mmss(r[0]), r[1], " x%d" % r[3] if r[3] > 1 else "", r[2], r[5]) for r in rows] + [""]
open(os.path.join(P, "QA.md"), "w").write("\n".join(L) + "\n")
by = {}
for f in flags: by[f[0]] = by.get(f[0], 0) + 1
print("QA: %s -> %s" % (", ".join("%s %d" % kv for kv in by.items()) or "clean", os.path.join(P, "QA.md")))
sys.exit(1 if flags else 0)
