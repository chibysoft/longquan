"""From SE2+lagE state, probe lead/lag next moves."""
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


def setup():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3next"]},
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
    data, _, _ = move_wp(sess, data, lead, (lead[0] + 2, lead[1] + 6), freeze15)
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, lag, (lag[0] + 2, lag[1] + 6), freeze15)
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, lead, (lead[0] - 3, lead[1] + 2), freeze15)
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, lag, (lag[0] + 3, lag[1]), freeze15)
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 42]
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    print(f"READY ship={me['c']} lead={lead} lag={lag} freeze15={freeze15} bud={step_budget(data['frame'])}")
    return sess, data, lead, lag, freeze15


def main():
    sess, data, lead, lag, freeze15 = setup()
    # Phase A: lag soft moves
    print("--- LAG ---")
    for gd in (
        (lag[0] - 3, lag[1] + 1),
        (lag[0] - 4, lag[1] + 1),
        (lag[0] - 2, lag[1] + 1),
        (lag[0] - 3, lag[1] + 2),
        (lag[0] + 1, lag[1] + 1),
        (lag[0], lag[1] + 1),
        (lag[0] + 2, lag[1] + 1),
        (lag[0] - 5, lag[1]),
        (lag[0] + 2, lag[1]),
    ):
        if step_budget(data["frame"]) < 6:
            break
        if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
            print(f"  skip {gd} cheb")
            continue
        if near_any(gd, list(freeze15), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, lag, gd, freeze15)
        print(f"  lag {lag}->{gd} {st}->{newc} bud={step_budget(data['frame'])}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD")
            return
        if st == "moved":
            freeze15 = lock_other_ship(data["frame"], 14)
            free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 42]
            lag = min(free14, key=lambda w: (w[1], w[0]))
            lead = max(free14, key=lambda w: (w[1], w[0]))
            print(f"  now lead={lead} lag={lag} ship={ships(data['frame'])}")
            break

    # Phase B: lead moves (fresh relative)
    print("--- LEAD ---")
    for ld in (
        (lead[0] + 4, lead[1]),
        (lead[0] + 5, lead[1]),
        (lead[0] + 3, lead[1]),
        (lead[0] + 4, lead[1] + 1),
        (lead[0] + 2, lead[1] + 1),
        (lead[0] - 2, lead[1] + 1),
        (lead[0] - 4, lead[1]),
        (lead[0], lead[1] + 1),
        (lead[0] - 1, lead[1] + 2),
        (lead[0] + 1, lead[1] + 2),
        (lead[0] - 3, lead[1] + 2),
    ):
        if step_budget(data["frame"]) < 6:
            break
        if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
            print(f"  skip lead {ld} cheb")
            continue
        if near_any(ld, list(freeze15), cheb=6):
            continue
        data, newc, st = move_wp(sess, data, lead, ld, freeze15)
        print(f"  lead {lead}->{ld} {st}->{newc} bud={step_budget(data['frame'])}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD")
            return
        if st == "moved":
            freeze15 = lock_other_ship(data["frame"], 14)
            free14 = count_free14(data["frame"], freeze15)
            me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            print(f"  HIT lead ship={me['c']} free={free14}")
            break
    print("done bud", step_budget(data["frame"]))


if __name__ == "__main__":
    main()
