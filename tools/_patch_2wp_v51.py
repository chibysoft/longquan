"""Replace translate2 with corridor-row pair planner that retries on lead noop."""
from pathlib import Path

p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")
start = t.find("def translate2(sess, data, freeze15, dx: int, dy: int = 0):")
end = t.find("\ndef west_to_neck(", start)
if start < 0 or end < 0:
    raise SystemExit(f"markers {start} {end}")

new = '''def translate2(sess, data, freeze15, dx: int, dy: int = 0):
    """East translate on y=36 band: try lead+lag pairs until both move."""
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

    # Prefer large lead steps; stay on same row (ady=0). Temp gap up to 18.
    lead_steps = []
    for s in (dx, dx + 1, dx - 1, 6, 5, 4, 7, 3):
        if s >= 3 and gap + s <= 18 and s not in lead_steps:
            lead_steps.append(s)

    pairs = []
    for adx in lead_steps:
        ld = (lead[0] + adx, lead[1])  # same row only
        if not _translate_dest_ok(g, cur, lead, ld, [lag], freeze15, me_c):
            continue
        trial_lead = [ld if c == lead else c for c in cur]
        tc = centroid(trial_lead)
        me_pred = (int(round(tc[0])), int(round(tc[1])))
        for lax in range(6, 16):
            gd = (lag[0] + lax, lag[1])  # same row
            cheb_l = max(abs(gd[0] - ld[0]), abs(gd[1] - ld[1]))
            if not (5 <= cheb_l <= 10):
                continue
            if not _translate_dest_ok(
                g, trial_lead, lag, gd, [ld], freeze15, me_pred, close_gap=True
            ):
                continue
            pairs.append((ld, gd))

    if not pairs:
        print("  translate2 no same-row pairs — abort")
        return data, False

    print(f"  translate2 candidates={pairs[:4]}{'...' if len(pairs)>4 else ''}")
    for lead_dest, lag_dest in pairs:
        # Dry identity from current frame each attempt (no prior move).
        cur0 = count_free14(data["frame"], freeze15)
        if len(cur0) != 2:
            return data, False
        lead0 = max(cur0, key=lambda w: (w[0], w[1]))
        lag0 = min(cur0, key=lambda w: (w[0], w[1]))
        data, newc, st = move_wp(sess, data, lead0, lead_dest, freeze15)
        print(
            f"  translate2-lead {lead0}->{lead_dest} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            print("  translate2 lead noop — try next pair")
            continue
        cur1 = count_free14(data["frame"], freeze15)
        if len(cur1) != 2:
            print(f"  translate2 post-lead flock broke {cur1}")
            return data, False
        lag1 = min(cur1, key=lambda w: (w[0], w[1]))
        data, newc, st = move_wp(sess, data, lag1, lag_dest, freeze15)
        print(
            f"  translate2-lag {lag1}->{lag_dest} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            print("  translate2 lag noop after lead — stop (no further burn)")
            return data, False
        if len(count_free14(data["frame"], freeze15)) != 2:
            print("  translate2 post-lag flock broke")
            return data, False
        return data, True

    print("  translate2 all pairs failed")
    return data, False


'''
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("translate2 replaced")
