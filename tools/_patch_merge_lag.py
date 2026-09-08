from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")

# Before lead/lag pulls when stacked and not post_seal: if 2 western
# wps are within merge range of a short walk, merge them to unlock 2wp strides.
old = """        else:
            # Free same-x shallow traps before lead (otherwise footprint rejects all east).
            shallow_band = [w for w in band if 28 <= w[1] <= 32]
"""
new = """        else:
            # Twin western lags at cheb<=6 block each other's east hops (noop).
            # Merge the west-most into its sibling to leave lead+1 lag (2wp mode).
            west_lags = [w for w in lag if w[0] < lead_x0 - 4]
            if len(west_lags) >= 2 and pulls < 1 and step_budget(data["frame"]) >= 10:
                a, b = sorted(west_lags, key=lambda w: w[0])[:2]
                cheb_ab = max(abs(a[0] - b[0]), abs(a[1] - b[1]))
                if 3 <= cheb_ab <= 8:
                    g = _plane(data["frame"])
                    # Step a toward b until cheb<=3 (engine merges at <5).
                    dest = a
                    for _ in range(6):
                        dx = 0 if b[0] == dest[0] else (1 if b[0] > dest[0] else -1)
                        dy = 0 if b[1] == dest[1] else (1 if b[1] > dest[1] else -1)
                        nxt = (dest[0] + dx, dest[1] + dy)
                        if max(abs(b[0] - nxt[0]), abs(b[1] - nxt[1])) < 3:
                            break
                        if not (0 <= nxt[0] < 64 and 0 <= nxt[1] < 64):
                            break
                        if int(g[nxt[1], nxt[0]]) in (2, 10):
                            break
                        dest = nxt
                        if max(abs(b[0] - dest[0]), abs(b[1] - dest[1])) <= 3:
                            break
                    if dest != a:
                        data, newc, st = move_wp(sess, data, a, dest, freeze15)
                        print(
                            f"    sync14-merge-lag {a}->{dest} (→{b}) {st}->{newc} "
                            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                        )
                        if st == "dead" or "frame" not in data:
                            return data, False
                        if st == "moved":
                            pulls += 1
                            moved_any = True
                            g = _plane(data["frame"])
                            me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
                            cur = count_free14(data["frame"], freeze15)
                            band = [w for w in cur if 28 <= w[1] <= 38] or cur
                            lead = sorted(band, key=lambda w: (-w[0], abs(w[1] - 34)))
                            lag = sorted(band, key=lambda w: (w[0], abs(w[1] - 34)))
                            lead_x0 = lead[0][0] if lead else 0
            # Free same-x shallow traps before lead (otherwise footprint rejects all east).
            shallow_band = [w for w in band if 28 <= w[1] <= 32]
"""
if old not in t:
    raise SystemExit("merge insert point missing")
t = t.replace(old, new, 1)

# Disable useless interleave15 that just path_ok-fails.
old3 = """                    elif (
                        lead_x >= 28
                        and not sealed
                        and step_budget(data["frame"]) >= 16
                        and d15 > 8
                    ):
"""
new3 = """                    elif False and (
                        lead_x >= 28
                        and not sealed
                        and step_budget(data["frame"]) >= 16
                        and d15 > 8
                    ):
"""
if old3 not in t:
    print("interleave guard missing (ok if already)")
else:
    t = t.replace(old3, new3, 1)
    print("interleave disabled")

p.write_text(t, encoding="utf-8")
print("merge-lag patched")
