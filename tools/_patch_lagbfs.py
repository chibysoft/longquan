from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")

# After noop on lag, stop trying more lags (each noop burns ~3).
old = """            if noop_hit and pulls == 0 and label == "-lead":
                break
        return True
"""
new = """            if noop_hit and pulls == 0 and label == "-lead":
                break
            # Lag noops burn budget with zero progress — stop the haul.
            if noop_hit and label == "-lag":
                break
        return True
"""
if old not in t:
    raise SystemExit("noop break missing")
t = t.replace(old, new, 1)

# Prefer lag haul via floor_bfs toward a pad just west of lead.
old2 = """        if post_seal:
            # Lead already past seal — only haul western lag; never retouch lead.
            if me["c"][1] >= 33:
                lag2 = [w for w in lag if w[0] < lead_x0 - 2][:3]
                if lag2:
                    if not _try_pull(lag2, "-lag"):
                        return data, False
"""
new2 = """        if post_seal:
            # Lead already past seal — only haul western lag; never retouch lead.
            if me["c"][1] >= 33:
                lag2 = [w for w in lag if w[0] < lead_x0 - 2][:2]
                if lag2:
                    # One BFS step toward a pad west of lead — avoids noop spam.
                    g = _plane(data["frame"])
                    hauled = False
                    for wp in lag2:
                        if step_budget(data["frame"]) < 6 or pulls >= 2:
                            break
                        cur_now = count_free14(data["frame"], freeze15)
                        if wp not in cur_now:
                            continue
                        others = [c for c in cur_now if c != wp]
                        for pad in (
                            (lead_x0 - 6, 34),
                            (lead_x0 - 8, 34),
                            (lead_x0 - 6, 36),
                            (wp[0] + 6, 34),
                            (wp[0] + 5, 34),
                        ):
                            if pad[0] <= wp[0]:
                                continue
                            if near_any(pad, others + freeze15, cheb=5):
                                continue
                            nxt = floor_bfs(g, wp, pad, max_step=6)
                            if not nxt or nxt == wp:
                                continue
                            if near_any(nxt, others + freeze15, cheb=5):
                                continue
                            trial = [nxt if c == wp else c for c in cur_now]
                            tc = centroid(trial)
                            tci = (int(round(tc[0])), int(round(tc[1])))
                            if not ship_footprint_ok(g, *tci):
                                continue
                            data, newc, st = move_wp(sess, data, wp, nxt, freeze15)
                            print(
                                f"    sync14-lagbfs {wp}->{nxt} (pad{pad}) {st}->{newc} "
                                f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                            )
                            if st == "dead" or "frame" not in data:
                                return data, False
                            if st == "moved":
                                pulls += 1
                                moved_any = True
                                hauled = True
                                g = _plane(data["frame"])
                                break
                            # noop: stop — further tries burn bud
                            break
                        if hauled:
                            break
                    if not hauled and lag2:
                        if not _try_pull(lag2[:1], "-lag"):
                            return data, False
"""
if old2 not in t:
    raise SystemExit("post_seal block missing")
t = t.replace(old2, new2, 1)
p.write_text(t, encoding="utf-8")
print("lagbfs patched")
