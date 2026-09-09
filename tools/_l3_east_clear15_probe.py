"""Clear 15 far east, then dual-east on y36 with wp dumps."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
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


def dump(data, label):
    wps = [w["c"] for w in r11l.waypoints(data["frame"])]
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    print(
        f"{label} ship14={me['c']} ship15={me15['c']} wps={wps} "
        f"freeze15={fr15} free14={free} bud={step_budget(data['frame'])}"
    )
    return fr15, free


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3clr2"]},
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
    dump(data, "GATE")

    # Haul 15 until western flock wp x>=48
    for i in range(5):
        fr15, _ = dump(data, f"pre15-{i}")
        west = min((p[0] for p in fr15), default=99)
        if west >= 48:
            print("15 clear enough")
            break
        data, ok = haul15_toward(sess, data, (34, 57), max_step=8, label=f"15h{i}")
        if data.get("state") == "GAME_OVER":
            print("GO")
            return
        if not ok:
            # force move western 15 wp further east
            fr15 = lock_other_ship(data["frame"], 14)
            freeze14 = lock_other_ship(data["frame"], 15)
            if not fr15:
                break
            wp = min(fr15, key=lambda w: w[0])
            for dest in ((wp[0] + 6, wp[1]), (wp[0] + 8, wp[1]), (wp[0] + 4, wp[1] + 2)):
                if near_any(dest, freeze14, cheb=5):
                    continue
                data, newc, st = move_wp(sess, data, wp, dest, freeze14)
                print(f"  force15 {wp}->{dest} {st}->{newc}")
                if st == "moved":
                    break
                if st == "dead" or data.get("state") == "GAME_OVER":
                    print("DEAD15")
                    return

    fr15, free = dump(data, "READY")
    if len(free) != 2:
        print("need 2")
        return
    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])

    for dx in (3, 2, 4, 5):
        ld = (lead[0] + dx, lead[1])
        if near_any(ld, list(fr15), cheb=5):
            print(f"skip near15 {ld} fr={fr15}")
            continue
        if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
            continue
        data, newc, st = move_wp(sess, data, lead, ld, fr15)
        print(f"LEAD+{dx} {lead}->{ld} {st}->{newc}")
        dump(data, f"after+{dx}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD")
            return
        if st == "moved":
            fr15, free = dump(data, "postlead")
            if len(free) != 2:
                print("FLOCK BREAK — try recover?")
                return
            lead = max(free, key=lambda w: w[0])
            lag = min(free, key=lambda w: w[0])
            # lag catch
            for ldx in (4, 5, 6, 3, 7):
                gd = (lag[0] + ldx, lag[1])
                if gd[0] >= lead[0]:
                    continue
                if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
                    continue
                if near_any(gd, list(fr15), cheb=5):
                    continue
                data, newc, st = move_wp(sess, data, lag, gd, fr15)
                print(f"LAG+{ldx} {lag}->{gd} {st}->{newc}")
                dump(data, "postlag")
                if st == "moved":
                    break
                if st == "dead" or data.get("state") == "GAME_OVER":
                    print("DEAD lag")
                    return
            break


if __name__ == "__main__":
    main()
