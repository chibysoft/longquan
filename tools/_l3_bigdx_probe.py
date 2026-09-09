"""From collapse: one big translate (+5/+6/+7) then lag; dump flock."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import collapse_to_2, translate2_nudge, west_to_neck, _install_reshape_cap3
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, lock_other_ship, near_any
from tools.r11l_seated_clear import clear_l1, reset


def dump(data, label):
    wps = [w["c"] for w in r11l.waypoints(data["frame"])]
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    print(f"{label} ship={me['c']} d14={abs(me['c'][0]-55)+abs(me['c'][1]-53)} wps={wps} free={free} fr15={fr15} bud={step_budget(data['frame'])}")
    return fr15, free


def setup_collapse(sess):
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    lv0 = data.get("levels_completed") or 0
    _install_reshape_cap3()
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    freeze15 = lock_other_ship(data["frame"], 14)
    data, _ = west_to_neck(sess, data, freeze15, lv0)
    freeze15 = lock_other_ship(data["frame"], 14)
    data, _ = collapse_to_2(sess, data, freeze15)
    # unseal
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = lock_other_ship(data["frame"], 14)
    seal = min(fr15, key=lambda w: w[0])
    for dest in ((45, 40), (44, 40), (46, 42)):
        data, newc, st = move_wp(sess, data, seal, dest, freeze14)
        print(f"seal {seal}->{dest} {st}")
        if st == "moved":
            break
        if st == "dead" or data.get("state") == "GAME_OVER":
            return data, False
    return data, True


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3bigdx"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"

    # Try each dx in separate... can't reset easily mid-script without full rerun.
    # Do sequential: collapse once, try dx=5 (known gate), then from there try south along clearance.
    data, ok = setup_collapse(sess)
    if not ok or data.get("state") == "GAME_OVER":
        print("setup fail")
        return
    fr15, free = dump(data, "START")

    for dx in (5, 6, 4, 7):
        fr15, free = dump(data, f"before dx={dx}")
        if len(free) != 2:
            print("broken before")
            break
        data, ok = translate2_nudge(sess, data, fr15, lead_dx=dx)
        fr15, free = dump(data, f"after dx={dx} ok={ok}")
        if data.get("state") == "GAME_OVER":
            print("GO")
            return
        if ok:
            me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            print(f"OK dx={dx} ship={me['c']}")
            # Now stuck for second translate — try SE/south from here toward clearance bend
            lead = max(free, key=lambda w: w[0])
            lag = min(free, key=lambda w: w[0])
            for ld in (
                (lead[0] + 2, lead[1] + 2),
                (lead[0], lead[1] + 4),
                (lead[0] + 4, lead[1] + 2),
                (lead[0] + 6, lead[1]),
                (min(50, lead[0] + 8), lead[1]),
                (lead[0] + 2, lead[1] + 6),
                (36, 42),
                (40, 40),
                (42, 42),
            ):
                if step_budget(data["frame"]) < 6:
                    break
                fr15, free = dump(data, "se-try")
                if len(free) < 2:
                    break
                lead = max(free, key=lambda w: (w[0], w[1]))
                lag = min(free, key=lambda w: (w[0], w[1]))
                if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
                    continue
                if near_any(ld, list(fr15), cheb=5):
                    print(f"  near15 {ld}")
                    continue
                data, newc, st = move_wp(sess, data, lead, ld, fr15)
                print(f"  SE {lead}->{ld} {st}->{newc}")
                if st == "dead" or data.get("state") == "GAME_OVER":
                    print("DEAD", ld)
                    return
                if st == "moved":
                    dump(data, "SE-HIT")
                    break
            break
        # if flock broke, stop
        if len(free) < 2:
            print("flock gone")
            # try 1wp haul along clearance
            if free:
                wp = free[0]
                for dest in ((45, 36), (50, 36), (55, 40), (55, 46), (55, 50), (55, 53)):
                    if step_budget(data["frame"]) < 5:
                        break
                    data, newc, st = move_wp(sess, data, wp, dest, [])
                    print(f"  1wp {wp}->{dest} {st}->{newc} ship={ships(data['frame'])}")
                    if st == "moved":
                        wp = newc
                        dump(data, "1wp")
                    if st == "dead" or data.get("state") == "GAME_OVER":
                        print("DEAD 1wp")
                        return
            break


if __name__ == "__main__":
    main()
