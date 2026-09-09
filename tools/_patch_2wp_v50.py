"""v50: restore v16 plant; reshape cap 4; translate gap already loosened."""
from pathlib import Path

p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")

t = t.replace(
    """        # Prefer eastern pair so ship forms nearer x>=28 (save translate bud).
        # Fallback to v16 (24,36)+(18,36) if east blocked.
        base_dests = [
            (24, 36),
            (30, 36),
            (32, 36),
            (18, 36),
            (20, 36),
            (26, 36),
        ]""",
    """        # Proven v16 pair. Eastern (30,36) made wrap-tug dead→GO.
        base_dests = [
            (24, 36),
            (18, 36),
            (30, 36),
            (20, 36),
            (26, 36),
            (32, 36),
        ]""",
    1,
)

# Inject reshape cap monkeypatch at start of run_probe
needle = "def run_probe(dx_list=(5, 5, 6, 6)):\n"
if needle not in t:
    # try current signature
    import re
    m = re.search(r"def run_probe\(dx_list=\([^)]+\)\):\n", t)
    if not m:
        raise SystemExit("run_probe not found")
    needle = m.group(0)

inject = needle + (
    "    # Save ~3 bud on west reshape so 2wp forms with room to translate.\n"
    "    import tools.r11l_l3_sync_probe as _sync\n"
    "    _rr = _sync.reshape_to_pads\n"
    "    def _reshape_cap(sess, data, chrome, locked, pads, lv0, label=\"\", max_moves=5, early_ship_dist=0):\n"
    "        if chrome == 14 and max_moves > 4:\n"
    "            max_moves = 4\n"
    "        return _rr(sess, data, chrome, locked, pads, lv0, label=label, max_moves=max_moves, early_ship_dist=early_ship_dist)\n"
    "    _sync.reshape_to_pads = _reshape_cap\n"
)
if "_reshape_cap" in t:
    print("monkeypatch already present")
else:
    t = t.replace(needle, inject, 1)

# tug: only (16,22) for wrap — don't cascade to dead pads
old_pref = """            pref = []
            if wp[0] <= 16:
                pref = [(16, 22), (15, 22), (14, 24), (13, 24), (16, 24)]"""
new_pref = """            pref = []
            if wp[0] <= 14:
                pref = [(16, 22)]  # v16 only; other pads noop/dead→GO"""
if old_pref in t:
    t = t.replace(old_pref, new_pref, 1)

p.write_text(t, encoding="utf-8")
print("v50 ok")
