"""Budget-tight: SE+(33,44)+lag west to y44, then lead west-south."""
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


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3ww2"]},
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
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[0], w[1]))
    lag = min(free14, key=lambda w: (w[0], w[1]))
    # No 15 clear — save bud; SE dual + SE2 + lag west
    data, _, _ = move_wp(sess, data, lead, (36, 42), freeze15)
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, lag, (25, 42), freeze15)
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, lead, (33, 44), freeze15)
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    print(f"SE2done lead={lead} lag={lag} bud={step_budget(data['frame'])} ship={ships(data['frame'])}")

    for gd in ((25, 43), (22, 43), (18, 44), (20, 44)):
        freeze15 = lock_other_ship(data["frame"], 14)
        free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 42]
        lead = max(free14, key=lambda w: (w[1], w[0]))
        lag = min(free14, key=lambda w: (w[1], w[0]))
        if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
            continue
        data, newc, st = move_wp(sess, data, lag, gd, freeze15)
        print(f"  G {lag}->{gd} {st}->{newc} bud={step_budget(data['frame'])}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD")
            return
        if st != "moved":
            continue
        print("  ship", ships(data["frame"]))

    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 42]
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    print(f"ALIGNED lead={lead} lag={lag} bud={step_budget(data['frame'])}")

    for ld in (
        (28, 44), (26, 44), (24, 44), (22, 44),
        (28, 46), (26, 46), (24, 46), (22, 46),
        (26, 48), (24, 48), (22, 48), (20, 48),
        (24, 50), (22, 50), (20, 50), (18, 50),
        (30, 46), (27, 47), (25, 48),
    ):
        if step_budget(data["frame"]) < 5:
            print("bud low")
            break
        freeze15 = lock_other_ship(data["frame"], 14)
        free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 42]
        lead = max(free14, key=lambda w: (w[1], w[0]))
        lag = min(free14, key=lambda w: (w[1], w[0]))
        if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
            continue
        if near_any(ld, list(freeze15), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, lead, ld, freeze15)
        print(f"  L {lead}->{ld} {st}->{newc} bud={step_budget(data['frame'])}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", ld)
            return
        if st == "moved":
            print("HIT", ships(data["frame"]), count_free14(data["frame"], lock_other_ship(data["frame"], 14)))
            break


if __name__ == "__main__":
    main()
