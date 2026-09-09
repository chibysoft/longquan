"""At gate: move east15 first, then west15 deeper; then frog-ny."""
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
    lock_other_ship,
    near_any,
)
from tools.r11l_seated_clear import clear_l1, reset


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me['c']} d14={d14} free14={sorted(free)} "
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}"
    )
    return fr15, free


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l315deep"]},
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
    dump(data, "GATE")

    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    west15 = min(fr15, key=lambda w: w[0])
    east15 = max(fr15, key=lambda w: w[0])

    # Push east15 SE/south so west can go to (48,42)+
    for tgt in ((56, 44), (58, 42), (56, 46), (54, 44), (56, 40), (58, 40)):
        if max(abs(tgt[0] - west15[0]), abs(tgt[1] - west15[1])) < 5:
            continue
        if near_any(tgt, list(freeze14), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, east15, tgt, freeze14)
        print(f"  east15 {east15}->{tgt} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("east15 DEAD")
            return
        if st == "moved":
            dump(data, "E15")
            break

    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    west15 = min(fr15, key=lambda w: w[0])
    east15 = max(fr15, key=lambda w: w[0])
    for tgt in ((48, 42), (50, 42), (48, 44), (50, 44), (46, 44), (52, 42), (46, 42)):
        if max(abs(tgt[0] - east15[0]), abs(tgt[1] - east15[1])) < 5:
            print(f"  skip merge {tgt}")
            continue
        if near_any(tgt, list(freeze14), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, west15, tgt, freeze14)
        print(f"  west15 {west15}->{tgt} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("west15 DEAD", tgt)
            return
        if st == "moved":
            dump(data, "W15")
            break

    # Manual frog without internal 15u (already vacated)
    data, ok = advance_14_frog_ny_stack(sess, data, (34, 57))
    fr15, free = dump(data, "STACK")
    print("ok", ok)
    for cell in ((43, 42), (44, 44), (44, 40), (42, 44), (48, 44), (48, 36)):
        print(f"  near15[{cell}]={near_any(cell, list(fr15), cheb=5)}")

    if len(free) != 2:
        return
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    for cur, ld in (
        (n, (43, 42)),
        (n, (44, 40)),
        (s, (44, 44)),
        (s, (42, 44)),
        (s, (s[0] + 2, s[1])),
        (n, (n[0] + 1, n[1])),
    ):
        other = s if cur == n else n
        if max(abs(ld[0] - other[0]), abs(ld[1] - other[1])) < 5:
            continue
        if near_any(ld, list(fr15), cheb=5):
            continue
        if ld[1] <= 36 and ld[0] >= 45:
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        print(f"  14 {cur}->{ld} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("14DEAD")
            return
        if st == "moved":
            dump(data, "HIT")
            return
    print("no 14")


if __name__ == "__main__":
    main()
