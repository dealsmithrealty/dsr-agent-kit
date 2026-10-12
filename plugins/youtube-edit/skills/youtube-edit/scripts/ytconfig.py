#!/usr/bin/env python3
"""ytconfig.py: the per-user settings for the youtube-edit skill.

Everything that belongs to one person (brand colours, broker name, where renders go, which accounts are connected,
how hard this machine can render) lives in ONE file outside the skill, so a skill update never touches it:

    $YT_CONFIG, else ~/.config/youtube-edit/config.json      (start from config.example.json in the skill folder)

Credentials are never stored here. The config only NAMES Keychain entries in the user's own Keychain
(service "youtube-edit" by default), read with `security find-generic-password -s <service> -a <key> -w`.

Library:   from ytconfig import CFG, ROOT, HF, palette_sub
Shell:     python3 ytconfig.py get workdir          -> the full path of ~/yt-edit
           python3 ytconfig.py path                 -> the config file path
           python3 ytconfig.py check                -> exit 1 (and says why) when the config is missing or incomplete
"""
import copy, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
CONFIG_PATH = os.path.expanduser(os.environ.get("YT_CONFIG") or "~/.config/youtube-edit/config.json")

# The kit's house style. Colour keys are the composer's token NAMES' roles: highlight = --cyan/--amber (key words,
# money), anchor = --blue, punchline = --magenta.
DEFAULTS = {
    "creator_name": "",
    "brand": {"name": "", "highlight": "#FFBB00", "anchor": "#8F6A10", "punchline": "#FCEFAE"},
    "workdir": "~/yt-edit",
    "staging_dir": "~/Movies/YouTube Renders",
    "compliance": {"enabled": True, "broker_name": "", "iabs_url": "", "consumer_protection_url": ""},
    "delivery": {"mode": "local", "drive_folder_path": "",
                 "drive_api": {"folder_id": "", "keychain_service": "youtube-edit", "client_id_key": "google-client-id",
                               "client_secret_key": "google-client-secret", "refresh_token_key": "google-refresh-token",
                               "googleapis_dir": ""}},
    "render": {"workers": 1, "heap_mb": 6144, "gpu": False, "min_free_gb": 40},
    "connectors": {"opusclip": False, "heygen_music": False, "tella": False, "epidemic_sound": False},
    "keychain_service": "youtube-edit",
}
# The kit's colours as they appear in the composer's output, replaced by the user's on the way out.
KIT = {"highlight": "#FFBB00", "anchor": "#8F6A10", "punchline": "#FCEFAE"}


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load():
    try:
        with open(CONFIG_PATH) as f:
            return _merge(DEFAULTS, json.load(f)), True
    except FileNotFoundError:
        return copy.deepcopy(DEFAULTS), False


CFG, HAS_CONFIG = load()
ROOT = os.path.expanduser(os.environ.get("YT_ROOT") or CFG["workdir"])
HF = os.environ.get("HF") or os.path.join(ROOT, "node_modules", ".bin", "hyperframes")


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def palette_sub(text, brand=None):
    """Swap the kit's colours (hex and rgba() forms) for the user's brand colours."""
    brand = brand or CFG["brand"]
    for role, kit_hex in KIT.items():
        new = brand.get(role) or kit_hex
        if new.lower() == kit_hex.lower():
            continue
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", new):
            raise SystemExit("config brand.%s must be a #RRGGBB colour, got %r" % (role, new))
        text = re.sub(re.escape(kit_hex), new.upper(), text, flags=re.I)
        r, g, b = _rgb(kit_hex)
        nr, ng, nb = _rgb(new)
        text = re.sub(r"rgba\(\s*%d\s*,\s*%d\s*,\s*%d\s*," % (r, g, b), "rgba(%d,%d,%d," % (nr, ng, nb), text)
    return text


def problems(cfg=None):
    cfg = cfg or CFG
    out = []
    if not HAS_CONFIG and cfg is CFG:
        return ["no config at %s: run /video-setup (or copy config.example.json there and fill it in)" % CONFIG_PATH]
    if not cfg.get("creator_name"):
        out.append("creator_name is empty")
    if cfg["compliance"].get("enabled") and not cfg["compliance"].get("broker_name"):
        out.append("compliance.broker_name is empty (TREC: videos promoting real estate show the broker name)")
    for role in KIT:
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", cfg["brand"].get(role, "")):
            out.append("brand.%s is not a #RRGGBB colour" % role)
    d = cfg["delivery"]
    if d["mode"] not in ("local", "drive-folder", "drive-api"):
        out.append("delivery.mode must be local, drive-folder or drive-api")
    if d["mode"] == "drive-folder" and not os.path.isdir(os.path.expanduser(d.get("drive_folder_path", ""))):
        out.append("delivery.drive_folder_path does not exist: %r" % d.get("drive_folder_path"))
    if d["mode"] == "drive-api" and not d["drive_api"].get("folder_id"):
        out.append("delivery.drive_api.folder_id is empty")
    return out


def _get(path):
    v = CFG
    for k in path.split("."):
        v = v[k]
    if path in ("workdir", "staging_dir") or path.endswith("_path") or path.endswith("_dir"):
        v = os.path.expanduser(v) if isinstance(v, str) else v
    return v


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "path":
        print(CONFIG_PATH)
    elif cmd == "get":
        v = _get(sys.argv[2])
        print(json.dumps(v) if isinstance(v, (dict, list, bool)) else v)
    elif cmd == "check":
        p = problems()
        for line in p:
            print("FAIL  config: " + line)
        if not p:
            print("ok    config %s (%s, delivery %s)" % (CONFIG_PATH, CFG["creator_name"], CFG["delivery"]["mode"]))
        sys.exit(1 if p else 0)
    else:
        sys.exit("usage: ytconfig.py path | get <key.path> | check")
