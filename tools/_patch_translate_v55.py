from pathlib import Path
p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")
# Fix find_pair loop inside translate2: lead y=36 only, cheb 3-8, try multiple pairs on noop
start = t.index("def translate2(sess, data, freeze15, dx: int, dy: int = 0):")
end = t.index("\ndef west_to_neck(")
new = r'''def translate2(sess, data, freeze15, dx: int, dy: int = 0):
    """East translate: try lead+lag pairs; on lead noop try next pair."""
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

    def iter_pairs():
        lead_steps = [s for s in (dx, dx - 1, 4, 3, 2) if s >= 2 and gap + s <= 12]
        for adx in lead_steps:
            # Prefer same-row y=36; only then y+/-2.
            for ady in (0, 2, -2):
                ld = (lead[0] + adx, min(38, max(34, lead[1] + ady)))
                if not _translate_dest_ok(g, cur, lead, ld, [lag], freeze15, me_c):
                    continue
                trial_lead = [ld if c == lead else c for c in cur]
                tc = centroid(trial_lead)
                me_pred = (int(round(tc[0])), int(round(tc[1])))
                for lax in range(5, 14):
                    for lay in (0, 2, -2):
                        gd = (lag[0] + lax, min(38, max(34, lag[1] + lay)))
                        cheb_l = max(abs(gd[0] - ld[0]), abs(gd[1] - ld[1]))
                        if not (3 <= cheb_l <= 8):
                            continue
                        if not _translate_dest_ok(
                            g, trial_lead, lag, gd, [ld], freeze15, me_pred, close_gap=True
                        ):
                            continue
                        yield ld, gd

    # Also try lag-first haul candidates before giving up.
    def try_lag_first():
        nonlocal data, g, lead, lag, me_c, gap, cur
        for lax in range(6, 14):
            for lay in (0, 2, -2):
                gd = (lag[0] + lax, min(38, max(34, lag[1] + lay)))
                if not _translate_dest_ok(g, cur, lag, gd, [lead], freeze15, me_c, close_gap=True):
                    continue
                cheb_l = max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1]))
                if cheb_l < 3 or cheb_l > 10:
                    continue
                data, newc, st = move_wp(sess, data, lag, gd, freeze15)
                print(
                    f"  translate2-lag1st {lag}->{gd} {st}->{newc} "
                    f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
                    f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                )
                if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                    return False
                if st != "moved":
                    continue
                g = _plane(data["frame"])
                cur = count_free14(data["frame"], freeze15)
                if len(cur) != 2:
                    return False
                lead = max(cur, key=lambda w: (w[0], w[1]))
                lag = min(cur, key=lambda w: (w[0], w[1]))
                me_c = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"]
                gap = lead[0] - lag[0]
                for adx in (dx, 3, 2, 4):
                    if gap + adx > 12:
                        continue
                    ld = (lead[0] + adx, lead[1])
                    if not _translate_dest_ok(g, cur, lead, ld, [lag], freeze15, me_c):
                        continue
                    data, newc, st = move_wp(sess, data, lead, ld, freeze15)
                    print(
                        f"  translate2-lead {lead}->{ld} {st}->{newc} "
                        f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
                        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                    )
                    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                        return False
                    if st == "moved":
                        return True
                return True  # lag moved even if lead failed
        return False

    for ld, gd in iter_pairs():
        data, newc, st = move_wp(sess, data, lead, ld, freeze15)
        print(
            f"  translate2-lead {lead}->{ld} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            continue  # try next pair
        g = _plane(data["frame"])
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
            print("  translate2 lag noop — keep lead progress")
            return data, True
        if len(count_free14(data["frame"], freeze15)) != 2:
            print("  translate2 post-lag flock broke")
            return data, False
        return data, True

    print("  translate2 no lead-lag pair worked — try lag-first")
    ok = try_lag_first()
    return data, bool(ok)


'''
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("ok")
