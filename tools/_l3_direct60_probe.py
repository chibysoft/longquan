"""Skip S5242/S5642: Ny46 → N4832 → S(60,44) direct — save bud."""
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


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(
        f"{label} ship={me['c']} d14={d14} free={sorted(free)} "
        f"fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14


def boot_ny46():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_direct60"]},
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
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, _ = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, _ = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, _ = move_wp(
        sess, data, max(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (58, 50), freeze14
    )
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lag = min(free, key=lambda w: w[0])
    data, _, _ = move_wp(sess, data, lag, (26, 44), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    src = (26, 44) if (26, 44) in free else max(free, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, src, (36, 44), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, north, (46, 36), fr15)
    dump(data, "NY46")
    return sess, data


PLANS = [
    ("N4832-S6044", [("N", (48, 32)), ("S", (60, 44))]),
    ("N4832-S5642-S6044", [("N", (48, 32)), ("S", (56, 42)), ("S", (60, 44))]),
    ("N4832-S5242-S6044", [("N", (48, 32)), ("S", (52, 42)), ("S", (60, 44))]),
    ("N4832-S6046", [("N", (48, 32)), ("S", (60, 46))]),
    ("N4832-S6244", [("N", (48, 32)), ("S", (62, 44))]),
    ("base-chain", [("N", (48, 32)), ("S", (52, 42)), ("S", (56, 42)), ("S", (60, 44))]),
]


def main():
    for name, steps in PLANS:
        print(f"\n===== {name} =====", flush=True)
        sess, data = boot_ny46()
        d0 = dump(data, "start")
        ok = True
        for who, tgt in steps:
            fr15 = lock_other_ship(data["frame"], 14)
            free = count_free14(data["frame"], fr15)
            if len(free) < 2:
                print(f"flock n={len(free)}", flush=True)
                ok = False
                break
            north = min(free, key=lambda w: (w[1], w[0]))
            south = max(free, key=lambda w: (w[1], w[0]))
            cur = north if who == "N" else south
            other = south if who == "N" else north
            if cheb(tgt, other) < 5:
                print(f"  {who}->{tgt} merge", flush=True)
                ok = False
                break
            if near_any(tgt, list(fr15), cheb=5):
                print(f"  {who}->{tgt} near15", flush=True)
                ok = False
                break
            data, newc, st = move_wp(sess, data, cur, tgt, fr15)
            print(
                f"  {who} {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}",
                flush=True,
            )
            if st != "moved":
                ok = False
                break
            dump(data, f"after-{tgt}")
        if ok:
            d1 = dump(data, "END")
            print(f"RESULT {name} d14 {d0}->{d1} bud={step_budget(data['frame'])}", flush=True)


if __name__ == "__main__":
    main()
