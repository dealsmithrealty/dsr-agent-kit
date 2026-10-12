#!/usr/bin/env python3
"""Build an SFX stem (48 kHz stereo wav) for the assembled master from the section storyboards.
Every graphic entrance gets a sound; item-level pops for pills/list items/diagram steps; impacts on stat landings;
a riser cresting on the cold-open -> intro join. Usage: build-sfx.py <offsets json> <out.wav> <duration> [plan.json]  (plan = [time, sound, beat_id] for pre-render-qa.py)"""
import json, os, subprocess, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ytconfig import ROOT
SFX = os.path.join(ROOT, "node_modules/hyperframes/dist/skills/media-use/audio/assets/sfx")
SR = 48000
offs = json.load(open(sys.argv[1])); out = sys.argv[2]; D = float(sys.argv[3])
cache = {}
def load(name):
    if name not in cache:
        src = os.path.join(EXTRA, name + ".wav") if os.path.exists(os.path.join(EXTRA, name + ".wav")) else os.path.join(SFX, ("click-soft" if name == "tick" else name) + ".mp3")
        trim = [] if name == "cash-register" else ["-af", "silenceremove=start_periods=1:start_threshold=-40dB"]
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src] + trim + [ "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                             capture_output=True).stdout
        x = np.frombuffer(raw, np.float32).reshape(-1, 2).copy(); x /= max(1e-6, np.abs(x).max()); x *= 10 ** (-3 / 20)
        if name == "tick":   # a short, dry tick so a fast run does not smear
            x = x[: int(0.05 * SR)].copy(); x *= np.linspace(1, 0, len(x))[:, None]
        cache[name] = x
    return cache[name]
EXTRA = os.path.join(ROOT, "videos/_shared/sfx/extra")
VOL = {"cash-register": 0.32, "chime": 0.2, "tick": 0.13, "pop": 0.22, "click-soft": 0.22, "whoosh-short": 0.16, "whoosh": 0.2, "impact-bass-1": 0.26, "typing": 0.16,
       "sparkle": 0.12, "riser": 0.22, "impact-bass-2": 0.28}
FULL = {"pipeline", "deck", "bars", "stats_row"}
ev = []; cur = ['-']
def add(t, n): ev.append((t, n, cur[0]))
for sec, o in offs.items():
    sb = json.load(open(f"sections/{sec}/storyboard.json"))
    cur[0] = "tag-" + sec
    if sb.get("tag"): add(o + sb["tag"]["in"] + 0.05, "click-soft")
    for b in sb["beats"]:
        cur[0] = b["id"]; t = b["type"]; i = o + b["in"] + 0.05
        kind = "stats_row" if t == "stats" and b.get("layout") == "row" else t
        if kind in FULL: add(i, "whoosh")
        elif t in ("line", "chip", "pointer"): add(i, "whoosh-short");  # text arrives on motion
        elif t in ("logo",): add(o + b.get("pop", b["in"]), "pop")
        elif t == "chat": add(i, "pop"); add(i + 0.25, "typing")
        if b.get("shimmer"): add(i + 0.4, "sparkle")
        for it in b.get("items", []):
            at = it.get("at") if isinstance(it, dict) else (it[1] if len(it) > 1 else None)
            if at is None: continue
            if t == "stats":
                start, dur = o + at + 0.1, float(it.get("dur", 1.1)); land = start + dur
                if str(it.get("prefix", "")).strip() == "$":      # money: the register's bell (1.35 s in) rings on the landing
                    add(land - 1.35, "cash-register")
                else:                                             # a counter: ticks that slow with the power2.out ease, then a ding
                    n = int(min(28, max(6, it["value"] / 100)))
                    for k in range(1, n): add(start + dur * (1 - (1 - k / n) ** 0.5), "tick")
                    add(land, "chime")
            else: add(o + at, "pop")
        for st in b.get("steps", []): add(o + st["at"], "pop")
        for r in b.get("rows", []): add(o + r["at"], "pop")
        for c in (b.get("cards") or []) if t == "deck" else []: pass
# the build into the intro comes from the music bed, not a riser under the speech (creator note, 2026-10-06)
ev.sort(); last = {}
buf = np.zeros((int((D + 3) * SR), 2), np.float32); kept = 0
plan = []
for t, name, bid in ev:
    if name == last.get("n") and name != "tick" and t - last.get("t", -9) < 0.18: continue   # no machine-gun repeats
    x = load(name) * VOL[name]; s = int(t * SR); e = min(len(buf), s + len(x)); buf[s:e] += x[: e - s]; kept += 1
    last = {"n": name, "t": t}; plan.append([round(t, 3), name, bid])
peak = np.abs(buf).max(); buf = buf / peak * 0.89 if peak > 0.89 else buf
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", out], input=buf.tobytes(), check=True)
from collections import Counter
print("events", kept, dict(Counter(n for _, n, _b in ev)))
if len(sys.argv) > 4: json.dump(plan, open(sys.argv[4], "w"))
