"""v55b: force safe translate + lag-haul; always write."""
from pathlib import Path

p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")

# reshape cap 3
t = t.replace(
    "if chrome == 14 and max_moves > 4:\n            max_moves = 4",
    "if chrome == 14 and max_moves > 3:\n            max_moves = 3",
)

# dx_list
import re
t = re.sub(r"def run_probe\(dx_list=\([^)]*\)\):", "def run_probe(dx_list=(5,)):", t, count=1)

# translate2 lead steps — only +5/+4
t = t.replace(
    """    pairs = []
    # Need ship x>=28 in ONE dual round (lead-only drops flock). Prefer +7/+8.
    for adx in (7, 8, 6, 5, dx, 4):
        if adx < 4 or gap + adx > 18:
            continue
""",
    """    pairs = []
    # lead +5 safe (v51); +7/+8 drops flock to n=1.
    for adx in (5, 4):
        if adx < 4 or gap + adx > 16:
            continue
""",
)

# Insert lag_haul before finish_nudge if missing
if "def lag_haul_east(" not in t:
    t = t.replace(
        "def finish_nudge2(sess, data, freeze15):",
        '''def lag_haul_east(sess, data, freeze15):
    """Move lag only to pull ship east. Lead-only drops flock."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    if len(cur) != 2 or me["c"][1] < 34:
        return data, False
    if me["c"][0] < 24 or step_budget(data["frame"]) < 28:
        return data, False
    lead = max(cur, key=lambda w: (w[0], w[1]))
    lag = min(cur, key=lambda w: (w[0], w[1]))
    cands = []
    for x in range(lag[0] + 4, lead[0] - 4):
        dest = (x, lag[1])
        cheb = abs(dest[0] - lead[0])
        if not (5 <= cheb <= 8):
            continue
        fx = (dest[0] + lead[0]) / 2.0
        if fx < 28:
            continue
        if max(abs(dest[0] - me["c"][0]), abs(dest[1] - me["c"][1])) < 3:
            continue
        if near_any(dest, [lead] + list(freeze15), cheb=5):
            continue
        cands.append((fx, dest))
    cands.sort(reverse=True)
    for fx, dest in cands[:6]:
        data, newc, st = move_wp(sess, data, lag, dest, freeze15)
        print(
            f"  lag-haul {lag}->{dest} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            continue
        if len(count_free14(data["frame"], freeze15)) != 2:
            print("  lag-haul flock broke")
            return data, False
        return data, True
    print("  lag-haul no dest")
    return data, False


def finish_nudge2(sess, data, freeze15):''',
        1,
    )

# Replace finish-nudge block with lag-haul
old = """        # Close to gate: one lead nudge, do not open gap with full dual translate.
        if info["ship"][0] >= 24 and info["n"] == 2 and info["bud"] >= 28:
            print(f"--- finish-nudge round{round_i} ship={info['ship']} bud={info['bud']} ---")
            d, ok = finish_nudge2(sess, d, freeze15)
            if d.get("state") == "GAME_OVER" or "frame" not in d:
                print("FAIL GO on finish-nudge")
                return 1
            freeze15 = lock_other_ship(d["frame"], 14)
            info = snap(d, freeze15, f"after-nudge{round_i}")
            if success_gate(info):
                break
            if ok:
                continue
            # nudge soft-fail: fall through to another dual translate
            print("  finish-nudge soft-fail — fall through translate")
"""

new = """        # Near gate: lag-only haul (never lead-only — drops flock).
        if info["ship"][0] >= 25 and info["n"] == 2 and info["bud"] >= 28:
            print(f"--- lag-haul round{round_i} ship={info['ship']} bud={info['bud']} ---")
            d, ok = lag_haul_east(sess, d, freeze15)
            if d.get("state") == "GAME_OVER" or "frame" not in d:
                print("FAIL GO on lag-haul")
                return 1
            freeze15 = lock_other_ship(d["frame"], 14)
            info = snap(d, freeze15, f"after-laghaul{round_i}")
            if success_gate(info):
                break
            if not ok:
                break
            continue
"""

if old not in t:
    raise SystemExit("finish-nudge block missing:\n" + t[t.find("for round_i") : t.find("for round_i") + 800])
t = t.replace(old, new, 1)

p.write_text(t, encoding="utf-8")
print("wrote v55b")
print("dx", re.search(r"def run_probe\(dx_list=\([^)]*\)\)", t).group(0))
print("adx ok", "for adx in (5, 4):" in t)
print("lag_haul", "def lag_haul_east" in t)
