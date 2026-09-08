from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")

# Replace hold-lead shallow block with: move blocking sib east, then lift shallow.
old = """            # Free shallow traps BEFORE any lead — else lead hop drops western flock.
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
"""

new = """            # Free shallow traps BEFORE any lead — else lead hop drops western flock.
            shallow_band = [w for w in band if 28 <= w[1] <= 32]
            if shallow_band and step_budget(data["frame"]) >= 6:
                g = _plane(data["frame"])
                wp = sorted(shallow_band, key=lambda w: w[1])[0]
                cur_now = count_free14(data["frame"], freeze15)
                # Same-x southern blocker (e.g. 14,36 vs 14,31) — nudge it east first.
                blockers = [
                    c
                    for c in cur_now
                    if c != wp and c[0] == wp[0] and c[1] >= 34
                ]
                if blockers and pulls < 1:
                    blk = blockers[0]
                    others_b = [c for c in cur_now if c != blk]
                    for dest in (
                        (blk[0] + 6, blk[1]),
                        (blk[0] + 5, 34),
                        (blk[0] + 4, 36),
                        (blk[0] + 8, 34),
                    ):
                        if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
                            continue
                        if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
                            continue
                        if near_any(dest, others_b + freeze15, cheb=5):
                            continue
                        trial = [dest if c == blk else c for c in cur_now]
                        tc = centroid(trial)
                        tci = (int(round(tc[0])), int(round(tc[1])))
                        if not ship_footprint_ok(g, *tci):
                            continue
                        data, newc, st = move_wp(sess, data, blk, dest, freeze15)
                        print(
                            f"    sync14-clear-blocker {blk}->{dest} {st}->{newc} "
                            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                        )
                        if st == "dead" or "frame" not in data:
                            return data, False
                        if st == "moved":
                            pulls += 1
                            moved_any = True
                            g = _plane(data["frame"])
                            me = next(
                                s for s in ships(data["frame"]) if s["chrome"] == 14
                            )
                            cur_now = count_free14(data["frame"], freeze15)
                            band = [w for w in cur_now if 28 <= w[1] <= 38] or cur_now
                        break
                # Refresh shallow after blocker move.
                shallow_band = [w for w in band if 28 <= w[1] <= 32]
                if not shallow_band:
                    shallow_band = [w for w in cur_now if 28 <= w[1] <= 32]
                if shallow_band and pulls < 2:
                    wp = sorted(shallow_band, key=lambda w: w[1])[0]
                    others = [c for c in cur_now if c != wp]
                    for dest in (
                        (wp[0] + 6, 34),
                        (wp[0] + 8, 34),
                        (wp[0] + 6, 36),
                        (wp[0] + 4, 36),
                        (wp[0], 36),
                        (wp[0] + 2, 34),
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
                            g = _plane(data["frame"])
                            me = next(
                                s for s in ships(data["frame"]) if s["chrome"] == 14
                            )
                            cur = count_free14(data["frame"], freeze15)
                            band = [w for w in cur if 28 <= w[1] <= 38] or cur
                            lead = sorted(
                                band, key=lambda w: (-w[0], abs(w[1] - 34))
                            )
                            lag = sorted(
                                band, key=lambda w: (w[0], abs(w[1] - 34))
                            )
                            lead_x0 = lead[0][0] if lead else 0
                        break
                # Still shallow? Hold lead this turn (no force_east either).
                band_now = [
                    w
                    for w in count_free14(data["frame"], freeze15)
                    if 28 <= w[1] <= 38
                ]
                if any(28 <= w[1] <= 32 for w in band_now):
                    print(
                        f"  sync_east14 hold-lead shallow ship={me['c']} "
                        f"bud={step_budget(data['frame'])}"
                    )
                    after = next(
                        s for s in ships(data["frame"]) if s["chrome"] == 14
                    )["c"]
                    return data, after != before or pulls > 0 or moved_any
"""

if old not in t:
    raise SystemExit("hold-lead block missing")
t = t.replace(old, new, 1)

# Disable force_east when any shallow remains.
old_f = """        data, forced = force_east_step(sess, data, freeze15)
        if forced:
            me2 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            print(
                f"  east14 force-first ship={me2['c']} "
                f"bud={step_budget(data['frame'])}"
            )
            return data, True
"""
new_f = """        flock_f = count_free14(data["frame"], freeze15)
        if any(28 <= w[1] <= 32 for w in flock_f):
            print(
                f"  east14 skip-force shallow={ [w for w in flock_f if 28<=w[1]<=32] } "
                f"bud={step_budget(data['frame'])}"
            )
            return data, False
        data, forced = force_east_step(sess, data, freeze15)
        if forced:
            me2 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            print(
                f"  east14 force-first ship={me2['c']} "
                f"bud={step_budget(data['frame'])}"
            )
            return data, True
"""
if old_f not in t:
    raise SystemExit("force_east block missing")
t = t.replace(old_f, new_f, 1)

p.write_text(t, encoding="utf-8")
print("ok")
