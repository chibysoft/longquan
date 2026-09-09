"""Continue from (28,44)+(33,40): pure east / north-east only."""
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


def to_state(sess, data):
    data, _ = haul15_toward(sess, data, (34, 57), max_step=6, label="15e")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print("leadS", st)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    print("frog", st)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, (south[0] + 3, south[1]), fr15)
    print("S+3", st)
    return data


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3frog4"]},
        timeout=90,
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
    data = to_state(sess, data)
    if data.get("state") == "GAME_OVER":
        print("GO")
        return
    fr15, free, me = dump(data, "BASE")
    known_dead = {(34, 46), (31, 44), (27, 48), (36, 48), (30, 48), (34, 48), (30, 50), (41, 42), (34, 44), (18, 48)}

    for rnd in range(10):
        if step_budget(data["frame"]) < 5:
            print("bud low")
            break
        fr15, free, me = dump(data, f"r{rnd}")
        if len(free) != 2:
            print("broke", free)
            break
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
        # Prefer: S pure east, N pure east, then mild SE
        cands = []
        for dx in (2, 3, 4, 5, 6, 8):
            cands.append(("S", south, (south[0] + dx, south[1])))
        for dx in (2, 3, 4, 5):
            cands.append(("N", north, (north[0] + dx, north[1])))
        for dx, dy in ((2, 2), (4, 2), (3, 2), (5, 2), (2, -2), (4, -2)):
            cands.append(("S", south, (south[0] + dx, south[1] + dy)))
        for dx in (2, 4):
            cands.append(("N", north, (north[0] + dx, north[1] + 2)))

        moved = False
        for who, cur, ld in cands:
            if ld in known_dead:
                continue
            other = north if who == "S" else south
            if max(abs(ld[0] - other[0]), abs(ld[1] - other[1])) < 5:
                continue
            if near_any(ld, list(fr15), cheb=5):
                continue
            data, newc, st = move_wp(sess, data, cur, ld, fr15)
            print(f"  {who} {cur}->{ld} {st}->{newc}")
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD", ld)
                known_dead.add(ld)
                return
            if st == "moved":
                dump(data, "HIT")
                moved = True
                break
        if not moved:
            print("stalled")
            break
    dump(data, "END")


if __name__ == "__main__":
    main()
