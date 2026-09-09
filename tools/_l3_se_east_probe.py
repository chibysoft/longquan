"""Clear 15 farther east, then probe lead east/SE from (36,42)."""
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
    haul15_toward,
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
        json={"tags": ["r11l_l3e"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    lv0 = data.get("levels_completed") or 0
    g15 = (34, 57)
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[0], w[1]))
    lag = min(free14, key=lambda w: (w[0], w[1]))
    data, _, _ = move_wp(sess, data, lead, (lead[0] + 2, lead[1] + 6), freeze15)
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, lag, (lag[0] + 2, lag[1] + 6), freeze15)
    print("after SE", ships(data["frame"]), "bud", step_budget(data["frame"]))

    # Push 15 east hard
    for i in range(3):
        data, ok = haul15_toward(sess, data, g15, max_step=8, label=f"15e{i}")
        print("haul", ok, ships(data["frame"]), step_budget(data["frame"]))
        if data.get("state") == "GAME_OVER":
            return

    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 42]
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    print(f"PROBE lead={lead} lag={lag} freeze15={freeze15} bud={step_budget(data['frame'])}")

    for ld in (
        (lead[0] + 4, lead[1]),
        (lead[0] + 5, lead[1]),
        (lead[0] + 3, lead[1] + 1),
        (lead[0] + 4, lead[1] + 2),
        (lead[0] + 2, lead[1] + 2),
        (lead[0], lead[1] + 2),
        (lead[0] - 2, lead[1] + 2),
        (lead[0] - 3, lead[1] + 2),
        (lead[0] + 6, lead[1]),
        (lead[0] + 2, lead[1] + 4),
    ):
        if step_budget(data["frame"]) < 6:
            break
        if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
            print("skip cheb", ld)
            continue
        if near_any(ld, list(freeze15), cheb=5):
            print("skip near15", ld)
            continue
        data, newc, st = move_wp(sess, data, lead, ld, freeze15)
        print(f"lead {lead}->{ld} {st}->{newc} bud={step_budget(data['frame'])}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD")
            return
        if st == "moved":
            print("HIT", ships(data["frame"]), count_free14(data["frame"], lock_other_ship(data["frame"], 14)))
            break


if __name__ == "__main__":
    main()
