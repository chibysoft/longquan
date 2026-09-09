"""After 15u+frog: try (48,36) / (46,36) / (47,36) — previously dead under old seal."""
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


def setup():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3y36u"]},
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
    west15 = min(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
    data, _, st = move_wp(sess, data, west15, (46, 42), freeze14)
    print("15u", st)
    data, ok = advance_14_frog_ny_stack(sess, data, (34, 57))
    return sess, data, ok


def main():
    for ld in ((48, 36), (47, 36), (46, 36), (49, 36), (50, 36), (48, 38), (50, 38)):
        print(f"=== try {ld} ===")
        sess, data, ok = setup()
        if not ok:
            print("setup fail")
            continue
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        s = max(free, key=lambda w: (w[1], w[0]))
        n = min(free, key=lambda w: (w[1], w[0]))
        if near_any(ld, list(fr15), cheb=5):
            print("near15")
            continue
        if max(abs(ld[0] - s[0]), abs(ld[1] - s[1])) < 5:
            print("merge")
            continue
        data, newc, st = move_wp(sess, data, n, ld, fr15)
        me = next(x for x in ships(data["frame"]) if x["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(f"  {n}->{ld} {st}->{newc} ship={me['c']} d14={d14} bud={step_budget(data['frame'])}")
        if st == "dead":
            print("DEAD")
            continue
        if st == "moved":
            print("HIT")
            fr15 = lock_other_ship(data["frame"], 14)
            print("free", sorted(count_free14(data["frame"], fr15)))
            return
    print("done")


if __name__ == "__main__":
    main()
