#!/usr/bin/env python3
# Windowed Parakeet: ~25 s windows cut at silences (SKILL.md: raw files over ~3 min drop sentences otherwise).
import json, os, re, subprocess, sys
W, wav, out = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ytconfig import HF
dur = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",wav],capture_output=True,text=True).stdout)
log = subprocess.run(["ffmpeg","-v","info","-i",wav,"-af","silencedetect=n=-35dB:d=0.25","-f","null","-"],capture_output=True,text=True).stderr
ss=[float(x) for x in re.findall(r"silence_start: ([\d.]+)",log)]; se=[float(x) for x in re.findall(r"silence_end: ([\d.]+)",log)]
mids=[(a+b)/2 for a,b in zip(ss,se)]
cuts=[0.0]; t=0.0
while t+25<dur:
    cand=[m for m in mids if t+18<=m<=t+32]
    nxt=min(cand,key=lambda m:abs(m-(t+25))) if cand else t+25
    cuts.append(nxt); t=nxt
cuts.append(dur)
tmp=os.path.join(W,"win"); os.makedirs(tmp,exist_ok=True)
words=[]; n=0
for i,(a,b) in enumerate(zip(cuts,cuts[1:])):
    f=os.path.join(tmp,"w%03d.wav"%i); d=os.path.join(tmp,"w%03d"%i)
    subprocess.run(["ffmpeg","-y","-v","error","-ss","%.3f"%a,"-t","%.3f"%(b-a),"-i",wav,f],check=True)
    r=subprocess.run([HF,"transcribe",f,"-d",d,"--engine","parakeet","--json"],capture_output=True,text=True)
    p=os.path.join(d,"transcript.json")
    if not os.path.exists(p): print("FAIL window",i,r.stderr[-300:]); continue
    for w in json.load(open(p)):
        words.append({"id":"w%d"%n,"text":w["text"],"start":round(w["start"]+a,3),"end":round(w["end"]+a,3)}); n+=1
    print("window %d/%d %.1f-%.1f"%(i+1,len(cuts)-1,a,b),flush=True)
json.dump(words,open(out,"w"),indent=1)
print("words",len(words))
