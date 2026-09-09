"""Patch collapse straggler path: direct ACTION6 to corridor, then wrap."""
from pathlib import Path

p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")
start = t.index("        # Only corridor keepers — shallow straggler must walk around hazard.")
end = t.index(
    '    cur = count_free14(data["frame"], freeze15)\n'
    '    print(f"  collapse end n={len(cur)} cur={cur}")'
)
new = r'''        # Only corridor keepers — shallow straggler must walk around hazard.
        ks = [c for c in cur_now if c[1] >= 34]
        if not ks:
            continue
        k = min(
            ks,
            key=lambda p: (
                max(abs(p[0] - wp[0]), abs(p[1] - wp[1])),
                abs(p[0] - wp[0]),
            ),
        )
        # On wrap column, prefer EASTERN keeper — same-column merge noops.
        if wp[0] <= 16:
            east = [c for c in ks if c[0] >= 20]
            if east:
                k = min(east, key=lambda p: abs(p[0] - 24) + abs(p[1] - 34))

        # Phase order for shallow north of hazard:
        #   A) direct ACTION6 onto corridor cheb==3 of keeper (plant proved this
        #      crosses hazard; floor_bfs dies in y~20–29 — never use it for y>=34)
        #   B) west-wrap interim if A all noop
        #   C) south along wrap then SE
        direct_pads = [
            (k[0] - 3, k[1]),
            (k[0] + 3, k[1]),
            (k[0] - 3, 34),
            (k[0] + 3, 34),
            (k[0] - 3, 36),
            (k[0] + 3, 36),
            (20, 34) if k[0] >= 22 else (26, 34),
            (22, 34),
            (28, 34),
            (24, 36),
            (26, 36),
        ]
        wrap_pads = [(14, 24), (13, 24), (12, 24), (14, 25), (13, 25)]
        south_pads = [
            (14, 28),
            (14, 32),
            (k[0] - 3, 34),
            (k[0] + 3, 34),
            (20, 34),
            (22, 34),
            (24, 34),
        ]
        if wp[1] < 34 and wp[0] > 14:
            phases = [("direct", direct_pads), ("wrap", wrap_pads)]
        elif wp[1] < 34 and wp[0] <= 14:
            phases = [("south", south_pads), ("direct", direct_pads)]
        else:
            phases = [("direct", direct_pads)]

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
                else:
                    if pad[1] < 34:
                        continue
                    nxt = pad  # no BFS — land on corridor pad directly
                # Dest must be cheb 3–4 from keeper (cheb<=2 = on-sprite noop).
                cheb_k = max(abs(nxt[0] - k[0]), abs(nxt[1] - k[1]))
                if phase != "wrap" and (nxt == k or cheb_k < 3 or cheb_k > 4):
                    rewritten = False
                    for alt in (
                        (k[0] - 3, k[1]),
                        (k[0] + 3, k[1]),
                        (k[0] - 3, 34),
                        (k[0] + 3, 34),
                        (k[0], max(34, k[1] - 3)),
                        (k[0], k[1] + 3) if k[1] + 3 < 64 else (k[0] - 3, 36),
                    ):
                        if alt[1] < 34 or not (0 <= alt[0] < 64) or alt == wp:
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
                if phase != "wrap" and near_any(nxt, freeze15, cheb=5):
                    print(f"    collapse skip pad{pad} nxt{nxt} near freeze")
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
'''
t2 = t[:start] + new + t[end:]
p.write_text(t2, encoding="utf-8")
print("patched", p, "delta", len(t2) - len(t))
