from pathlib import Path
p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")
old = '''    if gap > 8:
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
'''
new = '''    if gap > 8:
        print(f"  translate2 lag-haul gap={gap} lead={lead} lag={lag}")
        # Try several approach pads toward lead; first success wins.
        pads = []
        for px in (lead[0] - 6, lead[0] - 8, lead[0] - 5, lag[0] + 6, lag[0] + 4, lag[0] + 8):
            for py in (34, 36, 35):
                pads.append((px, py))
        cur_now = count_free14(data["frame"], freeze15)
        others = [c for c in cur_now if c != lag]
        for pad in pads:
            if pad[0] <= lag[0] or pad[1] < 34:
                continue
            if near_any(pad, others + freeze15, cheb=5):
                continue
            nxt = floor_bfs(g, lag, pad, max_step=6)
            if not nxt or nxt == lag:
                continue
            if near_any(nxt, others + freeze15, cheb=5):
                continue
            trial = [nxt if c == lag else c for c in cur_now]
            tc = centroid(trial)
            tci = (int(round(tc[0])), int(round(tc[1])))
            if not ship_footprint_ok(g, *tci):
                continue
            if not centroid_path_ok(cur_now, trial, g, samples=12):
                continue
            data, newc, st = move_wp(sess, data, lag, nxt, freeze15)
            print(
                f"  translate2-lag {lag}->{nxt} (pad{pad}) {st}->{newc} "
                f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
                f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
            )
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                return data, False
            if st == "moved":
                return data, True
            # noop: try next pad (already paid); do not retry same
            continue
        print("  translate2 lag-haul all pads failed")
        return data, False

    ordered = [lag, lead]
    for wp in ordered:
        cur_now = count_free14(data["frame"], freeze15)
        if wp not in cur_now:
            continue
        others = [c for c in cur_now if c != wp]
        dest = (wp[0] + dx, wp[1] + dy)
'''
if old not in t:
    raise SystemExit('block missing')
p.write_text(t.replace(old, new, 1), encoding='utf-8')
print('lag pads ok')
