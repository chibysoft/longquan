"""v55: reshape cap3; lead max+5; lag-only finish haul."""
from pathlib import Path

p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")

t = t.replace(
    "        if chrome == 14 and max_moves > 4:\n            max_moves = 4\n",
    "        if chrome == 14 and max_moves > 3:\n            max_moves = 3\n",
    1,
)

t = t.replace(
    "def run_probe(dx_list=(7, 5, 4)):",
    "def run_probe(dx_list=(5,)):",
    1,
)

# Cap lead steps at 5 in translate2
t = t.replace(
    "    for adx in (7, 8, 6, 5, dx, 4):\n        if adx < 4 or gap + adx > 18:",
    "    for adx in (5, 4, dx):\n        if adx < 4 or adx > 5 or gap + adx > 16:",
    1,
)

# Replace near-gate block with lag-only haul
old = """        # Near gate but short: small dual only (never lead-only — drops flock).
        if info["ship"][0] >= 25 and info["n"] == 2 and info["bud"] >= 30:
            dx = min(dx, 4)
"""

# Insert lag_haul function before finish_nudge if missing
if "def lag_haul_east(" not in t:
    t = t.replace(
        "def finish_nudge2(sess, data, freeze15):",
        '''def lag_haul_east(sess, data, freeze15):
    """Move lag only (lead-only drops flock). Target final centroid x>=28."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    if len(cur) != 2 or me["c"][1] < 34:
        return data, False
    if me["c"][0] < 24 or step_budget(data["frame"]) < 28:
        return data, False
    lead = max(cur, key=lambda w: (w[0], w[1]))
    lag = min(cur, key=lambda w: (w[0], w[1]))
    g = _plane(data["frame"])
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
    return data, False


def finish_nudge2(sess, data, freeze15):''',
        1,
    )

new = """        # Near gate: lag-only haul (lead-only drops flock).
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
    raise SystemExit("near-gate block not found")
t = t.replace(old, new, 1)

p.write_text(t, encoding="utf-8")
print("v55 ok")
