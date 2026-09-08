from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")
# Prefer staggered corridor landings in west_south.
old = """        if wp[1] < 28:
            for ty in (36, 35, 34, 33):
                for ox in (0, 4, 6, -2, 2, 8):
                    cands.append((wp[0] + ox, ty))
            cands.extend([(24, 33), (28, 33), (14, 36)])
"""
new = """        if wp[1] < 28:
            # Stagger landings so 3 south pulls don't stack on y=36 and merge.
            cands.extend([
                (24, 33), (28, 34), (14, 36), (20, 36),
                (wp[0], 34), (wp[0] + 4, 34), (wp[0] + 6, 33),
                (wp[0], 36), (wp[0] + 4, 36), (wp[0] - 2, 35),
            ])
            for ty in (34, 33, 36, 35):
                for ox in (0, 4, 6, -2, 2, 8):
                    cands.append((wp[0] + ox, ty))
"""
if old not in t:
    raise SystemExit("west_south cands missing")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("stagger ok")
