"""At AT40: 15 east-unlock; also try N→(40,36). Fresh card each major branch."""
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

DEAD = {(27, 40), (28, 40), (38, 44), (45, 47), (35, 44), (37, 40), (38, 40), (42, 48), (41, 48)}


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


def boot(tag):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": [tag]},
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
    return sess, data


def to_at40(sess, data):
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
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, s, (s[0] + 3, s[1]), fr15)
    print("S+3", st)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (23, 40), fr15)
    print("Nwest", st)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, s, (40, 44), fr15)
    print("S40", st)
    return data


def try14(sess, data, rounds=8):
    for rnd in range(rounds):
        if step_budget(data["frame"]) < 4:
            print("bud low")
            break
        fr15, free, me = dump(data, f"r{rnd}")
        if len(free) != 2:
            break
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
        moved = False
        trials = [
            (south, (south[0] + 4, south[1]), "Se"),
            (south, (south[0] + 5, south[1]), "Se"),
            (south, (south[0] + 6, south[1]), "Se"),
            (south, (south[0] + 8, south[1]), "Se"),
            (north, (40, 36), "Ny36"),
            (north, (44, 36), "Ny36"),
            (north, (37, 36), "Ny36"),
            (north, (48, 36), "Ny36"),
            (north, (north[0] + 10, north[1]), "Ne"),
            (north, (north[0] + 12, north[1]), "Ne"),
            (north, (south[0] - 12, south[1]), "Nc"),
            (south, (48, 44), "Sg"),
            (south, (52, 44), "Sg"),
            (south, (55, 44), "Sg"),
            (south, (55, 48), "Sg"),
        ]
        for cur, ld, lab in trials:
            if ld in DEAD:
                continue
            other = north if cur == south else south
            if cheb(ld, other) < 5:
                continue
            if near_any(ld, list(fr15), cheb=5):
                print(f"  near15 {ld}")
                continue
            data, newc, st = move_wp(sess, data, cur, ld, fr15)
            print(f"  {lab} {cur}->{ld} {st}->{newc}")
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD", ld)
                DEAD.add(ld)
                return data
            if st == "moved":
                dump(data, "HIT")
                if len(count_free14(data["frame"], lock_other_ship(data["frame"], 14))) != 2:
                    print("FLOCK")
                    return data
                moved = True
                break
        if not moved:
            print("stalled")
            break
    dump(data, "END")
    return data


def main():
    print("=== A: 15 east unlock ===")
    sess, data = boot("r11l_l3uA")
    data = to_at40(sess, data)
    dump(data, "AT40")
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = lock_other_ship(data["frame"], 14)
    west15 = min(fr15, key=lambda w: w[0])
    east15 = max(fr15, key=lambda w: w[0])
    for tgt in (
        (west15[0] + 6, west15[1]),
        (west15[0] + 8, west15[1]),
        (west15[0] + 4, west15[1]),
        (west15[0] + 10, west15[1]),
        (west15[0] + 6, west15[1] + 2),
        (51, 41),
        (52, 41),
        (49, 41),
    ):
        if cheb(tgt, east15) < 5:
            continue
        if near_any(tgt, list(freeze14), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, west15, tgt, freeze14)
        print(f"  15e {west15}->{tgt} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("15 DEAD")
            break
        if st == "moved":
            dump(data, "15OK")
            break
    try14(sess, data)

    print("=== B: N to y36 first (no 15 move) ===")
    sess, data = boot("r11l_l3uB")
    data = to_at40(sess, data)
    dump(data, "AT40b")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    for ld in ((40, 36), (44, 36), (37, 36), (36, 36), (48, 36), (32, 36), (40, 38)):
        if cheb(ld, south) < 5 or near_any(ld, list(fr15), cheb=5) or ld in DEAD:
            print(f"  skip {ld} cheb={cheb(ld, south)} near={near_any(ld, list(fr15), cheb=5)}")
            continue
        data, newc, st = move_wp(sess, data, north, ld, fr15)
        print(f"  Ny {north}->{ld} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", ld)
            break
        if st == "moved":
            dump(data, "NyHIT")
            try14(sess, data)
            break
    else:
        print("Ny none")
        dump(data, "BEND")


if __name__ == "__main__":
    main()
