"""From (36,42)/(25,42) + 15 cleared, probe big SE without west-to-33."""
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
        json={"tags": ["r11l_l3alt"]},
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
    for i in range(2):
        data, _ = haul15_toward(sess, data, (34, 57), max_step=8, label=f"15c{i}")
        if data.get("state") == "GAME_OVER":
            print("GO during 15")
            return
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 42]
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    print(f"PROBE lead={lead} lag={lag} freeze15={freeze15} bud={step_budget(data['frame'])} ship={ships(data['frame'])}")

    hits = []
    for ld in (
        (36, 48), (34, 48), (32, 48), (30, 48), (28, 48),
        (36, 50), (32, 50), (28, 50), (24, 50),
        (38, 46), (34, 46), (30, 46), (26, 46),
        (40, 48), (22, 48), (20, 46),
        (36, 44), (34, 44), (30, 44), (28, 44),
        (32, 42), (30, 42), (28, 42),  # west same row
        (36, 42),  # noop self
    ):
        if step_budget(data["frame"]) < 5:
            print("bud low", hits)
            break
        if ld == lead:
            continue
        if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
            continue
        if near_any(ld, list(freeze15), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, lead, ld, freeze15)
        print(f"  L {lead}->{ld} {st}->{newc} bud={step_budget(data['frame'])}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", ld)
            # dead ends session — stop
            return
        if st == "moved":
            hits.append(ld)
            print("HIT", ships(data["frame"]))
            freeze15 = lock_other_ship(data["frame"], 14)
            free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 44]
            lead = max(free14, key=lambda w: (w[1], w[0]))
            lag = min(free14, key=lambda w: (w[1], w[0]))
            if len(hits) >= 2:
                break
    print("hits", hits)


if __name__ == "__main__":
    main()
