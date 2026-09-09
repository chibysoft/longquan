"""Collapse: dedupe pads, blacklist noop/dead, absorb non-wrap first."""
from pathlib import Path

p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")

old = '''    stragglers = [w for w in cur if w not in keepers]
    print(f"  collapse keepers={keepers} stragglers={stragglers}")
'''
new = '''    stragglers = sorted(
        [w for w in cur if w not in keepers],
        key=lambda w: (0 if w[0] > 16 else 1, -w[1], w[0]),
    )
    print(f"  collapse keepers={keepers} stragglers={stragglers}")
'''
if old not in t:
    raise SystemExit("stragglers line missing")
t = t.replace(old, new, 1)

old2 = '''        moved_one = False
        for phase, pads in phases:
            for pad in pads:
'''
new2 = '''        moved_one = False
        tried = set()
        for phase, pads in phases:
            for pad in pads:
'''
if old2 not in t:
    raise SystemExit("moved_one block missing")
t = t.replace(old2, new2, 1)

# After nxt is finalized and before move_wp, skip tried
needle = '''                trial = [nxt if c == wp else c for c in cur_now]
                tc = centroid(trial)
                tci = (int(round(tc[0])), int(round(tc[1])))
                me_y = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"][1]
'''
if needle not in t:
    # try without me_y line order
    raise SystemExit("trial block missing — check file")
repl = '''                if nxt in tried:
                    continue
                tried.add(nxt)
                trial = [nxt if c == wp else c for c in cur_now]
                tc = centroid(trial)
                tci = (int(round(tc[0])), int(round(tc[1])))
                me_y = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"][1]
'''
t = t.replace(needle, repl, 1)

# On dead: if not GAME_OVER, skip pad; only abort on GO
old3 = '''                if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                    return data, False
                if st != "moved":
                    continue
'''
# Only replace inside collapse_to_2 — first occurrence after collapse-phase print
idx = t.find('f"    collapse-{phase}')
if idx < 0:
    raise SystemExit("collapse-phase print missing")
idx2 = t.find(old3, idx)
if idx2 < 0:
    raise SystemExit("dead handling missing near collapse")
new3 = '''                if data.get("state") == "GAME_OVER" or "frame" not in data:
                    return data, False
                if st == "dead":
                    print(f"    collapse dead pad — skip (not GO)")
                    continue
                if st != "moved":
                    continue
'''
t = t[:idx2] + new3 + t[idx2 + len(old3) :]

p.write_text(t, encoding="utf-8")
print("ok")
