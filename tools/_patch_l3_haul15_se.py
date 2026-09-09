"""Patch clear_l3 post-mid + SE-cont: haul15 direct, catch-lag first, no sync_to spam."""
from pathlib import Path

p = Path("tools/r11l_l3_sync_probe.py")
text = p.read_text(encoding="utf-8")

# Insert haul15_toward helper before clear_l3 if missing.
if "def haul15_toward(" not in text:
    marker = "def clear_l3(sess, data):"
    helper = '''def haul15_toward(sess, data, freeze14, goal15, *, max_step=8, label="haul15"):
    """Move one chrome15 wp toward goal via floor_bfs — sync_to path_ok often stuck."""
    if step_budget(data["frame"]) < 6:
        return data, False
    g = _plane(data["frame"])
    flock15 = list(freeze14)
    if not flock15:
        return data, False
    free14 = count_free14(data["frame"], freeze14)
    # Prefer western/southern wp closer to goal; avoid 14 flock.
    ordered = sorted(
        flock15,
        key=lambda w: (
            abs(w[0] - goal15[0]) + abs(w[1] - goal15[1]),
            w[0],
        ),
    )
    for wp in ordered[:2]:
        for step in (max_step, 6, 4):
            nxt = floor_bfs(g, wp, goal15, max_step=step)
            if not nxt or nxt == wp:
                # Fall back to a biased south/west step.
                nxt = (
                    wp[0] + max(-4, min(0, (goal15[0] - wp[0]) // 2)),
                    wp[1] + max(2, min(6, (goal15[1] - wp[1]) // 2)),
                )
            if not (0 <= nxt[0] < 64 and 0 <= nxt[1] < 64):
                continue
            if near_any(nxt, free14, cheb=5):
                continue
            if near_any(nxt, [c for c in flock15 if c != wp], cheb=5):
                continue
            if max(abs(nxt[0] - wp[0]), abs(nxt[1] - wp[1])) < 2:
                continue
            data, newc, st = move_wp(sess, data, wp, nxt, freeze14)
            print(
                f"  {label} {wp}->{nxt} {st}->{newc} "
                f"ship15={next(s for s in ships(data['frame']) if s['chrome']==15)['c'] if 'frame' in data else '?'} "
                f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
            )
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                return data, False
            if st == "moved":
                return data, True
            # noop: try next wp/step once
            break
    return data, False


'''
    text = text.replace(marker, helper + marker, 1)

# Replace post-mid block (sync_to spam → haul15 + one SE).
start = text.find("        # Post mid-east: same-row east noop/seals.")
end = text.find("    for turn in range(20):")
assert start > 0 and end > start, (start, end)

new_post = r'''        # Post mid-east: haul15 direct (no sync_to), then one SE dual for 14.
        if mid_ok and me14["c"][0] >= 28 and me14["c"][1] >= 34:
            freeze14 = lock_other_ship(data["frame"], 15)
            for hi in range(2):
                if step_budget(data["frame"]) < 12:
                    break
                me15b = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
                g15 = gmap[15]
                if abs(me15b["c"][0] - g15[0]) + abs(me15b["c"][1] - g15[1]) <= 10:
                    break
                before = me15b["c"]
                data, ok15 = haul15_toward(
                    sess, data, freeze14, g15, max_step=8, label="15postmid"
                )
                if data.get("state") == "GAME_OVER" or "frame" not in data:
                    raise RuntimeError("GAME_OVER 15 postmid")
                freeze14 = lock_other_ship(data["frame"], 15)
                me15a = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
                if not ok15 or me15a["c"] == before:
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
                        (lead[0] + 2, min(48, lead[1] + 6)),
                        (lead[0] + 4, min(48, lead[1] + 4)),
                        (lead[0], min(48, lead[1] + 6)),
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
                            (lag[0] + 2, min(48, lag[1] + 6)),
                            (lag[0] + 4, min(46, lag[1] + 4)),
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
text = text[:start] + new_post + text[end:]

# Replace SE-cont block through east_stalls += 1
start2 = text.find("        # 2wp already south of corridor: continue SE dual")
# Find the end: "            east_stalls += 1\n\n        on_neck"
end_marker = "            east_stalls += 1\n\n        on_neck"
end2 = text.find(end_marker, start2)
assert start2 > 0 and end2 > start2, (start2, end2)

new_se = r'''        # 2wp south of corridor: catch-lag first, then tiny SE; haul15 each turn.
        free14n = count_free14(data["frame"], freeze15)
        if (
            len(free14n) == 2
            and me14["c"][1] >= 38
            and d14 > 10
            and bud >= 8
        ):
            lead = max(free14n, key=lambda w: (w[1], w[0]))
            lag = min(free14n, key=lambda w: (w[1], w[0]))
            print(
                f"  L3 SE-cont ship={me14['c']} lead={lead} lag={lag} bud={bud}"
            )
            progressed = False

            # 1) Always catch lag in y before any further lead south.
            if lead[1] - lag[1] >= 1:
                for gd in (
                    (lag[0], min(lead[1], lag[1] + 2)),
                    (lag[0] + 2, min(lead[1], lag[1] + 2)),
                    (max(18, lag[0] - 2), min(lead[1], lag[1] + 2)),
                    (lead[0] - 5, lead[1]),
                ):
                    if not (0 <= gd[0] < 64 and 0 <= gd[1] < 64):
                        continue
                    if gd == lag:
                        continue
                    if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
                        continue
                    if near_any(gd, [lead] + list(freeze15), cheb=5):
                        continue
                    data, newc, st = move_wp(sess, data, lag, gd, freeze15)
                    print(
                        f"  SE-cont catch-lag {lag}->{gd} {st}->{newc} "
                        f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
                        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                    )
                    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                        break
                    if st == "moved":
                        freeze15 = lock_other_ship(data["frame"], 14)
                        free14n = count_free14(data["frame"], freeze15)
                        if len(free14n) == 2:
                            lag = min(free14n, key=lambda w: (w[1], w[0]))
                            lead = max(free14n, key=lambda w: (w[1], w[0]))
                            progressed = True
                            east_stalls = 0
                        break
                    # one noop only — save bud
                    break
                if data.get("state") == "GAME_OVER" or "frame" not in data:
                    break

            # 2) Lead only if lag roughly aligned (dy<=1); tiny steps only.
            if (
                not (data.get("state") == "GAME_OVER")
                and "frame" in data
                and len(count_free14(data["frame"], freeze15)) == 2
                and lead[1] - lag[1] <= 1
                and step_budget(data["frame"]) >= 8
            ):
                noops = 0
                for ld in (
                    (lead[0] + 2, lead[1]),
                    (lead[0] + 2, min(50, lead[1] + 1)),
                    (max(18, lead[0] - 2), min(50, lead[1] + 1)),
                ):
                    if not (0 <= ld[0] < 64 and 0 <= ld[1] < 64):
                        continue
                    if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
                        continue
                    if near_any(ld, list(freeze15), cheb=6):
                        continue
                    data, newc, st = move_wp(sess, data, lead, ld, freeze15)
                    print(
                        f"  SE-cont lead {lead}->{ld} {st}->{newc} "
                        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                    )
                    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                        print("  SE-cont lead dead — stop")
                        break
                    if st != "moved":
                        noops += 1
                        if noops >= 1:
                            print("  SE-cont lead noop — stop (save bud)")
                            break
                        continue
                    freeze15 = lock_other_ship(data["frame"], 14)
                    if len(count_free14(data["frame"], freeze15)) != 2:
                        print("  SE-cont flock broke")
                        break
                    progressed = True
                    east_stalls = 0
                    break
                if data.get("state") == "GAME_OVER" or "frame" not in data:
                    break

            # 3) Always try one haul15 while bud allows (even if 14 stalled).
            if (
                "frame" in data
                and data.get("state") != "GAME_OVER"
                and step_budget(data["frame"]) >= 8
                and d15 > 8
            ):
                freeze14 = lock_other_ship(data["frame"], 15)
                data, ok15 = haul15_toward(
                    sess, data, freeze14, gmap[15], max_step=8, label="haul15"
                )
                if data.get("state") == "GAME_OVER" or "frame" not in data:
                    break
                if ok15:
                    progressed = True
                    east_stalls = 0

            if progressed:
                continue
            east_stalls += 1
            # Don't fall into sync_east y34 path when already on SE band.
            if east_stalls >= 3:
                print(f"  SE-cont stalled {east_stalls} — break east scramble")
                # Still allow 15 haul below via allow15 path; skip leap14_east.
                freeze14 = lock_other_ship(data["frame"], 15)
                if step_budget(data["frame"]) >= 8 and d15 > 8:
                    data, _ = haul15_toward(
                        sess, data, freeze14, gmap[15], max_step=6, label="haul15-stall"
                    )
                    if data.get("state") == "GAME_OVER" or "frame" not in data:
                        break
                if east_stalls >= 5:
                    break
                continue

        on_neck'''

text = text[:start2] + new_se + text[end2 + len("            east_stalls += 1\n\n        on_neck"):]

# Replace interleave15-unsealed sync_to with haul15
old_unsealed = '''            if step_budget(data["frame"]) < 16 or not still_sealed:
                # Unsealed: still allow one cheap 15 hop if 14 is mid-east and 15 far.
                me14c = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
                if (
                    not still_sealed
                    and me14c["c"][0] >= 28
                    and d15 > 10
                    and step_budget(data["frame"]) >= 12
                ):
                    me15b = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
                    g15 = goals_by_chrome(data["frame"])[15]
                    hop15 = (
                        me15b["c"][0] + (g15[0] - me15b["c"][0]) // 3,
                        me15b["c"][1] + max(4, (g15[1] - me15b["c"][1]) // 3),
                    )
                    targets = [(hop15[0] + o[0], hop15[1] + o[1]) for o in OFFS15]
                    before15 = me15b["c"]
                    data, _ = sync_to(sess, data, freeze14, targets, "15unsealed")
                    if "frame" in data:
                        me15a = next(
                            s for s in ships(data["frame"]) if s["chrome"] == 15
                        )
                        print(
                            f"  interleave15-unsealed {before15}->{me15a['c']} "
                            f"bud={step_budget(data['frame'])}"
                        )
                        if me15a["c"] != before15:
                            continue
                print(
                    f"  skip wave15 thin/unsealed bud={step_budget(data['frame'])} "
                    f"d14={d14} sealed={still_sealed}"
                )
'''
new_unsealed = '''            if step_budget(data["frame"]) < 16 or not still_sealed:
                me14c = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
                if (
                    not still_sealed
                    and me14c["c"][0] >= 28
                    and d15 > 10
                    and step_budget(data["frame"]) >= 8
                ):
                    data, ok15 = haul15_toward(
                        sess, data, freeze14, gmap[15], max_step=8, label="15unsealed"
                    )
                    if data.get("state") == "GAME_OVER" or "frame" not in data:
                        break
                    if ok15:
                        continue
                print(
                    f"  skip wave15 thin/unsealed bud={step_budget(data['frame'])} "
                    f"d14={d14} sealed={still_sealed}"
                )
'''
if old_unsealed not in text:
    # softer match
    if "interleave15-unsealed" in text:
        print("WARN: unsealed block format changed; haul15 helper still added")
    else:
        print("WARN: no unsealed block found")
else:
    text = text.replace(old_unsealed, new_unsealed, 1)

p.write_text(text, encoding="utf-8")
print("patched haul15 + SE-cont")
