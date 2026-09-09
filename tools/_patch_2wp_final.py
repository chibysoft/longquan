from pathlib import Path

p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")
start = t.index("    # Final ship haul:")
end = t.index('    snap(data, freeze15, "after-plant")')
new = r'''    # Skip final-haul when soft-ok ready (2 corridor + y>=25) — (32,34) dead→GO.
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    cor = [c for c in cur if c[1] >= 34]
    if me["c"][1] < 25 and len(cor) >= 1 and step_budget(data["frame"]) >= 8:
        for wp in sorted([w for w in cur if w[1] < 34], key=lambda w: -w[1]):
            others = [c for c in cur if c != wp]
            k = min(cor, key=lambda p: max(abs(p[0] - wp[0]), abs(p[1] - wp[1])))
            dests = [
                (k[0] + 3, k[1]),
                (k[0] + 3, 34),
                (k[0] + 3, 36),
                (28, 36),
                (26, 36),
                (30, 36),
            ]
            for dest in dests:
                if dest[0] <= 16 or dest == wp or not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
                    continue
                if dest[1] < 34:
                    continue
                cheb_k = max(abs(dest[0] - k[0]), abs(dest[1] - k[1]))
                if cheb_k == 3:
                    pass  # merge into keeper
                elif cheb_k >= 5 and not near_any(dest, others + freeze15, cheb=5):
                    pass  # far plant
                else:
                    continue
                if int(_plane(data["frame"])[dest[1], dest[0]]) not in (5, 3, 0, 6):
                    continue
                data, newc, st = move_wp(sess, data, wp, dest, freeze15)
                print(
                    f"  final-haul {wp}->{dest} {st}->{newc} "
                    f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c']} "
                    f"bud={step_budget(data['frame'])}"
                )
                if st == "dead" or data.get("state") == "GAME_OVER":
                    return data, False
                if st == "noop":
                    break
                if st == "moved":
                    break
            me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            if me["c"][1] >= 28:
                break
            cur = count_free14(data["frame"], freeze15)
            cor = [c for c in cur if c[1] >= 34]
'''
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("ok")
