"""Continue from N-west + S-east chain at (40,44)+(23,40)."""
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

KNOWN_DEAD = {
    (28, 40),
    (35, 44),
    (37, 40),
    (38, 40),
    (34, 46),
    (31, 44),
    (41, 48),
    (27, 48),
    (36, 48),
    (30, 48),
    (34, 48),
    (40, 44),  # wait — we LANDED on (40,44) successfully as destination; not dead cell for dest
}


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(
        f"{label} ship={me['c']} d14={d14} free={sorted(free)} n={len(free)} "
        f"bud={step_budget(data['frame'])}"
    )
    return fr15, free, me


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def setup(sess, data):
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
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (23, 40), fr15)
    print("Nwest", st)
    for tgt in ((32, 44), (36, 44), (40, 44)):
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        south = max(free, key=lambda w: (w[1], w[0]))
        data, _, st = move_wp(sess, data, south, tgt, fr15)
        print(f"Seast->{tgt}", st)
        if st != "moved":
            break
    return data


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3chain"]},
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
    data = setup(sess, data)
    if data.get("state") == "GAME_OVER":
        print("GO setup")
        return
    dump(data, "CHAIN")

    dead = {(28, 40), (35, 44), (37, 40), (38, 40), (34, 46), (31, 44), (41, 48), (27, 48), (36, 48)}

    for rnd in range(10):
        if step_budget(data["frame"]) < 4:
            print("bud low")
            break
        fr15, free, me = dump(data, f"r{rnd}")
        if len(free) != 2:
            print("broke", free)
            break
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
        cands = [
            ("S", south, (south[0] + 4, south[1])),
            ("S", south, (south[0] + 5, south[1])),
            ("S", south, (south[0] + 6, south[1])),
            ("S", south, (south[0] + 8, south[1])),
            ("S", south, (south[0] + 4, south[1] + 2)),
            ("S", south, (south[0] + 2, south[1] + 4)),
            ("S", south, (south[0], south[1] + 4)),
            ("S", south, (south[0] + 4, south[1] + 4)),
            # N catch: same row as south but west, or mid
            ("N", north, (north[0], south[1])),
            ("N", north, (north[0] + 2, south[1])),
            ("N", north, (south[0] - 8, south[1])),
            ("N", north, (south[0] - 10, south[1])),
            ("N", north, (north[0] + 4, north[1])),
            ("N", north, (north[0] + 6, north[1])),
            ("N", north, (north[0] + 8, north[1])),
            ("N", north, (north[0] + 2, north[1] + 2)),
            ("N", north, (37, 36)),
            ("N", north, (40, 36)),
            ("N", north, (north[0] + 4, 36)),
            ("S", south, (44, 48)),
            ("S", south, (48, 44)),
            ("S", south, (50, 44)),
            ("S", south, (52, 48)),
            ("S", south, (55, 44)),
        ]
        moved = False
        for who, cur, ld in cands:
            if ld in dead:
                continue
            other = north if who == "S" else south
            if cheb(ld, other) < 5:
                continue
            if near_any(ld, list(fr15), cheb=5):
                print(f"  near15 {ld}")
                continue
            data, newc, st = move_wp(sess, data, cur, ld, fr15)
            print(f"  {who} {cur}->{ld} {st}->{newc}")
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD", ld)
                dead.add(ld)
                return
            if st == "moved":
                n = len(count_free14(data["frame"], lock_other_ship(data["frame"], 14)))
                dump(data, "HIT")
                if n != 2:
                    print("FLOCK", n)
                    return
                moved = True
                break
        if not moved:
            print("stalled — haul15")
            data, _ = haul15_toward(sess, data, (34, 57), max_step=6, label="15c")
            dump(data, "after15")
            # one more try N to y36 east
            fr15, free, me = dump(data, "retry")
            if len(free) != 2:
                break
            north = min(free, key=lambda w: (w[1], w[0]))
            south = max(free, key=lambda w: (w[1], w[0]))
            for ld in ((40, 36), (44, 36), (37, 36), (48, 36)):
                if cheb(ld, south) < 5 or near_any(ld, list(fr15), cheb=5):
                    continue
                data, newc, st = move_wp(sess, data, north, ld, fr15)
                print(f"  Ny36 {north}->{ld} {st}")
                if st == "dead" or data.get("state") == "GAME_OVER":
                    print("DEAD", ld)
                    return
                if st == "moved":
                    dump(data, "HIT36")
                    moved = True
                    break
            if not moved:
                print("hard stall")
                break
    dump(data, "END")


if __name__ == "__main__":
    main()
