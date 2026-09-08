from pathlib import Path

p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")
start = t.index("    # Corridor plant + south tugs")
end = t.index("def run_probe(")
new = r'''    # Corridor plant + south tugs until ship y>=28 (or 2 staggered plants).
    # Never BFS into y~30–33 hazard — that dead→GAME_OVER.
    g = _plane(data["frame"])
    moves = 0
    while moves < 8 and step_budget(data["frame"]) >= 10:
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        if me["c"][1] >= 28:
            break
        cur = count_free14(data["frame"], freeze15)
        cor = [c for c in cur if c[1] >= 34]
        if len(cor) >= 2:
            xs = sorted(c[0] for c in cor)
            if xs[-1] - xs[0] >= 5 and me["c"][1] >= 26:
                print(f"  plant enough corridor={cor} ship={me['c']} moves={moves}")
                break
        # Prefer southernmost shallow — pulls ship south faster.
        cands_wp = sorted(
            [w for w in cur if w[1] < 34],
            key=lambda w: (-w[1], abs(w[0] - 22)),
        )
        placed = False
        # While ship is north of neck, prefer south corridor pads near wrap (x~18–26),
        # not far-east (32,34) which barely moves ship south.
        if me["c"][1] < 26:
            base_dests = [
                (24, 36),
                (22, 36),
                (20, 36),
                (26, 36),
                (18, 36),
                (24, 34),
                (22, 34),
                (20, 34),
                (28, 36),
                (26, 34),
            ]
        else:
            base_dests = [
                (28, 34),
                (30, 34),
                (26, 34),
                (32, 34),
                (24, 36),
                (22, 36),
                (20, 36),
                (28, 36),
            ]
        for wp in cands_wp:
            others = [c for c in cur if c != wp]
            dests = list(base_dests) + [
                (wp[0] + 6, 36),
                (wp[0] + 4, 36),
                (wp[0] + 2, 36),
                (wp[0], 36),
                (wp[0] + 8, 34),
                (wp[0] + 4, 34),
            ]
            for dest in dests:
                if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64) or dest == wp:
                    continue
                if dest[1] < 34 or dest[0] <= 16:
                    continue
                if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
                    continue
                if near_any(dest, others + freeze15, cheb=5):
                    continue
                travel = abs(dest[0] - wp[0]) + abs(dest[1] - wp[1])
                if travel < 4 or travel > 32:
                    continue
                trial = [dest if c == wp else c for c in cur]
                tc = centroid(trial)
                tci = (int(round(tc[0])), int(round(tc[1])))
                if not ship_footprint_ok(g, *tci):
                    continue
                data, newc, st = move_wp(sess, data, wp, dest, freeze15)
                moves += 1
                print(
                    f"  plant {wp}->{dest} {st}->{newc} "
                    f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c']} "
                    f"bud={step_budget(data['frame'])}"
                )
                if st == "dead" or data.get("state") == "GAME_OVER":
                    return data, False
                if st == "noop":
                    continue
                if st == "moved":
                    g = _plane(data["frame"])
                    placed = True
                    break
            if placed:
                break
        if placed:
            continue
        # Interim south tug — stay at/below y=28 until past hazard, or jump to y>=34.
        tugged = False
        for wp in cands_wp:
            others = [c for c in cur if c != wp]
            for dy, dx in (
                (10, 2),
                (10, 4),
                (8, 4),
                (8, 6),
                (6, 6),
                (12, 0),
                (8, 0),
                (6, 2),
                (6, -2),
                (4, 4),
            ):
                raw_y = wp[1] + dy
                # Skip landing in hazard band 29–33 unless full corridor jump.
                if 29 <= raw_y <= 33:
                    dest = (wp[0] + dx, 34)
                else:
                    dest = (wp[0] + dx, min(36, raw_y))
                if dest[1] <= wp[1] or dest == wp:
                    continue
                if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
                    continue
                if dest[0] <= 14:
                    continue
                if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
                    continue
                if near_any(dest, others + freeze15, cheb=5):
                    continue
                trial = [dest if c == wp else c for c in cur]
                tc = centroid(trial)
                tci = (int(round(tc[0])), int(round(tc[1])))
                if not ship_footprint_ok(g, *tci):
                    continue
                data, newc, st = move_wp(sess, data, wp, dest, freeze15)
                moves += 1
                print(
                    f"  south-tug {wp}->{dest} {st}->{newc} "
                    f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c']} "
                    f"bud={step_budget(data['frame'])}"
                )
                if st == "dead" or data.get("state") == "GAME_OVER":
                    return data, False
                if st == "moved":
                    g = _plane(data["frame"])
                    tugged = True
                    break
            if tugged:
                break
        if not tugged:
            print("  plant/tug stuck", cur, "ship", me["c"])
            break
    snap(data, freeze15, "after-plant")
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    return data, me["c"][1] >= 27


'''
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("patched ok")
