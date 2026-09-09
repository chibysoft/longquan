"""Move only seal wp (41,40) east, then try translate2 dx=2/3."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east, translate2_nudge
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, lock_other_ship, near_any
from tools.r11l_seated_clear import clear_l1, reset


def dump(data, label):
    wps = [w["c"] for w in r11l.waypoints(data["frame"])]
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    print(f"{label} ships={ships(data['frame'])} wps={wps} freeze15={fr15} free={free} bud={step_budget(data['frame'])}")
    return fr15, free


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3seal"]},
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
    fr15, free = dump(data, "GATE")

    # Only move western seal (41,40) → (48,40) or (50,40)
    freeze14 = lock_other_ship(data["frame"], 15)
    seal = min(fr15, key=lambda w: w[0])
    for dest in ((48, 40), (50, 40), (46, 40), (48, 42), (52, 40)):
        if near_any(dest, freeze14, cheb=5):
            continue
        data, newc, st = move_wp(sess, data, seal, dest, freeze14)
        print(f"seal {seal}->{dest} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD")
            return
        if st == "moved":
            break
    fr15, free = dump(data, "UNSEALED")

    for dx in (2, 3, 4):
        # refresh freeze each attempt; stop if flock broken
        fr15, free = dump(data, f"try dx={dx}")
        if len(free) != 2:
            print("already broken")
            return
        data, ok = translate2_nudge(sess, data, fr15, lead_dx=dx)
        dump(data, f"after dx={dx} ok={ok}")
        if data.get("state") == "GAME_OVER":
            print("GO")
            return
        if ok:
            me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            print(f"SUCCESS dx={dx} ship={me['c']} d14={abs(me['c'][0]-55)+abs(me['c'][1]-53)}")
            # try another round
            fr15 = lock_other_ship(data["frame"], 14)
            data, ok2 = translate2_nudge(sess, data, fr15, lead_dx=2)
            dump(data, f"round2 ok={ok2}")
            return
    print("all dx failed")


if __name__ == "__main__":
    main()
