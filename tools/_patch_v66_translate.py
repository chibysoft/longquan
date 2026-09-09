from pathlib import Path

p = Path("tools/r11l_l3_2wp_probe.py")
text = p.read_text(encoding="utf-8")
t0 = text.find("def translate2(")
t1 = text.find("def west_to_neck(")
assert t0 > 0 and t1 > 0, (t0, t1)

new = '''def translate2(sess, data, freeze15, dx: int = 5, dy: int = 0):
    """v66: lead+5, ylift lag, then offset-row east aiming ship x>=28."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    if len(cur) != 2:
        print(f"  translate2 need exactly 2, got {cur}")
        return data, False
    if me["c"][1] < 34 or any(w[1] < 34 for w in cur):
        print(f"  translate2 refuse shallow ship={me['c']} cur={cur}")
        return data, False

    lead = max(cur, key=lambda w: (w[0], w[1]))
    lag = min(cur, key=lambda w: (w[0], w[1]))
    print(f"  translate2 v66 lead={lead} lag={lag} ship={me['c']}")

    ld = (lead[0] + 5, lead[1])
    data, newc, st = move_wp(sess, data, lead, ld, freeze15)
    print(
        f"  translate2-lead {lead}->{ld} {st}->{newc} "
        f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
    )
    if st != "moved" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, False
    cur2 = count_free14(data["frame"], freeze15)
    if len(cur2) != 2:
        print(f"  translate2 post-lead flock broke {cur2}")
        return data, False
    lag_now = min(cur2, key=lambda w: (w[0], w[1]))
    lead_now = max(cur2, key=lambda w: (w[0], w[1]))
    me2 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"]

    # Y-lift while ship still ~23 (fails later at ship=26).
    if abs(lag_now[1] - me2[1]) < 2:
        for ly in (38, 34):
            gd = (lag_now[0], ly)
            if max(abs(gd[0] - me2[0]), abs(gd[1] - me2[1])) < 2:
                continue
            if near_any(gd, [lead_now] + list(freeze15), cheb=5):
                continue
            data, newc, st = move_wp(sess, data, lag_now, gd, freeze15)
            print(
                f"  translate2-ylift {lag_now}->{gd} {st}->{newc} "
                f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
                f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
                f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
            )
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                return data, False
            if st != "moved":
                continue
            if len(count_free14(data["frame"], freeze15)) != 2:
                print("  translate2 ylift flock broke")
                return data, False
            lag_now = newc
            me2 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"]
            cur2 = count_free14(data["frame"], freeze15)
            lead_now = max(cur2, key=lambda w: (w[0], w[1]))
            break

    # Offset-row east only (same-row truncates west of ship).
    lag_cands = []
    for tx in (28, 27, 26, 25, 29, 24):
        gd = (tx, lag_now[1])
        cheb = max(abs(gd[0] - lead_now[0]), abs(gd[1] - lead_now[1]))
        if cheb < 5 or cheb > 12:
            continue
        fx = (gd[0] + lead_now[0]) / 2.0
        if fx < 27.5:
            continue
        if max(abs(gd[0] - me2[0]), abs(gd[1] - me2[1])) < 2:
            continue
        if near_any(gd, [lead_now] + list(freeze15), cheb=5):
            continue
        lag_cands.append((fx, gd))
    lag_cands.sort(reverse=True)
    print(f"  translate2-lag cands={lag_cands[:5]}")
    if not lag_cands:
        print("  translate2 no lag dest")
        return data, False
    gd = lag_cands[0][1]
    data, newc, st = move_wp(sess, data, lag_now, gd, freeze15)
    print(
        f"  translate2-lag {lag_now}->{gd} {st}->{newc} "
        f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
        f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
    )
    if st != "moved" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, False
    if len(count_free14(data["frame"], freeze15)) != 2:
        print("  translate2 post-lag flock broke")
        return data, False
    if near_any(newc, [lead_now], cheb=3) or newc == lead_now:
        print(f"  translate2-lag merged into lead {newc}")
        return data, False
    return data, True


'''

p.write_text(text[:t0] + new + text[t1:], encoding="utf-8")
print("translate2 v66 written")
