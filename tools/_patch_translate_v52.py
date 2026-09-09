from pathlib import Path
p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")
start = t.index("def _translate_dest_ok(")
end = t.index("\ndef west_to_neck(")
new = '''def _translate_dest_ok(g, cur, wp, dest, others, freeze15, me, *, close_gap=False):
    if dest[1] < 34 or not (0 <= dest[0] < 64):
        return False
    if dest == wp or dest[0] <= wp[0]:
        return False
    if max(abs(dest[0] - me[0]), abs(dest[1] - me[1])) < 3:
        return False
    # Lag must finish east of ship when ship sits between flock.
    if others and wp[0] < me[0] < max(others, key=lambda p: p[0])[0]:
        if dest[0] < me[0] + 3:
            return False
    if close_gap:
        # Allow cheb 3–4 to lead (still off-sprite); full cheb5 blocks all pairs.
        if any(max(abs(dest[0] - o[0]), abs(dest[1] - o[1])) < 3 for o in others):
            return False
        if near_any(dest, list(freeze15), cheb=5):
            return False
    else:
        if near_any(dest, list(others) + list(freeze15), cheb=5):
            return False
    return True


def translate2(sess, data, freeze15, dx: int, dy: int = 0):
    """East translate: find lead+lag pair (relaxed cheb); lag-first fallback."""
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

    def find_pair(lead_first=True):
        lead_steps = [s for s in (dx, dx - 1, 4, 3, 2) if s >= 2 and gap + s <= 12]
        for adx in lead_steps:
            for ady in (0, 2, -2):
                ld = (lead[0] + adx, min(38, max(34, lead[1] + ady)))
                if not _translate_dest_ok(g, cur, lead, ld, [lag], freeze15, me_c):
                    continue
                trial_lead = [ld if c == lead else c for c in cur]
                tc = centroid(trial_lead)
                me_pred = (int(round(tc[0])), int(round(tc[1])))
                for lax in range(5, 14):
                    for lay in (0, 2, -2, 1, -1):
                        gd = (lag[0] + lax, min(38, max(34, lag[1] + lay)))
                        cheb_l = max(abs(gd[0] - ld[0]), abs(gd[1] - ld[1]))
                        if not (4 <= cheb_l <= 8):
                            continue
                        if not _translate_dest_ok(
                            g, trial_lead, lag, gd, [ld], freeze15, me_pred, close_gap=True
                        ):
                            continue
                        return (ld, gd)
        return None

    pair = find_pair()
    order = "lead-lag"
    if pair is None:
        # Lag-first: haul lag east of ship (y+/-2), then lead +dx with new gap.
        print("  translate2 try lag-first haul")
        lag_dest = None
        for lax in range(6, 14):
            for lay in (0, 2, -2, 1, -1):
                gd = (lag[0] + lax, min(38, max(34, lag[1] + lay)))
                if not _translate_dest_ok(g, cur, lag, gd, [lead], freeze15, me_c, close_gap=True):
                    continue
                cheb_l = max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1]))
                if cheb_l < 4 or cheb_l > 10:
                    continue
                lag_dest = gd
                break
            if lag_dest:
                break
        if lag_dest is None:
            print("  translate2 no pair / lag-haul — abort")
            return data, False
        data, newc, st = move_wp(sess, data, lag, lag_dest, freeze15)
        print(
            f"  translate2-lag1st {lag}->{lag_dest} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            print("  translate2 lag1st noop — abort")
            return data, False
        g = _plane(data["frame"])
        cur = count_free14(data["frame"], freeze15)
        if len(cur) != 2:
            print(f"  translate2 lag1st flock broke {cur}")
            return data, False
        lead = max(cur, key=lambda w: (w[0], w[1]))
        lag = min(cur, key=lambda w: (w[0], w[1]))
        me_c = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"]
        gap = lead[0] - lag[0]
        pair = find_pair()
        if pair is None:
            # Just lead after lag haul
            for adx in (dx, 3, 2, 4):
                if gap + adx > 12:
                    continue
                ld = (lead[0] + adx, lead[1])
                if _translate_dest_ok(g, cur, lead, ld, [lag], freeze15, me_c):
                    pair = (ld, None)
                    break
        order = "lag-lead"
        if pair is None:
            print("  translate2 post-lag1st no lead — keep lag progress")
            return data, True

    lead_dest, lag_dest = pair
    seq = []
    if order == "lead-lag":
        seq = [("lead", lead, lead_dest), ("lag", lag, lag_dest)]
    else:
        if lag_dest is not None:
            seq = [("lead", lead, lead_dest), ("lag", lag, lag_dest)]
        else:
            seq = [("lead", lead, lead_dest)]

    for name, wp, dest in seq:
        if dest is None:
            continue
        cur_now = count_free14(data["frame"], freeze15)
        if len(cur_now) != 2:
            print(f"  translate2 flock broke before {name}")
            return data, False
        # Refresh wp identity after prior moves
        lead = max(cur_now, key=lambda w: (w[0], w[1]))
        lag = min(cur_now, key=lambda w: (w[0], w[1]))
        wp = lead if name == "lead" else lag
        data, newc, st = move_wp(sess, data, wp, dest, freeze15)
        print(
            f"  translate2-{name} {wp}->{dest} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            if name == "lag":
                print("  translate2 lag noop — keep lead progress")
                return data, True
            print(f"  translate2 {name} noop — abort")
            return data, False
        g = _plane(data["frame"])
        if len(count_free14(data["frame"], freeze15)) != 2:
            print("  translate2 post-move flock broke")
            return data, False
    return data, True


'''
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("translate2 replaced")
