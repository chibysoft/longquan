"""Harden 2wp probe: no wrap-column lag; lag-haul abort; no shallow landings."""
from pathlib import Path

p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")

# --- 1) Prefer keepers with x>=20 so merges don't land on wrap column ---
old_keepers = '''    # Prefer easternmost + a second with cheb>=5 (avoid same-column keepers).
    east = max(corridor, key=lambda w: (w[0], w[1]))
    rest = sorted(
        [w for w in corridor if w != east],
        key=lambda w: (
            0 if max(abs(w[0] - east[0]), abs(w[1] - east[1])) >= 5 else 1,
            -w[0],
            -w[1],
        ),
    )
    keepers = [east] + rest[:1]
'''
new_keepers = '''    # Prefer easternmost + a second with cheb>=5 and x>=20 (avoid wrap lag).
    east = max(corridor, key=lambda w: (w[0], w[1]))
    rest = sorted(
        [w for w in corridor if w != east],
        key=lambda w: (
            0 if w[0] >= 20 else 1,
            0 if max(abs(w[0] - east[0]), abs(w[1] - east[1])) >= 5 else 1,
            -w[0],
            -w[1],
        ),
    )
    keepers = [east] + rest[:1]
'''
if old_keepers not in t:
    raise SystemExit("keepers block not found")
t = t.replace(old_keepers, new_keepers, 1)

# --- 2) Replace translate2 lag-haul + pair move to be strict ---
start = t.index('def translate2(sess, data, freeze15, dx: int, dy: int = 0):')
# find next def at same level after translate2 body — success_gate or west_to_neck
end = t.index('\ndef west_to_neck(')
# Actually translate2 may be followed by success_gate
for marker in ('\ndef success_gate(', '\ndef west_to_neck('):
    if marker in t[start:]:
        end = start + t[start:].index(marker)
        break

new_translate = '''def translate2(sess, data, freeze15, dx: int, dy: int = 0):
    """Pair move. If lag trails by >8, haul lag only (no lead-only race)."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    if len(cur) != 2:
        print(f"  translate2 need exactly 2, got {cur}")
        return data, False
    if me["c"][1] < 34 or any(w[1] < 34 for w in cur):
        print(f"  translate2 refuse shallow ship={me['c']} cur={cur}")
        return data, False
    if not (4 <= dx <= 10):
        print(f"  translate2 dx out of range {dx}")
        return data, False

    g = _plane(data["frame"])
    lead = max(cur, key=lambda w: (w[0], w[1]))
    lag = min(cur, key=lambda w: (w[0], w[1]))
    gap = lead[0] - lag[0]
    if gap > 8:
        print(f"  translate2 lag-haul gap={gap} lead={lead} lag={lag}")
        # Close gap to 5..8 on y>=34. Direct pad only; abort on first noop.
        pads = []
        for px in (
            lead[0] - 6,
            lead[0] - 5,
            lead[0] - 8,
            lag[0] + 6,
            lag[0] + 8,
            max(lag[0] + 5, 20),
            20,
            22,
            24,
        ):
            for py in (lead[1], 36, 34):
                pads.append((px, py))
        cur_now = count_free14(data["frame"], freeze15)
        others = [c for c in cur_now if c != lag]
        tries = 0
        for pad in pads:
            if tries >= 4:
                break
            if pad[0] <= max(lag[0], 16) or pad[1] < 34:
                continue
            cheb_l = max(abs(pad[0] - lead[0]), abs(pad[1] - lead[1]))
            if cheb_l < 5 or cheb_l > 8:
                continue
            if near_any(pad, others + freeze15, cheb=5):
                continue
            trial = [pad if c == lag else c for c in cur_now]
            tc = centroid(trial)
            tci = (int(round(tc[0])), int(round(tc[1])))
            if not ship_footprint_ok(g, *tci):
                continue
            tries += 1
            data, newc, st = move_wp(sess, data, lag, pad, freeze15)
            print(
                f"  translate2-lag {lag}->{pad} {st}->{newc} "
                f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
                f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
            )
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                return data, False
            if st == "moved":
                # Reject accidental shallow landing.
                cur2 = count_free14(data["frame"], freeze15)
                if any(w[1] < 34 for w in cur2):
                    print(f"  translate2-lag landed shallow {cur2} — stop")
                    return data, False
                return data, True
            print("  translate2 lag-haul noop — abort (save bud)")
            return data, False
        print("  translate2 lag-haul all pads failed")
        return data, False

    ordered = [lag, lead]
    for wp in ordered:
        cur_now = count_free14(data["frame"], freeze15)
        if wp not in cur_now:
            continue
        others = [c for c in cur_now if c != wp]
        dest = (wp[0] + dx, wp[1] + dy)
        if dest[1] < 34 or not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
            print(f"  translate2 bad dest {dest}")
            return data, False
        # Prefer exact dest; never BFS into y<34.
        if near_any(dest, others + freeze15, cheb=5):
            alt = None
            for ady in (0, 2, -2, 1, -1):
                tpad = (wp[0] + dx, min(38, max(34, wp[1] + ady)))
                if tpad == wp or not (0 <= tpad[0] < 64):
                    continue
                if near_any(tpad, others + freeze15, cheb=5):
                    continue
                alt = tpad
                break
            if alt is None:
                print(f"  translate2 near sibling/lock {dest}")
                return data, False
            dest = alt
        if dest[1] < 34:
            print(f"  translate2 refuse shallow dest {dest}")
            return data, False
        trial = [dest if c == wp else c for c in cur_now]
        tc = centroid(trial)
        tci = (int(round(tc[0])), int(round(tc[1])))
        if not ship_footprint_ok(g, *tci):
            print(f"  translate2 footprint fail {tci}")
            return data, False
        if not centroid_path_ok(cur_now, trial, g, samples=12):
            print(f"  translate2 path_ok fail {wp}->{dest}")
            return data, False
        data, newc, st = move_wp(sess, data, wp, dest, freeze15)
        print(
            f"  translate2 {wp}->{dest} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            print(f"  translate2 noop — abort")
            return data, False
        g = _plane(data["frame"])
    return data, True

'''
t = t[:start] + new_translate + t[end:]
p.write_text(t, encoding="utf-8")
print("ok", p)
