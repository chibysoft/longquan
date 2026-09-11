"""After se-ny S6248 (bud≈6, east15 still @58,54): scan non-near15 S/N HITs."""
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
    advance_14_frog_ny_stack,
    clear15_corridor,
    count_free14,
    goals_by_chrome,
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
    return d14, d15, free, fr15


def boot():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_p6248"]},
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
    gmap = goals_by_chrome(data["frame"])
    data, ok = advance_14_frog_ny_stack(sess, data, gmap.get(15, (34, 57)))
    if not ok or "frame" not in data:
        return sess, data, False
    dump(data, "boot")
    return sess, data, True


# Avoid cheb≤5 to east15@(58,54).
PLANS = [
    ("S5052", [("S", (50, 52))]),
    ("S4852", [("S", (48, 52))]),
    ("S5254", [("S", (52, 54))]),
    ("S4850", [("S", (48, 50))]),
    ("S5050", [("S", (50, 50))]),
    ("S5450", [("S", (54, 50))]),  # may near15
    ("S5648", [("S", (56, 48))]),
    ("S5448", [("S", (54, 48))]),
    ("N5644", [("N", (56, 44))]),
    ("N5444", [("N", (54, 44))]),
    ("N5244", [("N", (52, 44))]),
    ("vacE-S5652", [("E", (52, 58)), ("S", (56, 52))]),
    ("vacE-S5452", [("E", (52, 58)), ("S", (54, 52))]),
    ("vacE-S5553", [("E", (52, 58)), ("S", (55, 53))]),
    ("vacE-S5052", [("E", (52, 58)), ("S", (50, 52))]),
    ("S5052-N5644", [("S", (50, 52)), ("N", (56, 44))]),
    ("S4852-S5052", [("S", (48, 52)), ("S", (50, 52))]),
]


def main():
    hits = []
    for name, steps in PLANS:
        print(f"\n===== {name} =====", flush=True)
        sess, data, ok = boot()
        if not ok:
            print("boot fail", flush=True)
            continue
        d0, _, free, fr15 = dump(data, "start")
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
        d1, d15, free2, _ = dump(data, "END")
        tag = "IMPROVED" if d1 < d0 else ("FLAT" if d1 == d0 else "WORSE")
        print(f"RESULT {tag} {name} d14 {d0}->{d1} d15={d15} bud={step_budget(data['frame'])} free={sorted(free2)}", flush=True)
        hits.append((tag, name, d0, d1, d15, step_budget(data["frame"])))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    best = [h for h in hits if h[0] == "IMPROVED"]
    print("IMPROVED", best or "none", flush=True)


if __name__ == "__main__":
    main()
