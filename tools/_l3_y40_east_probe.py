"""Aligned at y40: try lead east +2/+3 (not +4) to keep flock."""
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
from longquan.interactive import r11l


def dump(data, label):
    wps = [w["c"] for w in r11l.waypoints(data["frame"])]
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(f"{label} ship={me['c']} d14={d14} free={free} n={len(free)} bud={step_budget(data['frame'])}")
    return fr15, free, me


def to_y40(sess, data):
    data, _ = haul15_toward(sess, data, (34, 57), max_step=6, label="15e")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print(f"S4 {st}")
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    for gd in ((lag[0] + 2, lead[1]), (lag[0] + 4, lead[1]), (lead[0] - 6, lead[1])):
        if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
            continue
        data, _, st = move_wp(sess, data, lag, gd, fr15)
        print(f"catch {lag}->{gd} {st}")
        if st == "moved":
            return data, True
        if st == "dead" or data.get("state") == "GAME_OVER":
            return data, False
    return data, True


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3y40e"]},
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
    data, ok = to_y40(sess, data)
    if data.get("state") == "GAME_OVER":
        print("GO")
        return
    fr15, free, me = dump(data, "Y40")
    if len(free) != 2:
        print("not 2")
        return

    for rnd in range(6):
        if step_budget(data["frame"]) < 8:
            break
        fr15, free, me = dump(data, f"r{rnd}")
        if len(free) != 2:
            print("broke")
            break
        lead = max(free, key=lambda w: w[0])
        lag = min(free, key=lambda w: w[0])
        gap = lead[0] - lag[0]
        # Keep gap_after <= 12
        for dx in (2, 3, 1, 4):
            if lead[0] + dx - lag[0] > 12:
                continue
            ld = (lead[0] + dx, lead[1])
            if near_any(ld, list(fr15), cheb=5):
                print(f"  near15 {ld} — clear 15")
                freeze14 = lock_other_ship(data["frame"], 15)
                flock = lock_other_ship(data["frame"], 14)
                if flock:
                    wp = min(flock, key=lambda w: w[0])
                    data, _, st = move_wp(sess, data, wp, (wp[0] + 5, wp[1]), freeze14)
                    print(f"  clr15 {st}")
                break
            data, newc, st = move_wp(sess, data, lead, ld, fr15)
            print(f"  lead+{dx} {lead}->{ld} {st}->{newc}")
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD")
                return
            if st != "moved":
                continue
            fr15, free, me = dump(data, f"after+{dx}")
            if len(free) != 2:
                print("FLOCK BREAK at dx", dx)
                return
            # lag catch same row
            lead = max(free, key=lambda w: w[0])
            lag = min(free, key=lambda w: w[0])
            for ldx in (3, 4, 2, 5):
                gd = (lag[0] + ldx, lag[1])
                if gd[0] >= lead[0] - 4:
                    continue
                if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
                    continue
                data, newc, st = move_wp(sess, data, lag, gd, fr15)
                print(f"  lag+{ldx} {lag}->{gd} {st}")
                if st == "moved":
                    dump(data, "lagok")
                    break
                if st == "dead" or data.get("state") == "GAME_OVER":
                    print("DEAD lag")
                    return
            break
        else:
            # try south+4 instead
            fr15, free, me = dump(data, "tryS")
            lead = max(free, key=lambda w: (w[1], w[0]))
            lag = min(free, key=lambda w: (w[1], w[0]))
            ld = (lead[0], lead[1] + 4)
            if near_any(ld, list(fr15), cheb=5):
                print("S near15")
                break
            data, newc, st = move_wp(sess, data, lead, ld, fr15)
            print(f"  S4 {lead}->{ld} {st}")
            if st == "moved":
                dump(data, "S4ok")
            elif st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD S")
                return
            else:
                break

    dump(data, "END")


if __name__ == "__main__":
    main()
