"""From (33,44)/(28,42) try big leaps south/west-south."""
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
        json={"tags": ["r11l_l3big"]},
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
    data, _, _ = move_wp(sess, data, lead, (36, 42), freeze15)
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, lag, (25, 42), freeze15)
    data, _ = haul15_toward(sess, data, (34, 57), max_step=8, label="15c")
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max([w for w in free14 if w[0] <= 42], key=lambda w: (w[1], w[0]))
    lag = min([w for w in free14 if w[0] <= 42], key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lead, (33, 44), freeze15)
    print("SE2", st)
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 42]
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (28, 42), freeze15)
    print("lagE", st, ships(data["frame"]), "bud", step_budget(data["frame"]))
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 42]
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    print(f"PROBE lead={lead} lag={lag} freeze15={freeze15}")

    print("--- LEAD BIG ---")
    for ld in (
        (33, 50), (30, 50), (28, 50), (25, 50), (36, 50),
        (33, 48), (30, 48), (28, 48), (20, 48),
        (30, 46), (28, 46), (25, 46), (22, 46),
        (36, 48), (38, 48), (20, 44), (25, 44),
        (30, 52), (33, 52), (28, 52),
    ):
        if step_budget(data["frame"]) < 5:
            break
        if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
            continue
        if near_any(ld, list(freeze15), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, lead, ld, freeze15)
        print(f"  L {lead}->{ld} {st}->{newc} bud={step_budget(data['frame'])}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD lead", ld)
            return
        if st == "moved":
            print("HIT LEAD", ships(data["frame"]))
            freeze15 = lock_other_ship(data["frame"], 14)
            free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 44]
            lead = max(free14, key=lambda w: (w[1], w[0]))
            lag = min(free14, key=lambda w: (w[1], w[0]))
            break

    print("--- LAG BIG ---")
    for gd in (
        (28, 48), (25, 48), (22, 48), (20, 48),
        (28, 46), (25, 46), (22, 46),
        (25, 44), (22, 44), (20, 44),
        (30, 48), (18, 46), (28, 50), (24, 50),
    ):
        if step_budget(data["frame"]) < 5:
            break
        if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
            continue
        if near_any(gd, list(freeze15), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, lag, gd, freeze15)
        print(f"  G {lag}->{gd} {st}->{newc} bud={step_budget(data['frame'])}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD lag", gd)
            return
        if st == "moved":
            print("HIT LAG", ships(data["frame"]))
            break


if __name__ == "__main__":
    main()
