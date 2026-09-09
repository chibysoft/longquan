"""After mid-east: push 15 toward goal hard, then try 14 SE east."""
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
    wave15_once,
)
from tools.r11l_seated_clear import clear_l1, reset


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l315first"]},
        timeout=60,
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
    print("gate", ships(data["frame"]), "bud", step_budget(data["frame"]))

    # Push 15 with wave when possible, else haul
    for i in range(6):
        if step_budget(data["frame"]) < 8:
            break
        me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
        d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
        print(f"15round{i} ship15={me15['c']} d15={d15} bud={step_budget(data['frame'])}")
        if d15 <= 8:
            break
        freeze14 = lock_other_ship(data["frame"], 15)
        if step_budget(data["frame"]) >= 16:
            data, ok = wave15_once(sess, data, freeze14, lv0, stride=10)
            print("  wave", ok, ships(data["frame"]))
        else:
            data, ok = haul15_toward(sess, data, (34, 57), max_step=6, label=f"h{i}")
            print("  haul", ok, ships(data["frame"]))
        if data.get("state") == "GAME_OVER":
            print("GO")
            return

    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    print(f"15done {me15['c']} bud={step_budget(data['frame'])}")

    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[0], w[1]))
    lag = min(free14, key=lambda w: (w[0], w[1]))
    print(f"14try lead={lead} lag={lag} freeze15={freeze15}")

    for ld in (
        (36, 42), (38, 42), (40, 42), (38, 40), (40, 40),
        (36, 44), (38, 44), (34, 42), (32, 42),
        (40, 48), (42, 46), (44, 48), (45, 50),
    ):
        if step_budget(data["frame"]) < 5:
            break
        freeze15 = lock_other_ship(data["frame"], 14)
        free14 = count_free14(data["frame"], freeze15)
        lead = max(free14, key=lambda w: (w[0], w[1]))
        lag = min(free14, key=lambda w: (w[0], w[1]))
        if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
            continue
        if near_any(ld, list(freeze15), cheb=5):
            print("skip", ld)
            continue
        data, newc, st = move_wp(sess, data, lead, ld, freeze15)
        print(f"  L {lead}->{ld} {st}->{newc} bud={step_budget(data['frame'])}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", ld)
            return
        if st == "moved":
            print("HIT", ships(data["frame"]))
            break


if __name__ == "__main__":
    main()
