from pathlib import Path
p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")
start = t.find("    # Gap 9–10:")
if start < 0:
    start = t.find("    # Gap 9-10:")
if start < 0:
    raise SystemExit("gap 9-10 block not found")
end = t.find("    ordered = [lag, lead]", start)
if end < 0:
    raise SystemExit("ordered not found")
new = '''    # Gap 9–10: haul lag toward lead (avoid ship cell / cross — common noop).
    if gap >= 9:
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        hauled = False
        for h in (4, 5, 3, 6, 2):
            for dy in (0, 2, -2, 1, -1):
                dest_lag = (lag[0] + h, min(38, max(34, lag[1] + dy)))
                if dest_lag[0] <= lag[0] or dest_lag[1] < 34:
                    continue
                cheb_l = max(abs(dest_lag[0] - lead[0]), abs(dest_lag[1] - lead[1]))
                if cheb_l < 5 or cheb_l > 8:
                    continue
                if near_any(dest_lag, [lead, tuple(me["c"])] + list(freeze15), cheb=5):
                    continue
                data, newc, st = move_wp(sess, data, lag, dest_lag, freeze15)
                print(
                    f"  translate2-prehaul {lag}->{dest_lag} {st}->{newc} "
                    f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                )
                if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                    return data, False
                if st == "moved":
                    g = _plane(data["frame"])
                    cur = count_free14(data["frame"], freeze15)
                    lead = max(cur, key=lambda w: (w[0], w[1]))
                    lag = min(cur, key=lambda w: (w[0], w[1]))
                    hauled = True
                    break
            if hauled:
                break
        if not hauled:
            print("  translate2-prehaul all missed — try pair anyway")

'''
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("ok")
