"""Single shot: N43 then (43,42)."""
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


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l34342"]},
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
    data, ok = advance_14_frog_ny_stack(sess, data, (34, 57))
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    print(f"base ship={me['c']} free={sorted(free)} bud={step_budget(data['frame'])} ok={ok}")
    if len(free) != 2:
        return
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    for ld in ((43, 42), (43, 40), (44, 40), (42, 40), (44, 42), (42, 42)):
        other = s
        cheb = max(abs(ld[0] - other[0]), abs(ld[1] - other[1]))
        near = near_any(ld, list(fr15), cheb=5)
        print(f"  cand {ld} cheb={cheb} near15={near}")
        if cheb < 5 or near:
            continue
        data, newc, st = move_wp(sess, data, n, ld, fr15)
        me = next(x for x in ships(data["frame"]) if x["chrome"] == 14)
        print(f"  {n}->{ld} {st}->{newc} ship={me['c']} bud={step_budget(data['frame'])}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD")
            return
        if st == "moved":
            fr15 = lock_other_ship(data["frame"], 14)
            free = count_free14(data["frame"], fr15)
            print(f"HIT free={sorted(free)}")
            return
    print("none")


if __name__ == "__main__":
    main()
