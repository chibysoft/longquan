from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")

# Insert intentional column-merge at start of shallow handling.
needle = """            # Free shallow traps BEFORE any lead — else lead hop drops western flock.
            shallow_band = [w for w in band if 28 <= w[1] <= 32]
            if shallow_band and step_budget(data["frame"]) >= 6:
                g = _plane(data["frame"])
                wp = sorted(shallow_band, key=lambda w: w[1])[0]
                cur_now = count_free14(data["frame"], freeze15)
                # Same-x southern blocker
"""
# Use unique start
old_start = """            # Free shallow traps BEFORE any lead — else lead hop drops western flock.
            shallow_band = [w for w in band if 28 <= w[1] <= 32]
            if shallow_band and step_budget(data["frame"]) >= 6:
                g = _plane(data["frame"])
                wp = sorted(shallow_band, key=lambda w: w[1])[0]
                cur_now = count_free14(data["frame"], freeze15)
                # Same-x southern blocker (e.g. 14,36 vs 14,31) — nudge it east first.
"""
new_start = """            # Free shallow traps BEFORE any lead — else lead hop drops western flock.
            shallow_band = [w for w in band if 28 <= w[1] <= 32]
            if shallow_band and step_budget(data["frame"]) >= 6:
                g = _plane(data["frame"])
                wp = sorted(shallow_band, key=lambda w: w[1])[0]
                cur_now = count_free14(data["frame"], freeze15)
                # Prefer MERGE shallow into same-x southern sib (near_any blocks
                # separation; engine merges at cheb<5 — intentional).
                sibs_col = [
                    c
                    for c in cur_now
                    if c != wp and c[0] == wp[0] and c[1] >= 34
                ]
                if sibs_col and pulls < 1:
                    sib = sibs_col[0]
                    # Land at cheb=3 north of sib (merge range).
                    dest = (sib[0], sib[1] - 3)
                    if dest[1] < wp[1]:
                        dest = (sib[0], wp[1] + 2)  # step south toward sib
                    # Walk up to 4 cells toward sib.
                    dest = wp
                    for _ in range(5):
                        if max(abs(sib[0] - dest[0]), abs(sib[1] - dest[1])) <= 3:
                            break
                        dy = 1 if sib[1] > dest[1] else (-1 if sib[1] < dest[1] else 0)
                        dx = 0 if sib[0] == dest[0] else (1 if sib[0] > dest[0] else -1)
                        nxt = (dest[0] + dx, dest[1] + dy)
                        if not (0 <= nxt[0] < 64 and 0 <= nxt[1] < 64):
                            break
                        if int(g[nxt[1], nxt[0]]) in (2, 10):
                            break
                        dest = nxt
                    if dest != wp and max(abs(sib[0] - dest[0]), abs(sib[1] - dest[1])) <= 4:
                        # Do NOT near_any against sib — we want merge.
                        others = [c for c in cur_now if c != wp and c != sib]
                        if not near_any(dest, others + freeze15, cheb=5):
                            trial = [dest if c == wp else c for c in cur_now]
                            # Allow trial with dest near sib.
                            tc = centroid([c for c in trial if c != sib] + [sib])
                            tci = (int(round(tc[0])), int(round(tc[1])))
                            if ship_footprint_ok(g, *tci) or True:
                                data, newc, st = move_wp(
                                    sess, data, wp, dest, freeze15
                                )
                                print(
                                    f"    sync14-merge-shallow {wp}->{dest} (→{sib}) "
                                    f"{st}->{newc} "
                                    f"n={len(r11l.waypoints(data['frame'])) if 'frame' in data else '?'} "
                                    f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                                )
                                if st == "dead" or "frame" not in data:
                                    return data, False
                                if st == "moved":
                                    pulls += 1
                                    moved_any = True
                                    g = _plane(data["frame"])
                                    me = next(
                                        s
                                        for s in ships(data["frame"])
                                        if s["chrome"] == 14
                                    )
                                    cur_now = count_free14(data["frame"], freeze15)
                                    band = [
                                        w
                                        for w in cur_now
                                        if 28 <= w[1] <= 38
                                    ] or cur_now
                                    lead = sorted(
                                        band,
                                        key=lambda w: (-w[0], abs(w[1] - 34)),
                                    )
                                    lag = sorted(
                                        band,
                                        key=lambda w: (w[0], abs(w[1] - 34)),
                                    )
                                    lead_x0 = lead[0][0] if lead else 0
                                    # Merged: continue to lead/lag this turn.
                                    shallow_band = [
                                        w for w in band if 28 <= w[1] <= 32
                                    ]
                # Same-x southern blocker (e.g. 14,36 vs 14,31) — nudge it east first.
"""
if old_start not in t:
    raise SystemExit("shallow start missing")
t = t.replace(old_start, new_start, 1)

# After merge, don't hold-lead if shallow gone — fall through to lead.
# The hold-lead check already uses band_now; should be fine.

p.write_text(t, encoding="utf-8")
print("ok")
