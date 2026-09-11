"""Full deep15 (E5842+W4250+E5854) then goal-west / x<=52 south chains (no x60)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, lock_other_ship, near_any
from tools.r11l_seated_clear import clear_l1, reset

GOAL14 = (55, 53)
GOAL15 = (34, 57)


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
    d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
    print(
        f"{label} ship14={me14['c']} d14={d14} free={sorted(free)} "
        f"d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, free, fr15


def deep15(sess, data):
    """E5842 → W4250 → E5854 (same order as se-ny stack)."""
    freeze14 = lock_other_ship(data["frame"], 15)
    flock15 = list(lock_other_ship(data["frame"], 14))
    if not flock15:
        return data, False
    west15 = min(flock15, key=lambda w: w[0])
    east15 = max(flock15, key=lambda w: w[0])
    if east15[0] < 56:
        for tgt in ((58, 42), (56, 44), (58, 40)):
            if cheb(tgt, west15) < 5 or near_any(tgt, list(freeze14), cheb=5):
                continue
            data, newc, st = move_wp(sess, data, east15, tgt, freeze14)
            print(f"  E {east15}->{tgt} {st}->{newc}", flush=True)
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                return data, False
            if st == "moved":
                freeze14 = lock_other_ship(data["frame"], 15)
                flock15 = list(lock_other_ship(data["frame"], 14))
                west15 = min(flock15, key=lambda w: w[0])
                east15 = max(flock15, key=lambda w: w[0])
                break
    moved_w = False
    for tgt in ((42, 50), (48, 42), (46, 42), (50, 42)):
        if cheb(tgt, east15) < 5 or near_any(tgt, list(freeze14), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, west15, tgt, freeze14)
        print(f"  W {west15}->{tgt} {st}->{newc}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st == "moved":
            moved_w = True
            freeze14 = lock_other_ship(data["frame"], 15)
            flock15 = list(lock_other_ship(data["frame"], 14))
            west15 = min(flock15, key=lambda w: w[0])
            east15 = max(flock15, key=lambda w: w[0])
            break
    if not moved_w:
        print("  W fail", flush=True)
        return data, False
    if east15[1] < 52 and step_budget(data["frame"]) >= 6:
        for tgt in ((58, 54), (62, 52), (56, 54), (58, 50)):
            if cheb(tgt, west15) < 5 or near_any(tgt, list(freeze14), cheb=5):
                continue
            data, newc, st = move_wp(sess, data, east15, tgt, freeze14)
            print(f"  Eb {east15}->{tgt} {st}->{newc}", flush=True)
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                return data, False
            if st == "moved":
                break
    dump(data, "deep15")
    return data, True


def boot():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_d15gw"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    lv0 = data.get("levels_completed") or 0
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
    data, ok = deep15(sess, data)
    return sess, data, ok


def step(sess, data, who, tgt):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return data, "nfree"
    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    cur = {"R": lead, "L": lag, "N": north, "S": south}[who]
    other = next(w for w in free if w != cur)
    if cheb(tgt, other) < 5:
        return data, "merge"
    if near_any(tgt, list(fr15), cheb=5):
        return data, "near15"
    data, newc, st = move_wp(sess, data, cur, tgt, fr15)
    print(
        f"  {who} {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}",
        flush=True,
    )
    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, "dead"
    if st != "moved":
        return data, st
    return data, "moved"


# After deep15: try x<=55 south / goal-west instead of S6044.
PLANS = [
    # Best light15 mid-path, now with Eb clearing x52
    ("L-N4832-S5242-S5248-S5553", [("L", (36, 44)), ("N", (48, 32)), ("S", (52, 42)), ("S", (52, 48)), ("S", (55, 53))]),
    ("L-N4832-S5242-L4248-R5253", [("L", (36, 44)), ("N", (48, 32)), ("S", (52, 42)), ("L", (42, 48)), ("R", (52, 53))]),
    ("L-N4832-S5242-L4244-S5250", [("L", (36, 44)), ("N", (48, 32)), ("S", (52, 42)), ("L", (42, 44)), ("S", (52, 50))]),
    ("L-N4832-S5544-S5553", [("L", (36, 44)), ("N", (48, 32)), ("S", (55, 44)), ("S", (55, 53))]),
    ("L-N4832-S5248-L4248-R5553", [("L", (36, 44)), ("N", (48, 32)), ("S", (52, 48)), ("L", (42, 48)), ("R", (55, 53))]),
    ("L-N4832-S4848-S5553", [("L", (36, 44)), ("N", (48, 32)), ("S", (48, 48)), ("S", (55, 53))]),
    # Skip N: lag then south toward goal column
    ("L-S4848-R5553", [("L", (36, 44)), ("S", (48, 48)), ("R", (55, 53))]),
    ("L-S5248-L4248", [("L", (36, 44)), ("S", (52, 48)), ("L", (42, 48))]),
    # Baseline x60 for d14 compare under same deep15
    ("base-L-N4832-S6044-N6038-S6048", [("L", (36, 44)), ("N", (48, 32)), ("S", (60, 44)), ("N", (60, 38)), ("S", (60, 48))]),
]


def main():
    hits = []
    for name, steps in PLANS:
        print(f"\n===== {name} =====", flush=True)
        sess, data, ok = boot()
        if not ok:
            print("boot fail", flush=True)
            continue
        d0, _, _ = dump(data, "start")
        failed = False
        for who, tgt in steps:
            if "frame" not in data or step_budget(data["frame"]) < 3:
                print("budout", flush=True)
                failed = True
                break
            data, st = step(sess, data, who, tgt)
            if st == "dead":
                print("DEAD", flush=True)
                failed = True
                break
            if st != "moved":
                print(f"SOFT {st}", flush=True)
                failed = True
                break
            d1, free, _ = dump(data, f"after-{who}{tgt}")
            if d1 < d0:
                print(f"  progress d14 {d0}->{d1}", flush=True)
            if (data.get("levels_completed") or 0) >= 3:
                print("PASS L3!", flush=True)
                hits.append(("PASS", name, d0, 0, step_budget(data["frame"])))
                failed = False
                break
        if failed or "frame" not in data:
            continue
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        d1 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
        tag = "IMPROVED" if d1 < d0 else ("FLAT" if d1 == d0 else "WORSE")
        beat = " BEAT25" if d1 < 25 else (" BEAT20" if d1 < 20 else "")
        free2 = count_free14(data["frame"], lock_other_ship(data["frame"], 14))
        print(
            f"RESULT {tag}{beat} {name} d14 {d0}->{d1} "
            f"bud={step_budget(data['frame'])} free={sorted(free2)}",
            flush=True,
        )
        hits.append((tag, name, d0, d1, step_budget(data["frame"])))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    best = sorted(
        [h for h in hits if h[0] in ("IMPROVED", "PASS", "FLAT")],
        key=lambda x: (0 if x[0] == "PASS" else 1, x[3] if isinstance(x[3], int) else 99, -x[4]),
    )
    print("BEST", best[:10] or "none", flush=True)
    print("BEAT25", [h for h in hits if isinstance(h[3], int) and h[3] < 25] or "none", flush=True)


if __name__ == "__main__":
    main()
