"""From N6038→S6048 same-col (60,38)+(60,48) d14=25 bud≈6: scan continuations."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import (
    clear15_corridor,
    count_free14,
    lock_other_ship,
    near_any,
)
from tools.r11l_seated_clear import clear_l1, reset


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me14["c"][0] - 55) + abs(me14["c"][1] - 53)
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me14['c']} d14={d14} free={sorted(free)} "
        f"d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, free, fr15


def deep15(sess, data):
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    if st != "moved":
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    if st != "moved":
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    east = max(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
    data, _, st = move_wp(sess, data, east, (58, 54), freeze14)
    return data, st == "moved"


def to_s6048(sess, data, *, vac_first=False):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lag = min(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lag, (36, 44), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (48, 32), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, (60, 44), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (60, 38), fr15)
    if st != "moved":
        return data, False
    if vac_first:
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        north = min(free, key=lambda w: (w[1], w[0]))
        south = max(free, key=lambda w: (w[1], w[0]))
        flock = [c for c in fr15 if c not in (north, south)] or list(fr15)
        east = next((c for c in flock if c in ((58, 54), (58, 50))), max(flock, key=lambda w: w[1]))
        data, _, st = move_wp(sess, data, east, (52, 58), [north, south])
        print(f"  vacE {st} bud={step_budget(data['frame'])}", flush=True)
        if st != "moved":
            return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, (60, 48), fr15)
    print(f"  S6048 {st} bud={step_budget(data['frame'])}", flush=True)
    return data, st == "moved"


def boot(vac_first=False):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_s6048"]},
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
    if not ok:
        return sess, data, False
    data, ok = to_s6048(sess, data, vac_first=vac_first)
    if not ok:
        return sess, data, False
    dump(data, "S6048")
    return sess, data, True


PLANS = [
    ("S6052", False, [("S", (60, 52))]),
    ("S6050", False, [("S", (60, 50))]),
    ("S5553", False, [("S", (55, 53))]),
    ("S5652", False, [("S", (56, 52))]),
    ("S5452", False, [("S", (54, 52))]),
    ("S5252", False, [("S", (52, 52))]),
    ("S5052", False, [("S", (50, 52))]),
    ("S5852", False, [("S", (58, 52))]),
    ("S6252", False, [("S", (62, 52))]),
    ("S6054", False, [("S", (60, 54))]),
    ("N5642", False, [("N", (56, 42))]),
    ("N5544", False, [("N", (55, 44))]),
    ("vacE-S6052", False, [("E", (52, 58)), ("S", (60, 52))]),
    ("vacE-S5553", False, [("E", (52, 58)), ("S", (55, 53))]),
    ("vacE-S5652", False, [("E", (52, 58)), ("S", (56, 52))]),
    ("vac1st-S6052", True, [("S", (60, 52))]),
    ("vac1st-S5553", True, [("S", (55, 53))]),
    ("vac1st-S5652", True, [("S", (56, 52))]),
]


def main():
    hits = []
    for name, vac1, steps in PLANS:
        print(f"\n===== {name} =====", flush=True)
        sess, data, ok = boot(vac_first=vac1)
        if not ok:
            print("boot fail", flush=True)
            continue
        d0, free, fr15 = dump(data, "start")
        failed = False
        for who, tgt in steps:
            if "frame" not in data or step_budget(data["frame"]) < 3:
                print("budout", flush=True)
                failed = True
                break
            fr15 = lock_other_ship(data["frame"], 14)
            free = count_free14(data["frame"], fr15)
            if len(free) < 2:
                print(f"n={len(free)}", flush=True)
                failed = True
                break
            north = min(free, key=lambda w: (w[1], w[0]))
            south = max(free, key=lambda w: (w[1], w[0]))
            if who == "E":
                flock = [c for c in fr15 if c not in (north, south)] or list(fr15)
                cur = next(
                    (c for c in flock if c in ((58, 54), (58, 50))),
                    max(flock, key=lambda w: w[1]),
                )
                lock = [north, south]
            else:
                cur = south if who == "S" else north
                other = north if who == "S" else south
                if cheb(tgt, other) < 5:
                    print(f"  {who}->{tgt} merge", flush=True)
                    failed = True
                    break
                if near_any(tgt, list(fr15), cheb=5):
                    print(f"  {who}->{tgt} near15", flush=True)
                    failed = True
                    break
                lock = fr15
            data, newc, st = move_wp(sess, data, cur, tgt, lock)
            print(
                f"  {who} {cur}->{tgt} {st}->{newc} "
                f"bud={step_budget(data['frame']) if 'frame' in data else '?'}",
                flush=True,
            )
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                print("DEAD", flush=True)
                failed = True
                break
            if st != "moved":
                print(f"SOFT {st}", flush=True)
                failed = True
                break
        if failed or "frame" not in data:
            continue
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        d1 = abs(me14["c"][0] - 55) + abs(me14["c"][1] - 53)
        me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
        d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
        free2 = count_free14(data["frame"], lock_other_ship(data["frame"], 14))
        tag = "IMPROVED" if d1 < d0 else ("FLAT" if d1 == d0 else "WORSE")
        print(
            f"RESULT {tag} {name} d14 {d0}->{d1} d15={d15} "
            f"bud={step_budget(data['frame'])} free={sorted(free2)}",
            flush=True,
        )
        hits.append((tag, name, d0, d1, d15, step_budget(data["frame"])))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    print("IMPROVED", [h for h in hits if h[0] == "IMPROVED"] or "none", flush=True)


if __name__ == "__main__":
    main()
