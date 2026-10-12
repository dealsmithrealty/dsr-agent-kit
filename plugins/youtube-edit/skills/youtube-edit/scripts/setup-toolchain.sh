#!/bin/bash
# setup-toolchain.sh: builds this user's working folder for the youtube-edit skill. Safe to run again.
#   --check   only report what is missing (no installs); exit 1 when something required is missing
#   (none)    create the working folder from config.json "workdir", install the PINNED HyperFrames (npm ci against the
#             committed lockfile), the Parakeet transcriber and the shared asset folders.
# System tools (Homebrew, node, ffmpeg, uv, auto-editor, Chrome) are NOT installed here: Claude asks the user first and
# runs the matching line from the README one at a time.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$HERE")"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/sbin:/usr/bin:/bin:$PATH"
ROOT="${YT_ROOT:-$(python3 "$HERE/ytconfig.py" get workdir)}"
missing=0
need() { if command -v "$1" >/dev/null 2>&1; then echo "ok    $1"; else echo "MISS  $1  -> $2"; missing=1; fi; }

[ "$(uname)" = "Darwin" ] || { echo "FAIL  this kit supports macOS only"; exit 1; }
need brew        '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
need node        'brew install node'
need ffmpeg      'brew install ffmpeg'
need ffprobe     'brew install ffmpeg'
need uv          'brew install uv'
need auto-editor 'uv tool install auto-editor'
python3 -c "import numpy" 2>/dev/null && echo "ok    python3 + numpy" || { echo "MISS  numpy  -> python3 -m pip install --user numpy"; missing=1; }
if [ -d "/Applications/Google Chrome.app" ] || [ -d "$HOME/Applications/Google Chrome.app" ]; then echo "ok    Google Chrome"; else echo "MISS  Google Chrome  -> https://www.google.com/chrome/"; missing=1; fi
if command -v node >/dev/null 2>&1; then
  major=$(node -p 'process.versions.node.split(".")[0]'); [ "$major" -ge 22 ] && echo "ok    node $major" || { echo "MISS  node 22+ (have $major)  -> brew upgrade node"; missing=1; }
fi
free_gb=$(df -g "$HOME" | awk 'NR==2{print $4}'); echo "info  ${free_gb} GB free (a 4K render wants 40+)"
ram_gb=$(( $(sysctl -n hw.memsize) / 1073741824 )); echo "info  ${ram_gb} GB RAM, $(sysctl -n hw.ncpu) cores, $(uname -m)"

[ "${1:-}" = "--check" ] && { [ -x "$ROOT/node_modules/.bin/hyperframes" ] && echo "ok    hyperframes in $ROOT" || { echo "MISS  hyperframes  -> bash $0"; missing=1; }; exit $missing; }
[ $missing -eq 0 ] || { echo "setup: install the MISS lines first, then run this again"; exit 1; }

mkdir -p "$ROOT/videos/_shared/sfx/extra" "$ROOT/videos/_shared/img/thumbs"
cp "$SKILL_DIR/toolchain/package.json" "$SKILL_DIR/toolchain/package-lock.json" "$ROOT/"
( cd "$ROOT" && npm ci --no-audit --no-fund ) || { echo "FAIL  npm ci in $ROOT"; exit 1; }
HF="$ROOT/node_modules/.bin/hyperframes"
echo "ok    hyperframes $("$HF" --version 2>/dev/null | tail -1)"
"$HF" models install parakeet || echo "warn  parakeet install failed: run '$HF models install parakeet' again"
"$HF" skills update media-use >/dev/null 2>&1 && echo "ok    free sound library (media-use)" || echo "warn  media-use sound library not installed (sounds optional)"
( cd "$HERE" && python3 -m unittest tests 2>&1 | tail -3 )
echo "setup: done. Working folder: $ROOT"
