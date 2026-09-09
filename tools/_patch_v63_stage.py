# v63: lead-only first hop; staged lag ylift+east while ship still ~23.
from pathlib import Path

p = Path("tools/r11l_l3_2wp_probe.py")
text = p.read_text(encoding="utf-8")

# --- replace translate2 ---
t0 = text.find("def translate2(")
t1 = text.find("def west_to_neck(")
if t0 < 0 or t1 < 0:
    raise SystemExit("translate2 markers missing")

new_t2 = r'''def translate2(sess, data, freeze15, dx: int = 5, dy: int = 0):
    """v63: lead +5 ONLY. Lag staged later while ship still ~23 (ylift works)."""
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
    ld = (lead[0] + 5, lead[1])
    print(f"  translate2 lead-only {lead}->{ld} ship={me['c']} lag={lag}")
    data, newc, st = move_wp(sess, data, lead, ld, freeze15)
    print(
        f"  translate2-lead {lead}->{ld} {st}->{newc} "
        f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
        f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
    )
    if st != "moved" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, False
    if len(count_free14(data["frame"], freeze15)) != 2:
        print("  translate2 post-lead flock broke")
        return data, False
    return data, True


'''

text = text[:t0] + new_t2 + text[t1:]

# --- replace lag_haul_east ---
start = text.find("def lag_haul_east(")
end = text.find("def finish_nudge2(")
if start < 0 or end < 0:
    raise SystemExit("lag_haul markers missing")

new_lag = r'''def lag_haul_east(sess, data, freeze15):
    """Stage lag: y-lift then east. Call while ship x is still 23-27."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    if len(cur) != 2 or me["c"][1] < 34:
        return data, False
    if me["c"][0] < 22 or me["c"][0] >= 28 or step_budget(data["frame"]) < 28:
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

    # 1) y-lift if same row as ship
    if abs(lag[1] - me_c[1]) < 2:
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

    # 2) east on offset row — pull ship; keep cheb_lead >= 6
    cur = count_free14(data["frame"], freeze15)
    lead = max(cur, key=lambda w: (w[0], w[1]))
    lag = min(cur, key=lambda w: (w[0], w[1]))
    me_c = _ship()
    # Prefer dest whose midpoint with lead is >= 28
    cands = []
    for x in range(max(lag[0] + 4, me_c[0] - 1), lead[0] - 5):
        dest = (x, lag[1])
        cheb = max(abs(dest[0] - lead[0]), abs(dest[1] - lead[1]))
        if cheb < 6 or cheb > 12:
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
    print(f"  lag-haul east-cands={cands[:6]}")
    for fx, dest in cands[:5]:
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
            print("  lag-haul east noop — stop")
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

# --- run_probe: trigger lag-haul from ship>=23 (after lead-only) ---
old = """        # Near gate: lag-only haul (never lead+large — drops flock).
        if info["ship"][0] >= 25 and info["ship"][0] < 28 and info["n"] == 2 and info["bud"] >= 28:
"""
new = """        # After lead-only: stage lag while ship still 23-27 (ylift fails at ship=26).
        if info["ship"][0] >= 23 and info["ship"][0] < 28 and info["n"] == 2 and info["bud"] >= 28:
"""
if old not in text:
    raise SystemExit("run_probe trigger not found")
text = text.replace(old, new, 1)

p.write_text(text, encoding="utf-8")
print("patched v63")
