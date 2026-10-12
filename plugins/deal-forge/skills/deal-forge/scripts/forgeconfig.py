#!/usr/bin/env python3
"""forgeconfig.py: the per-user settings for the deal-forge skill.

One file outside the skill, so plugin updates never touch it:
    $FORGE_CONFIG, else ~/.config/deal-forge/config.json   (start from config.example.json)
The contact database lives next to it in ~/.local/share/deal-forge/forge.db ($FORGE_DB overrides).
Secrets are never stored here: the config only NAMES an entry in the user's own Keychain.

Shell:  python3 forgeconfig.py check | path | get <key.path>
"""
import copy, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
CONFIG_PATH = os.path.expanduser(os.environ.get("FORGE_CONFIG") or "~/.config/deal-forge/config.json")
DB_PATH = os.path.expanduser(os.environ.get("FORGE_DB") or "~/.local/share/deal-forge/forge.db")
EXPORT_DIR = os.path.expanduser(os.environ.get("FORGE_EXPORT_DIR") or "~/Documents/Deal Forge")

RELATIONSHIPS = ["past_client", "lead", "referral_partner", "friend", "agent", "vendor", "acquaintance", "family"]
OPPORTUNITIES = ["buyer", "seller", "investor", "referral", "none"]

with open(os.path.join(SKILL, "config.example.json")) as _f:
    DEFAULTS = json.load(_f)
DEFAULTS.update({"agent_name": "", "agent_first_name": ""})


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


def secret(key):
    """Read one secret from the user's own Keychain (service from the config). None when absent."""
    svc = CFG["ghl"]["keychain_service"]
    r = subprocess.run(["security", "find-generic-password", "-s", svc, "-a", key, "-w"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def problems():
    if not HAS_CONFIG:
        return ["no config at %s: run /forge-setup" % CONFIG_PATH]
    out = []
    if not CFG.get("agent_name"):
        out.append("agent_name is empty")
    if not CFG.get("agent_first_name"):
        out.append("agent_first_name is empty")
    g = CFG["ghl"]
    if g.get("enabled"):
        if not g.get("location_id"):
            out.append("ghl.enabled but ghl.location_id is empty")
        if not secret(g["token_key"]):
            out.append("ghl.enabled but no token in Keychain (service %s, account %s): run store_secret.py"
                       % (g["keychain_service"], g["token_key"]))
    for rel in CFG["cadence_days"]:
        if rel not in RELATIONSHIPS:
            out.append("cadence_days has unknown relationship %r" % rel)
    return out


def _get(path):
    v = CFG
    for k in path.split("."):
        v = v[k]
    return v


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "path":
        print(CONFIG_PATH)
    elif cmd == "db":
        print(DB_PATH)
    elif cmd == "get":
        v = _get(sys.argv[2])
        print(json.dumps(v) if isinstance(v, (dict, list, bool)) else v)
    elif cmd == "check":
        p = problems()
        for line in p:
            print("FAIL  config: " + line)
        if not p:
            print("ok    config %s (%s, GHL %s)" % (CONFIG_PATH, CFG["agent_name"],
                                                   "on" if CFG["ghl"]["enabled"] else "off"))
        sys.exit(1 if p else 0)
    else:
        sys.exit("usage: forgeconfig.py check | path | db | get <key.path>")
