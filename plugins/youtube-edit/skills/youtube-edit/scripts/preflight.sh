#!/bin/bash
# preflight.sh: run before EVERY render and every assembly.
#   0. checks the per-user config (ytconfig.py check): missing = run /video-setup first
#   1. checks the binaries the skill needs (pinned HyperFrames, ffmpeg, ffprobe, auto-editor, python3 + numpy, node)
#   2. clears stale HyperFrames frame caches and leftover work-* folders, but only when no render is running
#   3. stops (exit 1) when free disk is under the floor (default 40 GB; override with YT_MIN_FREE_GB)
# Exit 0 = go. Exit 1 = do not render. Prints one line per check.
# Usage: bash "$SK/scripts/preflight.sh" [project-dir]
set -u
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
HERE="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$HERE")"
ROOT="${YT_ROOT:-$(python3 "$HERE/ytconfig.py" get workdir)}"
HF="${HF:-$ROOT/node_modules/.bin/hyperframes}"
MIN_GB="${YT_MIN_FREE_GB:-$(python3 "$HERE/ytconfig.py" get render.min_free_gb)}"
PROJ="${1:-}"
fail=0

ok()  { echo "ok    $*"; }
bad() { echo "FAIL  $*"; fail=1; }

# 0. config
python3 "$HERE/ytconfig.py" check || fail=1

# 1. binaries
[ -x "$HF" ] && ok "hyperframes $("$HF" --version 2>/dev/null | tail -1) (pinned, $HF)" || bad "hyperframes missing at $HF (bash $HERE/setup-toolchain.sh)"
for b in ffmpeg ffprobe node auto-editor; do
  command -v "$b" >/dev/null 2>&1 && ok "$b" || bad "$b not on PATH"
done
python3 -c "import numpy" 2>/dev/null && ok "python3 + numpy" || bad "numpy missing (python3 -m pip install --user numpy)"
[ -f "$SKILL_DIR/assets/vendor/gsap.min.js" ] && ok "gsap vendored (offline renders)" || echo "warn  no local gsap.min.js: renders will load it from the CDN"

# 2. cleanup, only when nothing is rendering
if pgrep -f "hyperframes.*(render|snapshot|transcribe|capture)" >/dev/null 2>&1 || pgrep -f "assemble.py" >/dev/null 2>&1; then
  echo "skip  cleanup: a render or assembly is running right now"
else
  TMPD="${TMPDIR:-/tmp}"
  for c in "$TMPD"/hyperframes-extract-cache-*; do
    [ -d "$c" ] || continue
    sz=$(du -sh "$c" 2>/dev/null | cut -f1); rm -rf "$c" && ok "cleared frame cache $c ($sz)"
  done
  for base in "$ROOT/videos" "$(python3 "$HERE/ytconfig.py" get staging_dir)"; do
    [ -d "$base" ] || continue
    find "$base" -maxdepth 3 -type d -name 'work-*' -mmin +60 2>/dev/null | while read -r w; do
      sz=$(du -sh "$w" 2>/dev/null | cut -f1); rm -rf "$w" && echo "ok    removed stale $w ($sz)"
    done
  done
fi

# 3. disk floor
free_gb=$(df -g "$ROOT" 2>/dev/null | awk 'NR==2{print $4}')
if [ -z "$free_gb" ]; then
  bad "could not read free disk for $ROOT"
elif [ "$free_gb" -lt "$MIN_GB" ]; then
  bad "only ${free_gb} GB free (floor ${MIN_GB} GB): a 4K render caches every frame; free space first"
else
  ok "${free_gb} GB free (floor ${MIN_GB} GB)"
fi

# rough need for an assembly: about 2 x minutes x 0.34 GB
if [ -n "$PROJ" ] && [ -f "$PROJ/input-video.mp4" -o -f "$PROJ/public/input-video.mp4" ]; then
  f="$PROJ/public/input-video.mp4"; [ -f "$f" ] || f="$PROJ/input-video.mp4"
  mins=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null | awk '{printf "%d", $1/60+1}')
  [ -n "$mins" ] && echo "info  ~${mins} min of footage: budget about $(awk -v m="$mins" 'BEGIN{printf "%.0f", 2*m*0.34}') GB scratch"
fi

[ $fail -eq 0 ] && echo "preflight: GO" || echo "preflight: STOP"
exit $fail
