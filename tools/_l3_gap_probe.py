"""From (28,44)+(33,40): N-west to open gap, then S-east; also clear15 south."""
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
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me['c']} d14={d14} free14={sorted(free)} n={len(free)} "
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}"
    )
    return fr15, free, me


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def to_s3(sess, data):
    data, _ = haul15_toward(sess, data, (34, 57), max_step=4, label="15soft")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
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
    data, _, st = move_wp(sess, data, south, (south[0] + 3, south[1]), fr15)
    print("S+3", st)
    return data


def try_one(sess, data, who, cur, ld, other, fr15):
    if cheb(ld, other) < 5:
        print(f"  skip merge {who} {ld} cheb={cheb(ld, other)}")
        return data, False
    if near_any(ld, list(fr15), cheb=5):
        print(f"  skip near15 {ld}")
        return data, False
    data, newc, st = move_wp(sess, data, cur, ld, fr15)
    print(f"  {who} {cur}->{ld} {st}->{newc}")
    if st == "dead" or data.get("state") == "GAME_OVER":
        print("DEAD", ld)
        return data, False
    if st == "moved":
        dump(data, "HIT")
        n = len(count_free14(data["frame"], lock_other_ship(data["frame"], 14)))
        if n != 2:
            print("FLOCK", n)
            return data, False
        return data, True
    return data, False


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3gap"]},
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
    data = to_s3(sess, data)
    fr15, free, me = dump(data, "BASE")

    # Phase1: pull N west/south to open gap for S east
    plans = [
        ("N", -5, 0),
        ("N", -8, 0),
        ("N", -4, 0),
        ("N", -6, 0),
        ("N", -3, 0),
        ("N", -5, 2),
        ("N", -2, 4),
        ("N", 0, 4),
        ("N", 2, 4),
        ("S", 10, 0),
        ("S", 12, 0),
        ("S", 8, 0),
        ("S", 0, 4),
        ("S", 4, 4),
        ("S", 2, 2),
    ]
    for rnd in range(8):
        if step_budget(data["frame"]) < 5:
            print("bud low")
            break
        fr15, free, me = dump(data, f"r{rnd}")
        if len(free) != 2:
            break
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
        moved = False
        for who, dx, dy in plans:
            cur = south if who == "S" else north
            other = north if who == "S" else south
            ld = (cur[0] + dx, cur[1] + dy)
            data, ok = try_one(sess, data, who, cur, ld, other, fr15)
            if data.get("state") == "GAME_OVER" or ("frame" in data and False):
                return
            # detect DEAD from print path — check state
            if "frame" not in data or data.get("state") == "GAME_OVER":
                return
            # if last move was dead, move_wp keeps frame usually
            if ok:
                moved = True
                break
            # if dead, stop
            fr15b = lock_other_ship(data["frame"], 14)
            if len(count_free14(data["frame"], fr15b)) < 2 and step_budget(data["frame"]) < 3:
                return
        if not moved:
            # try haul15 south more to unlock
            print("try haul15 more")
            data, _ = haul15_toward(sess, data, (34, 57), max_step=8, label="15more")
            dump(data, "after15")
            # try lead to (37,36) style — pick north back to y36 east
            fr15, free, me = dump(data, "retry")
            if len(free) != 2:
                break
            south = max(free, key=lambda w: (w[1], w[0]))
            north = min(free, key=lambda w: (w[1], w[0]))
            for ld in (
                (north[0] + 4, 36),
                (37, 36),
                (40, 36),
                (north[0] + 4, north[1]),
                (south[0] + 10, south[1]),
            ):
                # which wp is closer to ld?
                cur = north if abs(north[1] - ld[1]) <= abs(south[1] - ld[1]) else south
                other = south if cur == north else north
                data, ok = try_one(sess, data, "X", cur, ld, other, fr15)
                if ok:
                    moved = True
                    break
                if data.get("state") == "GAME_OVER":
                    return
            if not moved:
                print("stalled")
                break
    dump(data, "END")


if __name__ == "__main__":
    main()
