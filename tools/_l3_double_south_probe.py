"""Lead double-south before any lag catch; then lag +4/+8 catch."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, haul15_toward, lock_other_ship, near_any
from tools.r11l_seated_clear import clear_l1, reset


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(f"{label} ship={me['c']} d14={d14} free={free} n={len(free)} bud={step_budget(data['frame'])}")
    return fr15, free, me


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3dbl"]},
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
    data, _ = haul15_toward(sess, data, (34, 57), max_step=6, label="15e")
    fr15, free, me = dump(data, "GATE")
    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])

    # Lead S4 twice without catching
    for i, ld in enumerate([(lead[0], 40), (lead[0], 44), (lead[0] + 2, 44), (lead[0], 48)]):
        fr15, free, me = dump(data, f"preL{i}")
        if len(free) != 2:
            print("broke")
            return
        lead = max(free, key=lambda w: (w[1], w[0]))
        lag = min(free, key=lambda w: (w[1], w[0]))
        # retarget ld relative
        if i == 0:
            ld = (lead[0], lead[1] + 4)
        elif i == 1:
            ld = (lead[0], lead[1] + 4)
        if near_any(ld, list(fr15), cheb=5):
            print("near15", ld)
            continue
        if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
            print("cheb", ld)
            continue
        data, newc, st = move_wp(sess, data, lead, ld, fr15)
        print(f"  L{i} {lead}->{ld} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD")
            return
        if st != "moved":
            print("noop stop lead chain")
            break
        fr15, free, me = dump(data, f"L{i}")
        if len(free) != 2:
            print("FLOCK BREAK")
            return

    # Now catch lag with +4 steps
    fr15, free, me = dump(data, "catchphase")
    for j in range(4):
        if len(free) != 2 or step_budget(data["frame"]) < 6:
            break
        lead = max(free, key=lambda w: (w[1], w[0]))
        lag = min(free, key=lambda w: (w[1], w[0]))
        if lead[1] - lag[1] <= 2:
            print("lag close enough")
            break
        for gd in (
            (lag[0] + 2, lag[1] + 4),
            (lag[0], lag[1] + 4),
            (lag[0] + 4, lag[1] + 4),
            (lead[0] - 6, min(lead[1], lag[1] + 4)),
        ):
            if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
                continue
            if near_any(gd, list(fr15), cheb=5):
                continue
            data, newc, st = move_wp(sess, data, lag, gd, fr15)
            print(f"  G{j} {lag}->{gd} {st}")
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD G")
                return
            if st == "moved":
                fr15, free, me = dump(data, f"G{j}")
                if len(free) != 2:
                    print("FLOCK BREAK G")
                    return
                break
        else:
            print("lag stuck")
            break
    dump(data, "END")


if __name__ == "__main__":
    main()
