# Patch lag_haul for v62: y-lift then east; stop on noop.
from pathlib import Path

p = Path("tools/r11l_l3_2wp_probe.py")
text = p.read_text(encoding="utf-8")

start = text.find("def lag_haul_east(")
end = text.find("def finish_nudge2(")
if start < 0 or end < 0:
    raise SystemExit(f"markers missing start={start} end={end}")

new_lag = r'''def lag_haul_east(sess, data, freeze15):
    """Y-lift lag then east on offset row — same-row east hits ship (noop); diagonal merges lead."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    if len(cur) != 2 or me["c"][1] < 34:
        return data, False
    if me["c"][0] < 24 or me["c"][0] >= 28 or step_budget(data["frame"]) < 28:
        return data, False
    lead = max(cur, key=lambda w: (w[0], w[1]))
    lag = min(cur, key=lambda w: (w[0], w[1]))
    me_c = me["c"]

    def _ship():
        return next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"]

    def _n():
        return len(count_free14(data["frame"], freeze15))

    def _bud():
        return step_budget(data["frame"])

    # 1) pure y-lift (same x) — open a lane around the ship
    if lag[1] == me_c[1]:
        lifted = False
        for ly in (38, 34):
            gd = (lag[0], ly)
            if max(abs(gd[0] - me_c[0]), abs(gd[1] - me_c[1])) < 2:
                continue
            if near_any(gd, [lead] + list(freeze15), cheb=5):
                continue
            data, newc, st = move_wp(sess, data, lag, gd, freeze15)
            print(
                f"  lag-haul ylift {lag}->{gd} {st}->{newc} "
                f"ship={_ship() if 'frame' in data else '?'} "
                f"n={_n() if 'frame' in data else '?'} "
                f"bud={_bud() if 'frame' in data else '?'}"
            )
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                return data, False
            if st != "moved":
                continue
            if _n() != 2:
                print("  lag-haul ylift flock broke")
                return data, False
            lag = newc
            me_c = _ship()
            cur = count_free14(data["frame"], freeze15)
            lead = max(cur, key=lambda w: (w[0], w[1]))
            lifted = True
            break
        if not lifted:
            print("  lag-haul ylift failed")
            return data, False

    # 2) east on offset row; cheb_lead>=6 to avoid merge into lead
    cur = count_free14(data["frame"], freeze15)
    lead = max(cur, key=lambda w: (w[0], w[1]))
    lag = min(cur, key=lambda w: (w[0], w[1]))
    me_c = _ship()
    cands = []
    for x in range(lag[0] + 3, lead[0] - 5):
        dest = (x, lag[1])
        cheb = max(abs(dest[0] - lead[0]), abs(dest[1] - lead[1]))
        if cheb < 6 or cheb > 10:
            continue
        fx = (dest[0] + lead[0]) / 2.0
        if fx < 27.5:
            continue
        if max(abs(dest[0] - me_c[0]), abs(dest[1] - me_c[1])) < 2:
            continue
        if near_any(dest, list(freeze15), cheb=5):
            continue
        cands.append((fx, dest))
    cands.sort(reverse=True)
    print(f"  lag-haul east-cands={cands[:5]}")
    for fx, dest in cands[:4]:
        data, newc, st = move_wp(sess, data, lag, dest, freeze15)
        print(
            f"  lag-haul east {lag}->{dest} {st}->{newc} "
            f"ship={_ship() if 'frame' in data else '?'} "
            f"n={_n() if 'frame' in data else '?'} "
            f"bud={_bud() if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            print("  lag-haul east noop — stop (save bud)")
            return data, False
        if _n() != 2:
            print("  lag-haul east flock broke")
            return data, False
        if newc == lead or near_any(newc, [lead], cheb=3):
            print(f"  lag-haul merged into lead {newc}")
            return data, False
        return data, True
    print("  lag-haul no east dest")
    return data, False


'''

text = text[:start] + new_lag + text[end:]

old = """            if success_gate(info):
                break
            if not ok:
                break
            continue
"""
new = """            if success_gate(info):
                break
            if ok:
                continue
            print("  lag-haul soft-fail — stop (do not burn translate)")
            break
"""
if old not in text:
    raise SystemExit("run_probe lag-haul block not found")
text = text.replace(old, new, 1)

p.write_text(text, encoding="utf-8")
print("patched v62")
