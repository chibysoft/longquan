from pathlib import Path

p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")
start = t.index("        # Phase order for shallow north of hazard:")
end = t.index("\ndef translate2(sess, data, freeze15, dx: int, dy: int = 0):")
new = r'''        # Phase order for shallow north of hazard:
        #   A) sync-style walk ≤6 toward keeper (safer footprint than one long jump)
        #   B) direct ACTION6 onto corridor cheb==3 of keeper
        #   C) west-wrap ONLY if <2 corridor keepers (wrap previously ate keepers)
        dx = 0 if k[0] == wp[0] else (1 if k[0] > wp[0] else -1)
        dy = 0 if k[1] == wp[1] else (1 if k[1] > wp[1] else -1)
        step_dest = wp
        for _ in range(6):
            nxts = (step_dest[0] + dx, step_dest[1] + dy)
            if not (0 <= nxts[0] < 64 and 0 <= nxts[1] < 64):
                break
            if int(g[nxts[1], nxts[0]]) in (2, 10):
                break
            if max(abs(k[0] - nxts[0]), abs(k[1] - nxts[1])) < 3:
                break
            step_dest = nxts
            if max(abs(k[0] - step_dest[0]), abs(k[1] - step_dest[1])) <= 3:
                break
        walk_pads = [step_dest] if step_dest != wp else []
        direct_pads = [
            (k[0] + 3, k[1]),
            (k[0] + 3, 34),
            (k[0] + 3, 36),
            (k[0] - 3, k[1]) if k[0] - 3 > 16 else (k[0] + 3, 36),
            (k[0] - 3, 34) if k[0] - 3 > 16 else (26, 34),
            (26, 34),
            (28, 34),
            (22, 34),
            (24, 36),
            (26, 36),
        ]
        wrap_pads = [(14, 24), (13, 24), (12, 24), (14, 25), (13, 25)]
        south_pads = [
            (14, 28),
            (14, 32),
            (k[0] + 3, 34),
            (20, 34),
            (22, 34),
            (24, 34),
        ]
        have_corridor_keepers = len(ks) >= 2
        if wp[1] < 34 and wp[0] > 14:
            phases = [("walk", walk_pads), ("direct", direct_pads)]
            if not have_corridor_keepers:
                phases.append(("wrap", wrap_pads))
        elif wp[1] < 34 and wp[0] <= 14:
            phases = [("south", south_pads), ("walk", walk_pads), ("direct", direct_pads)]
        else:
            phases = [("walk", walk_pads), ("direct", direct_pads)]

        moved_one = False
        for phase, pads in phases:
            for pad in pads:
                if not (0 <= pad[0] < 64 and 0 <= pad[1] < 64) or pad == wp:
                    continue
                if phase == "wrap":
                    nxt = pad
                elif phase == "south" and pad[1] < 34:
                    if not (28 <= pad[1] < 34 and pad[0] <= 14):
                        continue
                    nxt = pad
                elif phase == "walk":
                    nxt = pad
                else:
                    if pad[1] < 34 or pad[0] <= 16:
                        continue
                    nxt = pad
                cheb_k = max(abs(nxt[0] - k[0]), abs(nxt[1] - k[1]))
                if phase == "direct" and (nxt == k or cheb_k < 3 or cheb_k > 4):
                    rewritten = False
                    for alt in (
                        (k[0] + 3, k[1]),
                        (k[0] + 3, 34),
                        (k[0] + 3, 36),
                        (k[0] - 3, k[1]),
                        (k[0] - 3, 34),
                        (k[0], max(34, k[1] - 3)),
                        (k[0], k[1] + 3) if k[1] + 3 < 64 else (k[0] + 3, 36),
                    ):
                        if alt[1] < 34 or not (0 <= alt[0] < 64) or alt == wp:
                            continue
                        if alt[0] <= 16:
                            continue
                        if max(abs(alt[0] - k[0]), abs(alt[1] - k[1])) != 3:
                            continue
                        if near_any(alt, freeze15, cheb=5):
                            continue
                        others_x = [c for c in cur_now if c != wp and c != k]
                        if near_any(alt, others_x, cheb=3):
                            continue
                        nxt = alt
                        rewritten = True
                        break
                    if not rewritten:
                        print(f"    collapse skip pad{pad} cannot approach {k}")
                        continue
                if phase == "wrap" and nxt[0] >= wp[0]:
                    continue
                if phase == "walk" and nxt[1] < wp[1] and nxt[0] <= wp[0]:
                    continue
                if phase != "wrap" and near_any(nxt, freeze15, cheb=5):
                    print(f"    collapse skip pad{pad} nxt{nxt} near freeze")
                    continue
                if phase == "direct" and nxt[0] <= 16:
                    continue
                trial = [nxt if c == wp else c for c in cur_now]
                tc = centroid(trial)
                tci = (int(round(tc[0])), int(round(tc[1])))
                if phase != "wrap" and not ship_footprint_ok(g, *tci):
                    print(f"    collapse skip pad{pad} nxt{nxt} footprint {tci}")
                    continue
                data, newc, st = move_wp(sess, data, wp, nxt, freeze15)
                print(
                    f"    collapse-{phase} {wp}->{nxt} (→{k}) {st}->{newc} "
                    f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
                    f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                )
                if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                    return data, False
                if st != "moved":
                    continue
                g = _plane(data["frame"])
                moved_one = True
                break
            if moved_one:
                break
        if not moved_one:
            print(f"    collapse no-path {wp} toward {k}")
            continue
    cur = count_free14(data["frame"], freeze15)
    print(f"  collapse end n={len(cur)} cur={cur}")
    return data, len(cur) == 2


'''
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("collapse walk patch ok")
