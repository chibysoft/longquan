"""From (28,44)+(33,40): need cheb>=5 — try S+10 east / south band."""
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


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def to_base(sess, data, do_s3=True):
    data, _ = haul15_toward(sess, data, (34, 57), max_step=6, label="15e")
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
    if do_s3:
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        south = max(free, key=lambda w: (w[1], w[0]))
        data, _, st = move_wp(sess, data, south, (south[0] + 3, south[1]), fr15)
        print("S+3", st)
    return data


def try_moves(sess, data, label, cands):
    known_dead = {
        (34, 46),
        (31, 44),
        (27, 48),
        (36, 48),
        (30, 48),
        (34, 48),
        (30, 50),
        (41, 42),
        (34, 44),
        (18, 48),
        (37, 40),
    }
    fr15, free, me = dump(data, label)
    if len(free) != 2:
        return data, False
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    for who, dx, dy in cands:
        cur = south if who == "S" else north
        other = north if who == "S" else south
        ld = (cur[0] + dx, cur[1] + dy)
        if ld in known_dead:
            print(f"  skip dead {ld}")
            continue
        if cheb(ld, other) < 5:
            print(f"  skip merge {who} {cur}->{ld} cheb={cheb(ld, other)}")
            continue
        if near_any(ld, list(fr15), cheb=5):
            print(f"  skip near15 {ld}")
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        print(f"  {who} {cur}->{ld} {st}->{newc} chebN={cheb(ld, other)}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", ld)
            return data, False
        if st == "moved":
            dump(data, "HIT")
            return data, True
    print("no move")
    return data, False


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3frog5"]},
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

    # Path A: from frog, big S east before S+3
    data_a = to_base(sess, data, do_s3=False)
    print("=== A from frog big S east ===")
    data_a, ok = try_moves(
        sess,
        data_a,
        "Afrog",
        [
            ("S", 13, 0),
            ("S", 10, 0),
            ("S", 8, 0),
            ("S", 15, 0),
            ("S", 12, 0),
            ("S", 6, 2),
            ("S", 8, 2),
            ("S", 4, 4),
            ("S", 0, 4),
            ("S", 2, 4),
            ("N", 5, 0),
            ("N", 8, 0),
            ("N", 2, 0),
            ("N", 0, 4),
            ("N", 2, 4),
            ("N", -2, 0),
        ],
    )
    if ok:
        for i in range(6):
            data_a, ok = try_moves(
                sess,
                data_a,
                f"A{i}",
                [
                    ("S", 4, 0),
                    ("S", 5, 0),
                    ("S", 8, 0),
                    ("S", 10, 0),
                    ("N", 4, 0),
                    ("N", 5, 0),
                    ("S", 4, 2),
                    ("S", 0, 4),
                    ("N", 0, 4),
                    ("S", 2, 4),
                ],
            )
            if not ok:
                break
        dump(data_a, "AEND")
        return

    # Need fresh run for path B — reopen
    print("=== A failed; reopen for B ===")
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3frog5b"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    lv0 = data.get("levels_completed") or 0
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
    data = to_base(sess, data, do_s3=True)
    print("=== B from S+3 big jumps ===")
    data, ok = try_moves(
        sess,
        data,
        "Bbase",
        [
            ("S", 10, 0),
            ("S", 12, 0),
            ("S", 8, 0),
            ("S", 14, 0),
            ("S", 0, 4),
            ("S", 2, 4),
            ("S", 4, 4),
            ("S", 6, 4),
            ("S", 4, 2),
            ("N", 8, 0),
            ("N", 5, 0),
            ("N", 0, 4),
            ("N", 2, 4),
            ("N", -4, 0),
            ("N", -5, 0),
        ],
    )
    if ok:
        for i in range(6):
            data, ok = try_moves(
                sess,
                data,
                f"B{i}",
                [
                    ("S", 4, 0),
                    ("S", 8, 0),
                    ("N", 4, 0),
                    ("S", 0, 4),
                    ("N", 0, 4),
                    ("S", 5, 0),
                ],
            )
            if not ok:
                break
    dump(data, "BEND")


if __name__ == "__main__":
    main()
