from pathlib import Path

p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
text = p.read_text(encoding="utf-8")
start = text.index("def translate2(sess, data, freeze15, dx: int, dy: int = 0):")
end = text.index("\ndef west_to_neck(sess, data, freeze15, lv0):")
new = '''def translate2(sess, data, freeze15, dx: int, dy: int = 0):
    """Pair move. If lag trails by >8, haul lag only (no lead-only race)."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    if len(cur) != 2:
        print(f"  translate2 need exactly 2, got {cur}")
        return data, False
    if me["c"][1] < 34 or any(w[1] < 34 for w in cur):
        print(f"  translate2 refuse shallow ship={me['c']} cur={cur}")
        return data, False
    if not (4 <= dx <= 10):
        print(f"  translate2 dx out of range {dx}")
        return data, False

    g = _plane(data["frame"])
    lead = max(cur, key=lambda w: (w[0], w[1]))
    lag = min(cur, key=lambda w: (w[0], w[1]))
    gap = lead[0] - lag[0]
    if gap > 8:
        print(f"  translate2 lag-haul gap={gap} lead={lead} lag={lag}")
        ordered = [lag]
        target_dx = min(dx, max(4, lead[0] - 6 - lag[0]))
        if target_dx < 4:
            print("  translate2 lag already close enough")
            return data, True
        dx = target_dx
    else:
        ordered = [lag, lead]

    for wp in ordered:
        cur_now = count_free14(data["frame"], freeze15)
        if wp not in cur_now:
            continue
        others = [c for c in cur_now if c != wp]
        dest = (wp[0] + dx, wp[1] + dy)
        if dest[1] < 34 or not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
            print(f"  translate2 bad dest {dest}")
            return data, False
        if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
            nxt = floor_bfs(g, wp, dest, max_step=max(dx, 6))
            if not nxt or nxt == wp:
                print(f"  translate2 blocked cell {dest}")
                return data, False
            dest = nxt
        if near_any(dest, others + freeze15, cheb=5):
            alt = None
            for ady in (0, 2, -2, 1, -1):
                t = (wp[0] + dx, min(38, max(34, wp[1] + ady)))
                if t == wp or not (0 <= t[0] < 64):
                    continue
                if int(g[t[1], t[0]]) not in (5, 3, 0, 6):
                    continue
                if near_any(t, others + freeze15, cheb=5):
                    continue
                alt = t
                break
            if alt is None:
                print(f"  translate2 near sibling/lock {dest}")
                return data, False
            dest = alt
        if any(
            30 <= p[1] <= 38
            and 28 <= p[0] <= 40
            and max(abs(dest[0] - p[0]), abs(dest[1] - p[1])) <= 5
            for p in freeze15
        ):
            print(f"  translate2 seal bubble {dest}")
            return data, False
        trial = [dest if c == wp else c for c in cur_now]
        tc = centroid(trial)
        tci = (int(round(tc[0])), int(round(tc[1])))
        if not ship_footprint_ok(g, *tci):
            print(f"  translate2 footprint fail {trial} cent={tci}")
            return data, False
        if not centroid_path_ok(cur_now, trial, g, samples=12):
            print(f"  translate2 path_ok fail {wp}->{dest}")
            return data, False
        data, newc, st = move_wp(sess, data, wp, dest, freeze15)
        print(
            f"  translate2 {wp}->{dest} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            print("  translate2 abort", st)
            return data, False
        g = _plane(data["frame"])
    return data, True


'''
p.write_text(text[:start] + new + text[end:], encoding="utf-8")
print("translate2 replaced")
