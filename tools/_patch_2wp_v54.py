"""v54: bigger first dual translate; relax lag clear; no lead-only nudge."""
from pathlib import Path

p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")

# Relax lag must be east of ship by +2 (was +3)
t = t.replace(
    "        if dest[0] < me[0] + 3:\n            return False",
    "        if dest[0] < me[0] + 2:\n            return False",
    1,
)

# translate2: prefer larger lead steps first
old = """    pairs = []
    for adx in (5, 6, dx, 4, 7, 3):
        if adx < 3 or gap + adx > 18:
            continue
        ld = (lead[0] + adx, lead[1])
        if not _translate_dest_ok(g, cur, lead, ld, [lag], freeze15, me_c):
            continue
        trial_lead = [ld if c == lead else c for c in cur]
        tc = centroid(trial_lead)
        me_pred = (int(round(tc[0])), int(round(tc[1])))
        for lax in (10, 9, 11, 8, 12, 7, 6):
            gd = (lag[0] + lax, lag[1])
            cheb_l = abs(gd[0] - ld[0])
            if not (5 <= cheb_l <= 10):
                continue
            if not _translate_dest_ok(
                g, trial_lead, lag, gd, [ld], freeze15, me_pred, close_gap=True
            ):
                continue
            pairs.append((ld, gd))
            break  # one lag dest per lead
"""

new = """    pairs = []
    # Need ship x>=28 in ONE dual round (lead-only drops flock). Prefer +7/+8.
    for adx in (7, 8, 6, 5, dx, 4):
        if adx < 4 or gap + adx > 18:
            continue
        ld = (lead[0] + adx, lead[1])
        if not _translate_dest_ok(g, cur, lead, ld, [lag], freeze15, me_c):
            continue
        trial_lead = [ld if c == lead else c for c in cur]
        tc = centroid(trial_lead)
        me_pred = (int(round(tc[0])), int(round(tc[1])))
        for lax in (12, 11, 13, 10, 9, 14, 8):
            gd = (lag[0] + lax, lag[1])
            cheb_l = abs(gd[0] - ld[0])
            if not (5 <= cheb_l <= 10):
                continue
            if not _translate_dest_ok(
                g, trial_lead, lag, gd, [ld], freeze15, me_pred, close_gap=True
            ):
                continue
            # Prefer pairs whose final centroid x >= 28
            final = [gd if c == lag else (ld if c == lead else c) for c in cur]
            # after both: positions ld and gd
            fx = (ld[0] + gd[0]) / 2.0
            pairs.append((ld, gd, fx))
            break
    pairs.sort(key=lambda p: -p[2])
    pairs = [(a, b) for a, b, _ in pairs]
"""

if old not in t:
    raise SystemExit("pairs block not found")
t = t.replace(old, new, 1)

# Disable finish-nudge lead-only (known n→1). Use second dual with small dx instead.
t = t.replace(
    """        # Close to gate: one lead nudge, do not open gap with full dual translate.
        if info["ship"][0] >= 24 and info["n"] == 2 and info["bud"] >= 30:
            print(f"--- finish-nudge round{round_i} ship={info['ship']} bud={info['bud']} ---")
            d, ok = finish_nudge2(sess, d, freeze15)
            if d.get("state") == "GAME_OVER" or "frame" not in d:
                print("FAIL GO on finish-nudge")
                return 1
            freeze15 = lock_other_ship(d["frame"], 14)
            info = snap(d, freeze15, f"after-nudge{round_i}")
            if success_gate(info):
                break
            if not ok:
                break
            continue
""",
    """        # Near gate but short: small dual only (never lead-only — drops flock).
        if info["ship"][0] >= 25 and info["n"] == 2 and info["bud"] >= 30:
            dx = min(dx, 4)
""",
    1,
)

p.write_text(t, encoding="utf-8")
print("v54 ok")
