"""Try alternate first SE-lead dests from gate (34,36). Stop at first moved."""
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
        json={"tags": ["r11l_l3first"]},
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
    print(f"GATE lead={lead} lag={lag} freeze15={freeze15} bud={step_budget(data['frame'])}")

    # Avoid known dead: (34,48),(30,50),(41,42)
    # Prefer untried; put known (36,42) last as control
    cands = [
        (32, 42), (30, 42), (28, 42), (34, 42), (38, 42),
        (32, 40), (30, 40), (36, 40), (38, 40), (40, 40),
        (34, 40), (32, 44), (30, 44), (28, 44), (36, 44),
        (38, 38), (32, 38), (40, 38),
        (36, 42),  # known HIT
    ]
    for ld in cands:
        if step_budget(data["frame"]) < 6:
            print("bud low")
            break
        if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
            print("skip cheb", ld)
            continue
        if near_any(ld, list(freeze15), cheb=5):
            print("skip 15", ld)
            continue
        data, newc, st = move_wp(sess, data, lead, ld, freeze15)
        print(f"  {lead}->{ld} {st}->{newc} bud={step_budget(data['frame'])}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", ld)
            return
        if st == "moved":
            print("HIT", ships(data["frame"]), count_free14(data["frame"], lock_other_ship(data["frame"], 14)))
            # Try lag follow to same dy
            freeze15 = lock_other_ship(data["frame"], 14)
            free14 = count_free14(data["frame"], freeze15)
            lead = max(free14, key=lambda w: (w[1], w[0]))
            lag = min(free14, key=lambda w: (w[1], w[0]))
            for gd in (
                (lag[0] + 2, ld[1]),
                (lag[0] + 4, ld[1]),
                (lag[0] + 2, lag[1] + 6),
                (lead[0] - 6, lead[1]),
            ):
                if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
                    continue
                if near_any(gd, [lead] + list(freeze15), cheb=5):
                    continue
                data, newc, st = move_wp(sess, data, lag, gd, freeze15)
                print(f"  lag {lag}->{gd} {st}->{newc} ship={ships(data['frame'])}")
                if st == "moved":
                    break
                if st == "dead" or data.get("state") == "GAME_OVER":
                    print("DEAD lag")
                    return
            return
    print("no hit")


if __name__ == "__main__":
    main()
