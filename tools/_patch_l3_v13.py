from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")

# 1) Always compact shallow even if lead exists — (14,31) left behind caused 4→2.
old = """    if step_budget(data["frame"]) < 12 or lead0 >= 28:
        shallow = []
"""
new = """    # Compact shallow even with a lead — leaving (14,31) then lead-hop drops flock.
    if step_budget(data["frame"]) < 10:
        shallow = []
"""
if old not in t:
    raise SystemExit("shallow skip missing")
t = t.replace(old, new, 1)

# 2) Before lead: if shallow remains, haul shallow south only (no lead).
old2 = """            # Free same-x shallow traps before lead (otherwise footprint rejects all east).
            shallow_band = [w for w in band if 28 <= w[1] <= 32]
            if shallow_band and pulls < 1:
                sibs = [
                    w
                    for w in lag
                    if w[1] >= 34
                    and any(s[0] == w[0] for s in shallow_band)
                ]
                if sibs:
                    if not _try_pull(sibs[:1], "-sib"):
                        return data, False
            # 2wp with lead far ahead: haul lag first — lone lead hop GAME_OVER'd.
"""
new2 = """            # Free shallow traps BEFORE any lead — else lead hop drops western flock.
            shallow_band = [w for w in band if 28 <= w[1] <= 32]
            if shallow_band and step_budget(data["frame"]) >= 6:
                g = _plane(data["frame"])
                wp = sorted(shallow_band, key=lambda w: w[1])[0]
                cur_now = count_free14(data["frame"], freeze15)
                others = [c for c in cur_now if c != wp]
                lifted = False
                for dest in (
                    (wp[0], 36),
                    (wp[0], 34),
                    (wp[0] + 4, 34),
                    (wp[0] + 6, 34),
                    (wp[0] - 2, 36),
                ):
                    if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
                        continue
                    if dest[1] < 33 or dest == wp:
                        continue
                    if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
                        continue
                    if near_any(dest, others + freeze15, cheb=5):
                        continue
                    trial = [dest if c == wp else c for c in cur_now]
                    tc = centroid(trial)
                    tci = (int(round(tc[0])), int(round(tc[1])))
                    if not ship_footprint_ok(g, *tci):
                        continue
                    data, newc, st = move_wp(sess, data, wp, dest, freeze15)
                    print(
                        f"    sync14-lift-shallow {wp}->{dest} {st}->{newc} "
                        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                    )
                    if st == "dead" or "frame" not in data:
                        return data, False
                    if st == "moved":
                        pulls += 1
                        moved_any = True
                        lifted = True
                        g = _plane(data["frame"])
                        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
                        cur = count_free14(data["frame"], freeze15)
                        band = [w for w in cur if 28 <= w[1] <= 38] or cur
                        lead = sorted(band, key=lambda w: (-w[0], abs(w[1] - 34)))
                        lag = sorted(band, key=lambda w: (w[0], abs(w[1] - 34)))
                        lead_x0 = lead[0][0] if lead else 0
                    break
                # Do not lead this turn if shallow still present.
                if lifted or any(28 <= w[1] <= 32 for w in band):
                    print(
                        f"  sync_east14 hold-lead shallow ship={me['c']} "
                        f"bud={step_budget(data['frame'])}"
                    )
                    after = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"]
                    return data, after != before or pulls > 0 or moved_any
            # 2wp with lead far ahead: haul lag first — lone lead hop GAME_OVER'd.
"""
if old2 not in t:
    raise SystemExit("shallow_band block missing")
t = t.replace(old2, new2, 1)

p.write_text(t, encoding="utf-8")
print("ok")
