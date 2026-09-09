"""Fix haul15 flock selection + SE-cont try west-south after noop."""
from pathlib import Path

p = Path("tools/r11l_l3_sync_probe.py")
text = p.read_text(encoding="utf-8")

old_h = text.find("def haul15_toward(")
old_e = text.find("def clear_l3(sess, data):")
assert old_h > 0 and old_e > old_h

new_h = '''def haul15_toward(sess, data, goal15, *, max_step=8, label="haul15", _freeze14_unused=None):
    """Move one chrome15 wp toward goal. Resolves flocks itself (never touch 14)."""
    if step_budget(data["frame"]) < 6:
        return data, False
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    # freeze14 = wps to not touch while moving 15
    freeze14 = lock_other_ship(data["frame"], 15)
    # flock15 = wps belonging to 15 (frozen when moving 14)
    flock15 = [
        c
        for c in lock_other_ship(data["frame"], 14)
        if manh(c, me15["c"]) <= manh(c, me14["c"]) + 4
    ]
    if len(flock15) < 1:
        # Fallback: wps nearer to 15 than 14
        flock15 = [
            w["c"]
            for w in r11l.waypoints(data["frame"])
            if manh(w["c"], me15["c"]) + 2 < manh(w["c"], me14["c"])
        ]
    if not flock15:
        print(f"  {label} no chrome15 flock")
        return data, False
    g = _plane(data["frame"])
    ordered = sorted(
        flock15,
        key=lambda w: (abs(w[0] - goal15[0]) + abs(w[1] - goal15[1]), w[0]),
    )
    print(f"  {label} flock15={ordered[:3]} goal={goal15}")
    for wp in ordered[:2]:
        cands = []
        nxt = floor_bfs(g, wp, goal15, max_step=max_step)
        if nxt and nxt != wp:
            cands.append(nxt)
        # Explicit south/west steps toward goal (34,57)
        for dx, dy in (
            (0, 6),
            (0, 4),
            (-4, 4),
            (-6, 2),
            (-4, 6),
            (0, 8),
            (-2, 4),
        ):
            cands.append((wp[0] + dx, min(60, wp[1] + dy)))
        seen = set()
        for nxt in cands:
            if nxt in seen or nxt == wp:
                continue
            seen.add(nxt)
            if not (0 <= nxt[0] < 64 and 0 <= nxt[1] < 64):
                continue
            if near_any(nxt, freeze14, cheb=5):
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
            # noop: try next candidate once for this wp, then next wp
            break
    return data, False


'''
text = text[:old_h] + new_h + text[old_e:]

# Fix call sites: haul15_toward(sess, data, freeze14, g15, ...) -> haul15_toward(sess, data, g15, ...)
import re
text2 = re.sub(
    r"haul15_toward\(\s*sess,\s*data,\s*freeze14,\s*g15,",
    "haul15_toward(sess, data, g15,",
    text,
)
text2 = re.sub(
    r"haul15_toward\(\s*sess,\s*data,\s*freeze14,\s*gmap\[15\],",
    "haul15_toward(sess, data, gmap[15],",
    text2,
)
text = text2

# SE-cont: try west-south first; allow 2 noops before stop
old_lead = '''            noops = 0
            for ld in (
                (lead[0] + 2, lead[1]),
                (lead[0] + 2, min(50, lead[1] + 1)),
                (max(18, lead[0] - 2), min(50, lead[1] + 1)),
            ):
'''
new_lead = '''            noops = 0
            # Prefer west-south (away from 15 seal ~x41) then tiny east.
            for ld in (
                (max(18, lead[0] - 3), min(48, lead[1] + 2)),
                (max(18, lead[0] - 2), min(48, lead[1] + 2)),
                (lead[0] + 2, lead[1]),
                (lead[0] + 2, min(48, lead[1] + 1)),
            ):
'''
if old_lead not in text:
    raise SystemExit("SE lead dests block not found")
text = text.replace(old_lead, new_lead, 1)

old_noop = '''                if st != "moved":
                    noops += 1
                    if noops >= 1:
                        print("  SE-cont lead noop — stop (save bud)")
                        break
                    continue
'''
new_noop = '''                if st != "moved":
                    noops += 1
                    if noops >= 2:
                        print("  SE-cont lead 2x noop — stop (save bud)")
                        break
                    continue
'''
if old_noop not in text:
    raise SystemExit("noop block not found")
text = text.replace(old_noop, new_noop, 1)

p.write_text(text, encoding="utf-8")
print("fixed haul15 flocks + SE dests")
