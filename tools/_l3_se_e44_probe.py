"""From (28,44)/(18,44) try east along y=44, then south."""
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


def refresh(data):
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 45]
    if len(free14) < 2:
        free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[0], w[1]))
    lag = min(free14, key=lambda w: (w[0], w[1]))
    return freeze15, lead, lag


def setup():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3e44"]},
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
    freeze15, lead, lag = refresh(data)
    data, _, _ = move_wp(sess, data, lead, (36, 42), freeze15)
    freeze15, lead, lag = refresh(data)
    data, _, _ = move_wp(sess, data, lag, (25, 42), freeze15)
    freeze15, lead, lag = refresh(data)
    data, _, _ = move_wp(sess, data, lead, (33, 44), freeze15)
    freeze15, lead, lag = refresh(data)
    for gd in ((22, 43), (18, 44)):
        freeze15, lead, lag = refresh(data)
        data, _, _ = move_wp(sess, data, lag, gd, freeze15)
    freeze15, lead, lag = refresh(data)
    data, _, _ = move_wp(sess, data, lead, (28, 44), freeze15)
    return sess, data


def main():
    sess, data = setup()
    freeze15, lead, lag = refresh(data)
    print(f"READY lead={lead} lag={lag} ship={ships(data['frame'])} bud={step_budget(data['frame'])}")

    # Compact lag east toward lead first (gap=10)
    for gd in ((22, 44), (20, 44), (23, 44)):
        freeze15, lead, lag = refresh(data)
        if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
            continue
        data, newc, st = move_wp(sess, data, lag, gd, freeze15)
        print(f"  compact {lag}->{gd} {st}->{newc} bud={step_budget(data['frame'])}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD")
            return
        if st == "moved":
            break

    freeze15, lead, lag = refresh(data)
    print(f"COMPACT lead={lead} lag={lag} ship={ships(data['frame'])}")

    for ld in (
        (32, 44), (34, 44), (36, 44), (38, 44), (40, 44),
        (32, 46), (34, 46), (30, 46),
        (28, 42), (30, 42),  # north?
        (24, 44), (22, 44),
    ):
        if step_budget(data["frame"]) < 5:
            break
        freeze15, lead, lag = refresh(data)
        if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
            continue
        if near_any(ld, list(freeze15), cheb=5):
            print("near15", ld, freeze15)
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
