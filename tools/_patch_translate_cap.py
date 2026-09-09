from pathlib import Path
p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")
start = t.index("def translate2(sess, data, freeze15, dx: int, dy: int = 0):")
end = t.index("\ndef west_to_neck(")
new = '''def translate2(sess, data, freeze15, dx: int, dy: int = 0):
    """East translate. Ship-between → lead-only with gap cap (avoid seal-jump to 1wp)."""
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
    ship_between = lag[0] < me["c"][0] < lead[0]

    if ship_between:
        order_names = ["lead"]
        print(f"  translate2 ship-between — lead-only lead={lead} lag={lag} gap={lead[0]-lag[0]}")
    else:
        order_names = ["lag", "lead"]

    for name in order_names:
        cur_now = count_free14(data["frame"], freeze15)
        if len(cur_now) != 2:
            print(f"  translate2 flock broke n={len(cur_now)} {cur_now}")
            return data, False
        lead = max(cur_now, key=lambda w: (w[0], w[1]))
        lag = min(cur_now, key=lambda w: (w[0], w[1]))
        wp = lead if name == "lead" else lag
        others = [c for c in cur_now if c != wp]
        me_now = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"]
        gap_now = lead[0] - lag[0]
        steps = [dx, dx - 1, dx - 2, 3, 4, 2]
        if name == "lead":
            # Keep post-move gap <= 12 (wider → seal-jump collapses to 1wp).
            steps = [s for s in steps if s >= 2 and gap_now + s <= 12]
            if not steps:
                print(f"  translate2 lead gap-blocked gap={gap_now} — need lag")
                return data, False
        cands = []
        for adx in steps:
            for ady in (0, 2, -2):
                cands.append((wp[0] + adx, min(38, max(34, wp[1] + ady))))
        picked = None
        for dest in cands:
            if dest[1] < 34 or not (0 <= dest[0] < 64):
                continue
            if dest == wp or dest[0] <= wp[0]:
                continue
            if max(abs(dest[0] - me_now[0]), abs(dest[1] - me_now[1])) < 3:
                continue
            if near_any(dest, others + freeze15, cheb=5):
                continue
            trial = [dest if c == wp else c for c in cur_now]
            tc = centroid(trial)
            tci = (int(round(tc[0])), int(round(tc[1])))
            if not ship_footprint_ok(g, *tci):
                continue
            if not centroid_path_ok(cur_now, trial, g, samples=12):
                continue
            picked = dest
            break
        if picked is None:
            print(f"  translate2 no dest for {name}={wp}")
            return data, False
        data, newc, st = move_wp(sess, data, wp, picked, freeze15)
        print(
            f"  translate2-{name} {wp}->{picked} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            print("  translate2 noop — abort")
            return data, False
        g = _plane(data["frame"])
        cur_after = count_free14(data["frame"], freeze15)
        if len(cur_after) != 2:
            print(f"  translate2 post-move n={len(cur_after)} {cur_after}")
            return data, len(cur_after) == 2
    return data, True


'''
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("translate2 replaced")
