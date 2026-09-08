from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
text = p.read_text(encoding="utf-8")
marker = "def leap14_once(sess, data, freeze15, lv0, stride=12):"
if "def leap14_west_south" in text:
    print("already patched")
    raise SystemExit(0)
if marker not in text:
    raise SystemExit("marker missing")

fn = '''
def leap14_west_south(sess, data, freeze15, lv0):
    """Lean west-wall descent: 2-3 long south pulls instead of a full diamond.

    After hop1 lands on x~19/y~18, a second 5-move diamond burns ~15 and still
    needs a south-burst. Prefer planting corridor leads at y>=33 with fewer moves.
    """
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    if not (me["c"][0] <= 22 and me["c"][1] < 28):
        return data, False
    if step_budget(data["frame"]) < 14:
        return data, False
    before = me["c"]
    bud0 = step_budget(data["frame"])
    g = _plane(data["frame"])
    cur = count_free14(data["frame"], freeze15)
    print(f"  west_south begin ship={me['c']} cur={cur} bud={bud0}")
    ordered = sorted(cur, key=lambda w: (-w[1], abs(w[0] - 19), -w[0]))
    moves = 0
    for wp in ordered:
        if moves >= 3 or step_budget(data["frame"]) < 10:
            break
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        if me["c"][1] >= 28:
            break
        cur = count_free14(data["frame"], freeze15)
        if wp not in cur:
            continue
        others = [c for c in cur if c != wp]
        dest = None
        cands = []
        if wp[1] < 28:
            for ty in (36, 35, 34, 33):
                for ox in (0, 4, 6, -2, 2, 8):
                    cands.append((wp[0] + ox, ty))
            cands.extend([(24, 33), (28, 33), (14, 36)])
        else:
            for ox in (4, 6, 8, 0):
                cands.append((wp[0] + ox, min(36, wp[1] + 4)))
        for t in cands:
            if not (0 <= t[0] < 64 and 0 <= t[1] < 64):
                continue
            if t == wp or t[1] < 33:
                continue
            if int(g[t[1], t[0]]) not in (5, 3, 0, 6):
                continue
            if near_any(t, others + freeze15, cheb=5):
                continue
            travel = abs(t[0] - wp[0]) + abs(t[1] - wp[1])
            if travel < 4 or travel > 16:
                continue
            trial = [t if c == wp else c for c in cur]
            tc = centroid(trial)
            tci = (int(round(tc[0])), int(round(tc[1])))
            if not ship_footprint_ok(g, *tci):
                continue
            dest = t
            break
        if dest is None:
            continue
        data, newc, st = move_wp(sess, data, wp, dest, freeze15)
        moves += 1
        print(
            f"    west_south {wp}->{dest} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or "frame" not in data:
            return data, False
        if st == "noop":
            continue
        if st == "moved":
            g = _plane(data["frame"])
    if "frame" not in data:
        return data, False
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    moved = me["c"] != before or me["c"][1] > before[1]
    print(
        f"  west_south end ship={me['c']} moves={moves} "
        f"bud={step_budget(data['frame'])} (d{bud0 - step_budget(data['frame'])})"
    )
    return data, moved


'''

insert = '''    # West wall after hop1: lean south instead of second diamond.
    if me["c"][0] <= 22 and 16 <= me["c"][1] < 28:
        data, ok = leap14_west_south(sess, data, freeze15, lv0)
        if data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        if me["c"][1] >= 27:
            return leap14_east_once(sess, data, freeze15, lv0, stride=6)
        if ok:
            return data, True
'''

# Insert function before leap14_once
text = text.replace(marker, fn + marker, 1)
# Insert branch after neck check
needle = '''    if me["c"][1] >= 34 and me["c"][0] >= 20:
        return leap14_east_once(sess, data, freeze15, lv0, stride=6)
    fine = clearance_path(data["frame"], me["c"], goal, step=1)
'''
repl = '''    if me["c"][1] >= 34 and me["c"][0] >= 20:
        return leap14_east_once(sess, data, freeze15, lv0, stride=6)
''' + insert + '''    fine = clearance_path(data["frame"], me["c"], goal, step=1)
'''
if needle not in text:
    raise SystemExit("needle missing")
text = text.replace(needle, repl, 1)
p.write_text(text, encoding="utf-8")
print("patched ok")
