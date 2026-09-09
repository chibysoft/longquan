"""N44 bud≈10: vacate15 then SE; also try Ny46 before S."""
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
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me['c']} d14={d14} free={sorted(free)} n={len(free)} "
        f"d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, free, fr15


def to_deep_frog(sess, data, lv0):
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
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    return data, st == "moved"


def open_sess(tag):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": [f"r11l_{tag}"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    return sess, data, data.get("levels_completed") or 0


def try_ny_s(name, nyt):
    print(f"\n===== {name} Ny={nyt} =====", flush=True)
    sess, data, lv0 = open_sess(name)
    data, ok = to_deep_frog(sess, data, lv0)
    if not ok:
        print("frog fail", flush=True)
        return
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, nyt, fr15)
    print(f"  Ny {north}->{nyt} {st}", flush=True)
    if st != "moved":
        return
    dump(data, "N")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, (48, 42), fr15)
    print(f"  S {south}->(48,42) {st}", flush=True)
    if st != "moved":
        dump(data, "Sfail")
        return
    d14, free, fr15 = dump(data, "S")
    beat = d14 < 34 or (d14 <= 34 and step_budget(data["frame"]) >= 8)
    print(
        f"=== {'BEAT' if beat else 'best'} {name}: d14={d14} "
        f"bud={step_budget(data['frame'])} free={sorted(free)} ===",
        flush=True,
    )


def try_vac_then_se():
    print("\n===== vac15 then SE from N44 =====", flush=True)
    sess, data, lv0 = open_sess("vacse")
    data, ok = to_deep_frog(sess, data, lv0)
    if not ok:
        return
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (44, 36), fr15)
    if st != "moved":
        return
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, (48, 42), fr15)
    if st != "moved":
        return
    d0, free, fr15 = dump(data, "N44")
    # vacate west15 further south/west
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    east = max(flock, key=lambda w: w[0])
    for wt in ((38, 54), (34, 56), (42, 54), (36, 52)):
        if cheb(wt, east) < 5:
            continue
        data, _, st = move_wp(sess, data, west, wt, freeze14)
        print(f"  vac {west}->{wt} {st}", flush=True)
        if st == "moved":
            break
        if st == "dead":
            dump(data, "vacdead")
            return
    d1, free, fr15 = dump(data, "VACed")
    if len(free) != 2:
        print("flock after vac", flush=True)
        return
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    for who, tgt in (
        ("S", (52, 44)),
        ("S", (50, 46)),
        ("S", (52, 46)),
        ("S", (54, 44)),
        ("S", (50, 44)),
        ("N", (48, 38)),
        ("N", (46, 40)),
        ("N", (50, 38)),
        ("N", (48, 40)),
    ):
        cur = south if who == "S" else north
        other = north if who == "S" else south
        if cheb(tgt, other) < 5 or near_any(tgt, list(fr15), cheb=5):
            print(f"  skip {who} {tgt}", flush=True)
            continue
        if step_budget(data["frame"]) < 4:
            break
        data, newc, st = move_wp(sess, data, cur, tgt, fr15)
        print(f"  {who} {cur}->{tgt} {st}->{newc}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", flush=True)
            return
        if st == "moved":
            d2, free2, _ = dump(data, "HIT")
            if len(free2) == 2 and d2 < d1:
                print(f"IMPROVED {d1}->{d2} bud={step_budget(data['frame'])}", flush=True)
            break
        # one soft — refresh and try next without burning more? already burned
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) != 2:
            break
        north = min(free, key=lambda w: (w[1], w[0]))
        south = max(free, key=lambda w: (w[1], w[0]))


def main():
    for nyt in ((46, 36), (48, 36), (45, 36), (44, 36), (43, 36)):
        try_ny_s(f"Ny{nyt[0]}", nyt)
    try_vac_then_se()


if __name__ == "__main__":
    main()
