from pathlib import Path

p = Path("tools/r11l_l3_sync_probe.py")
text = p.read_text(encoding="utf-8")
start = text.find("        # Post mid-east: NEVER lead+5")
end = text.find("    for turn in range(20):")
assert start > 0 and end > start, (start, end)

new = r'''        # Post mid-east: same-row east noop/seals. Push 15 south, then one 14 SE hop.
        if mid_ok and me14["c"][0] >= 28 and me14["c"][1] >= 34:
            for _ in range(3):
                if step_budget(data["frame"]) < 14:
                    break
                freeze14 = lock_other_ship(data["frame"], 15)
                me15b = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
                g15 = gmap[15]
                d15n = abs(me15b["c"][0] - g15[0]) + abs(me15b["c"][1] - g15[1])
                if d15n <= 10:
                    break
                hop15 = (
                    me15b["c"][0] + max(-4, min(4, (g15[0] - me15b["c"][0]) // 2)),
                    me15b["c"][1] + max(4, min(10, (g15[1] - me15b["c"][1]) // 2)),
                )
                targets = [(hop15[0] + o[0], hop15[1] + o[1]) for o in OFFS15]
                before15 = me15b["c"]
                data, _ = sync_to(sess, data, freeze14, targets, "15postmid")
                if data.get("state") == "GAME_OVER" or "frame" not in data:
                    raise RuntimeError("GAME_OVER 15 postmid")
                me15a = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
                print(
                    f"  interleave15-postmid {before15}->{me15a['c']} "
                    f"bud={step_budget(data['frame'])}"
                )
                if me15a["c"] == before15:
                    break

            if step_budget(data["frame"]) >= 10:
                freeze15 = lock_other_ship(data["frame"], 14)
                free14 = count_free14(data["frame"], freeze15)
                if len(free14) == 2:
                    lead = max(free14, key=lambda w: (w[0], w[1]))
                    lag = min(free14, key=lambda w: (w[0], w[1]))
                    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
                    print(
                        f"--- L3 post-mid SE ship={me14['c']} lead={lead} lag={lag} "
                        f"bud={step_budget(data['frame'])} ---"
                    )
                    for ld in (
                        (lead[0] + 2, min(50, lead[1] + 6)),
                        (lead[0] + 4, min(50, lead[1] + 4)),
                        (lead[0], min(50, lead[1] + 6)),
                        (lead[0] + 3, min(48, lead[1] + 3)),
                    ):
                        if ld[1] < 34 or ld[0] >= 64:
                            continue
                        if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
                            continue
                        if near_any(ld, list(freeze15), cheb=5):
                            continue
                        data, newc, st = move_wp(sess, data, lead, ld, freeze15)
                        print(
                            f"  post-mid SE-lead {lead}->{ld} {st}->{newc} "
                            f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
                            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
                            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                        )
                        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                            raise RuntimeError("GAME_OVER post-mid SE")
                        if st != "moved":
                            continue
                        freeze15 = lock_other_ship(data["frame"], 14)
                        if len(count_free14(data["frame"], freeze15)) != 2:
                            print("  post-mid SE flock broke")
                            break
                        free14 = count_free14(data["frame"], freeze15)
                        lag = min(free14, key=lambda w: (w[0], w[1]))
                        lead = max(free14, key=lambda w: (w[0], w[1]))
                        for gd in (
                            (lag[0] + 2, min(50, lag[1] + 6)),
                            (lag[0] + 4, min(48, lag[1] + 4)),
                            (lead[0] - 6, lead[1]),
                        ):
                            if gd[1] < 34:
                                continue
                            if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
                                continue
                            if near_any(gd, [lead] + list(freeze15), cheb=5):
                                continue
                            data, newc, st = move_wp(sess, data, lag, gd, freeze15)
                            print(
                                f"  post-mid SE-lag {lag}->{gd} {st}->{newc} "
                                f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
                                f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
                                f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                            )
                            break
                        break
            me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            print(
                f"  L3 post-mid done ship={me14['c']} "
                f"bud={step_budget(data['frame'])}"
            )

'''

p.write_text(text[:start] + new + text[end:], encoding="utf-8")
print("patched post-mid SE")
