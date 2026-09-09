"""Patch plant wrap-stop + collapse keeper/pads toward v16 path."""
from pathlib import Path
import re

p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")

t = t.replace(
    "wrap_shallow = [c for c in cur if c[0] <= 16 and c[1] < 28]",
    "wrap_shallow = [c for c in cur if c[0] <= 14 and c[1] < 28]",
    1,
)

old = """        walk_pads = [step_dest] if step_dest != wp else []
        direct_pads = [
            (k[0] + 3, 36),
            (k[0] - 3, 36) if k[0] - 3 > 16 else (k[0] + 3, 36),
            (k[0] + 3, 38),
            (k[0] - 3, 38) if k[0] - 3 > 16 else (k[0] + 3, 38),
            (k[0] + 3, k[1]),
            (k[0] - 3, k[1]) if k[0] - 3 > 16 else (k[0] + 3, 36),
        ]"""
new = """        walk_pads = [step_dest] if step_dest != wp else []
        # Proven v16 order: (21,36) then (27,36).
        direct_pads = [
            (21, 36),
            (27, 36),
            (k[0] + 3, 36),
            (k[0] - 3, 36) if k[0] - 3 > 16 else (k[0] + 3, 36),
            (24, 36),
            (30, 36),
        ]"""
if old not in t:
    raise SystemExit("direct_pads block not found")
t = t.replace(old, new, 1)

oldk = """        # Prefer nearest corridor keeper with x>=20 (merge cheb=3); avoid ultra-long deadly jumps.
        ks_e = [c for c in ks if c[0] >= 20] or ks
        k = min(
            ks_e,
            key=lambda p: (
                max(abs(p[0] - wp[0]), abs(p[1] - wp[1])),
                -p[0],
            ),
        )"""
newk = """        # Always absorb toward EASTERNMOST corridor keeper (v16).
        k = max(ks, key=lambda p: (p[0], p[1]))
        if wp[0] <= 16:
            east = [c for c in ks if c[0] >= 20]
            if east:
                k = max(east, key=lambda p: p[0])"""
if oldk not in t:
    raise SystemExit("keeper block not found")
t = t.replace(oldk, newk, 1)

# plant enough: break at y>=26 once wrap cleared (not y>=25 with continued tug)
t = t.replace(
    'elif xs[-1] - xs[0] >= 5 and me["c"][1] >= 25:',
    'elif xs[-1] - xs[0] >= 5 and me["c"][1] >= 26:',
    1,
)

# tug_wps: only true wrap col x<=14
t = t.replace(
    "[w for w in cur if w[0] <= 16 and w[1] < 28]",
    "[w for w in cur if w[0] <= 14 and w[1] < 28]",
)

p.write_text(t, encoding="utf-8")
print("patched ok")
