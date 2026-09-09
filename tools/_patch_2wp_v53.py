"""Rewrite translate2 cleanly for v53."""
from pathlib import Path

p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")
start = t.find("def translate2(sess, data, freeze15, dx: int, dy: int = 0):")
end = t.find("\ndef west_to_neck(", start)
if start < 0 or end < 0:
    raise SystemExit(f"bad markers {start} {end}")

# Keep finish_nudge2 which is before translate2
new = '''def translate2(sess, data, freeze15, dx: int, dy: int = 0):
    """East translate: proven same-row pair; max 3 distinct lead attempts."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    if len(cur) != 2:
        print(f"  translate2 need exactly 2, got {cur}")
        return data, False
    if me["c"][1] < 34 or any(w[1] < 34 for w in cur):
        print(f"  translate2 refuse shallow ship={me['c']} cur={cur}")
        return data, False
    if not (3 <= dx <= 10):
        print(f"  translate2 dx out of range {dx}")
        return data, False

    g = _plane(data["frame"])
    lead = max(cur, key=lambda w: (w[0], w[1]))
    lag = min(cur, key=lambda w: (w[0], w[1]))
    gap = lead[0] - lag[0]
    me_c = me["c"]
    print(f"  translate2 pair-plan lead={lead} lag={lag} ship={me_c} gap={gap}")

    pairs = []
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

    print(f"  translate2 candidates={pairs[:5]}")
    tried = set()
    for ld, gd in pairs:
        if ld in tried:
            continue
        tried.add(ld)
        if len(tried) > 3:
            break
        data, newc, st = move_wp(sess, data, lead, ld, freeze15)
        print(
            f"  translate2-lead {lead}->{ld} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            continue
        cur2 = count_free14(data["frame"], freeze15)
        if len(cur2) != 2:
            print(f"  translate2 post-lead flock broke {cur2}")
            return data, False
        lag_now = min(cur2, key=lambda w: (w[0], w[1]))
        data, newc, st = move_wp(sess, data, lag_now, gd, freeze15)
        print(
            f"  translate2-lag {lag_now}->{gd} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            print("  translate2 lag noop — stop")
            return data, False
        if len(count_free14(data["frame"], freeze15)) != 2:
            print("  translate2 post-lag flock broke")
            return data, False
        return data, True

    print("  translate2 no pair worked")
    return data, False


'''
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("v53 translate2 ok, finish_nudge present:", "def finish_nudge2" in p.read_text(encoding="utf-8"))
