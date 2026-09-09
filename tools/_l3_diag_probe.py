"""From N438 (no swing): try diagonals; also probe 15 deeper south first."""
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

BAD = {(42, 40), (42, 42), (42, 46), (44, 36), (45, 36), (48, 36)}


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(
        f"{label} ship={me['c']} d14={d14} free={sorted(free)} n={len(free)} "
        f"fr15={sorted(fr15)} bud={step_budget(data['frame'])}"
    )
    return fr15, free, me


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def deep15(sess, data, extra_south=False):
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    print("east15", st)
    if st == "dead":
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    west15 = min(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
    data, _, st = move_wp(sess, data, west15, (48, 42), freeze14)
    print("west15", st)
    if st != "moved":
        return data, False
    if extra_south:
        freeze14 = lock_other_ship(data["frame"], 15)
        west15 = min(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
        east15 = max(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
        for tgt in ((48, 48), (50, 48), (48, 46), (50, 46), (52, 48), (46, 48)):
            if cheb(tgt, east15) < 5 or near_any(tgt, list(freeze14), cheb=5):
                continue
            data, newc, st = move_wp(sess, data, west15, tgt, freeze14)
            print(f"  15s {west15}->{tgt} {st}->{newc}")
            if st == "dead":
                print("15s DEAD")
                return data, False
            if st == "moved":
                break
    return data, True


def frog_to_n438(sess, data):
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
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (40, 36), fr15)
    print("Ny36", st)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, s, (40, 44), fr15)
    print("S40", st)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (43, 38), fr15)
    print("N438", st)
    return data, st == "moved"


def try_continues(sess, data):
    dump(data, "CONT")
    for rnd in range(8):
        if step_budget(data["frame"]) < 4:
            print("bud low")
            break
        fr15, free, me = dump(data, f"r{rnd}")
        if len(free) != 2:
            break
        s = max(free, key=lambda w: (w[1], w[0]))
        n = min(free, key=lambda w: (w[1], w[0]))
        trials = [
            (s, (42, 44), "S42"),
            (s, (43, 44), "S43"),
            (s, (41, 44), "S41"),
            (s, (42, 45), "S425"),
            (s, (40, 45), "S045"),
            (n, (45, 40), "N450"),
            (n, (46, 38), "N468"),
            (n, (44, 40), "N440"),
            (n, (45, 38), "N458"),
            (n, (46, 40), "N460"),
            (n, (44, 39), "N449"),
            (n, (45, 39), "N459"),
            (s, (s[0] + 4, s[1]), "Se4"),
            (n, (n[0] + 3, n[1]), "Ne3"),
            (s, (44, 46), "S446"),
            (s, (46, 44), "S464"),
        ]
        moved = False
        for cur, ld, lab in trials:
            if ld in BAD or ld == cur:
                continue
            other = s if cur == n else n
            if cheb(ld, other) < 5:
                print(f"  merge {ld}")
                continue
            if near_any(ld, list(fr15), cheb=5):
                print(f"  near15 {ld}")
                continue
            if ld[1] <= 36 and ld[0] >= 45:
                continue
            data, newc, st = move_wp(sess, data, cur, ld, fr15)
            print(f"  {lab} {cur}->{ld} {st}->{newc}")
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD", ld)
                return data
            if st == "moved":
                dump(data, "HIT")
                moved = True
                break
        if not moved:
            print("stalled")
            break
    dump(data, "END")
    return data


def main():
    print("=== A: N438 continues ===")
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3diagA"]},
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
    data, ok = deep15(sess, data, False)
    if not ok:
        return
    data, ok = frog_to_n438(sess, data)
    if not ok:
        return
    try_continues(sess, data)

    print("=== B: deeper 15 south then frog ===")
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3diagB"]},
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
    data, ok = deep15(sess, data, True)
    if not ok or data.get("state") == "GAME_OVER":
        print("B 15 fail")
        return
    dump(data, "B15")
    data, ok = frog_to_n438(sess, data)
    dump(data, "B438")
    if ok:
        try_continues(sess, data)


if __name__ == "__main__":
    main()
