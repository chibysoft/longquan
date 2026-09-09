"""v52: finishing lead-nudge when ship x>=24; stop full translate near gate."""
from pathlib import Path

p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")

# Insert finish_nudge before translate2
if "def finish_nudge2(" not in t:
    marker = "def translate2(sess, data, freeze15, dx: int, dy: int = 0):"
    nudge = '''def finish_nudge2(sess, data, freeze15):
    """One small lead-east when ship already mid-corridor; pred centroid x>=28."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    if len(cur) != 2 or me["c"][1] < 34:
        return data, False
    if me["c"][0] < 24 or step_budget(data["frame"]) < 30:
        return data, False
    lead = max(cur, key=lambda w: (w[0], w[1]))
    lag = min(cur, key=lambda w: (w[0], w[1]))
    g = _plane(data["frame"])
    for adx in (4, 3, 5, 2):
        ld = (lead[0] + adx, lead[1])
        if ld[0] >= 64:
            continue
        trial = [ld if c == lead else c for c in cur]
        tc = centroid(trial)
        tci = (int(round(tc[0])), int(round(tc[1])))
        if tci[0] < 28:
            continue
        if max(abs(ld[0] - me["c"][0]), abs(ld[1] - me["c"][1])) < 3:
            continue
        if near_any(ld, [lag] + list(freeze15), cheb=5):
            continue
        if not ship_footprint_ok(g, *tci):
            continue
        data, newc, st = move_wp(sess, data, lead, ld, freeze15)
        print(
            f"  finish-nudge lead {lead}->{ld} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            continue
        if len(count_free14(data["frame"], freeze15)) != 2:
            print("  finish-nudge flock broke")
            return data, False
        return data, True
    return data, False


'''
    t = t.replace(marker, nudge + marker, 1)

# In run_probe translate loop: after a successful round, prefer finish_nudge; shrink dx near gate
old = """    for round_i, dx in enumerate(dx_list):
        if step_budget(d["frame"]) < 8:
            break
        if success_gate(info):
            break
        if info["ship"][1] < 34 or any(w[1] < 34 for w in info["free14"]):
            print(f"  translate refuse shallow ship={info['ship']} free={info['free14']}")
            break
        # Prefer short strides when bud is tight relative to gate.
        if info["bud"] < 34 and dx > 5:
            dx = 5
        print(f"--- translate round{round_i} dx={dx} ---")
        d, ok = translate2(sess, d, freeze15, dx=dx, dy=0)
"""

new = """    for round_i, dx in enumerate(dx_list):
        if step_budget(d["frame"]) < 8:
            break
        if success_gate(info):
            break
        if info["ship"][1] < 34 or any(w[1] < 34 for w in info["free14"]):
            print(f"  translate refuse shallow ship={info['ship']} free={info['free14']}")
            break
        # Close to gate: one lead nudge, do not open gap with full dual translate.
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
        if info["bud"] < 34 and dx > 5:
            dx = 5
        print(f"--- translate round{round_i} dx={dx} ---")
        d, ok = translate2(sess, d, freeze15, dx=dx, dy=0)
"""

if old not in t:
    raise SystemExit("translate loop block not found")
t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")
print("v52 ok")
