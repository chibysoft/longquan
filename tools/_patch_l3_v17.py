from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")

# After successful lift-shallow, return immediately (don't lead same turn).
old = """                        print(
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
"""
new = """                        print(
                            f"    sync14-lift-shallow {wp}->{dest} {st}->{newc} "
                            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                        )
                        if st == "dead" or "frame" not in data:
                            return data, False
                        if st == "moved":
                            pulls += 1
                            moved_any = True
                            # Stop this sync — lead same turn dropped mid wp on live.
                            after = next(
                                s for s in ships(data["frame"]) if s["chrome"] == 14
                            )["c"]
                            print(
                                f"  sync_east14 post-lift stop ship={after} "
                                f"bud={step_budget(data['frame'])}"
                            )
                            return data, True
                        break
"""
if old not in t:
    raise SystemExit("lift-shallow block missing")
t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")
print("ok")
