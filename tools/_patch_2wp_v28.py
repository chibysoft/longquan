"""Stabilize collapse: direct y>=36 first; skip footprint when ship north."""
from pathlib import Path

p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")

old = '''        have_corridor_keepers = len(ks) >= 2
        if wp[1] < 34 and wp[0] > 14:
            phases = [("walk", walk_pads), ("direct", direct_pads)]
            if not have_corridor_keepers:
                phases.append(("wrap", wrap_pads))
        elif wp[1] < 34 and wp[0] <= 14:
            phases = [("south", south_pads), ("walk", walk_pads), ("direct", direct_pads)]
        else:
            phases = [("walk", walk_pads), ("direct", direct_pads)]
'''
new = '''        have_corridor_keepers = len(ks) >= 2
        if wp[1] < 34 and wp[0] > 14:
            # Direct first when keepers already on corridor (walk mid-band → dead/noop).
            phases = [("direct", direct_pads), ("walk", walk_pads)]
            if not have_corridor_keepers:
                phases.append(("wrap", wrap_pads))
        elif wp[1] < 34 and wp[0] <= 14:
            phases = [("south", south_pads), ("direct", direct_pads), ("walk", walk_pads)]
        else:
            phases = [("direct", direct_pads), ("walk", walk_pads)]
'''
if old not in t:
    raise SystemExit("phases block missing")
t = t.replace(old, new, 1)

old2 = '''                if phase != "wrap" and not ship_footprint_ok(g, *tci):
                    print(f"    collapse skip pad{pad} nxt{nxt} footprint {tci}")
                    continue
'''
new2 = '''                me_y = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"][1]
                # Ship north: centroid prediction sits in hazard and false-rejects.
                if phase == "direct" and me_y < 34 and nxt[1] < 36:
                    continue
                if phase != "wrap" and me_y >= 34 and not ship_footprint_ok(g, *tci):
                    print(f"    collapse skip pad{pad} nxt{nxt} footprint {tci}")
                    continue
'''
if old2 not in t:
    raise SystemExit("footprint block missing")
t = t.replace(old2, new2, 1)

# Prefer y=36 in direct_pads list
old3 = '''        direct_pads = [
            (k[0] + 3, k[1]),
            (k[0] + 3, 34),
            (k[0] + 3, 36),
            (k[0] - 3, k[1]) if k[0] - 3 > 16 else (k[0] + 3, 36),
            (k[0] - 3, 34) if k[0] - 3 > 16 else (26, 34),
            (26, 34),
            (28, 34),
            (22, 34),
            (24, 36),
            (26, 36),
        ]
'''
new3 = '''        direct_pads = [
            (k[0] + 3, 36),
            (k[0] + 3, k[1]) if k[1] >= 36 else (k[0] + 3, 36),
            (k[0] - 3, 36) if k[0] - 3 > 16 else (k[0] + 3, 36),
            (26, 36),
            (28, 36),
            (22, 36),
            (30, 36),
            (k[0] + 3, 34),
            (26, 34),
            (28, 34),
        ]
'''
if old3 not in t:
    raise SystemExit("direct_pads missing")
t = t.replace(old3, new3, 1)

p.write_text(t, encoding="utf-8")
print("patched ok")
