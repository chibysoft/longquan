"""At (40,44)+(23,40) bud~14: move 15 SOUTH (not east) to unlock Seast."""
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

DEAD14 = {(27, 40), (28, 40), (38, 44), (35, 44), (37, 40), (38, 40), (42, 48), (41, 48), (34, 46), (31, 44)}


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
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, (south[0] + 3, south[1]), fr15)
    print("S+3", st)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (23, 40), fr15)
    print("Nwest", st)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, (40, 44), fr15)
    print("S40", st)
    return data


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l315s"]},
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
    data = to_at40(sess, data)
    fr15, free, me = dump(data, "AT40")

    freeze14 = lock_other_ship(data["frame"], 15)
    # Try move western 15 wp south / SE
    west15 = min(fr15, key=lambda w: (w[0], w[1]))
    east15 = max(fr15, key=lambda w: (w[0], w[1]))
    print(f"west15={west15} east15={east15}")
    for tgt in (
        (west15[0], west15[1] + 4),
        (west15[0], west15[1] + 6),
        (west15[0] + 2, west15[1] + 4),
        (west15[0] - 2, west15[1] + 4),
        (west15[0] + 4, west15[1] + 4),
        (west15[0], west15[1] + 8),
        (west15[0] + 2, west15[1] + 6),
        (west15[0] + 6, west15[1] + 2),
        (west15[0] + 8, west15[1]),
        (east15[0], east15[1] + 4),
        (east15[0], east15[1] + 6),
        (east15[0] - 4, east15[1] + 4),
    ):
        if not (0 <= tgt[0] < 64 and 0 <= tgt[1] < 64):
            continue
        if near_any(tgt, list(freeze14), cheb=5):
            print(f"  15 near14 {tgt}")
            continue
        other = east15 if tgt != east15 and west15 == west15 else west15
        # avoid merge with other 15
        oth = east15 if (west15[0], west15[1]) == (west15[0], west15[1]) else west15
        # pick which wp we're moving
        cur = west15
        if abs(tgt[0] - east15[0]) + abs(tgt[1] - east15[1]) < abs(tgt[0] - west15[0]) + abs(
            tgt[1] - west15[1]
        ):
            cur = east15
        oth = east15 if cur == west15 else west15
        if cheb(tgt, oth) < 5:
            print(f"  15 merge {tgt}")
            continue
        data, newc, st = move_wp(sess, data, cur, tgt, freeze14)
        print(f"  15 {cur}->{tgt} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("15 DEAD", tgt)
            return
        if st == "moved":
            dump(data, "15OK")
            break
    else:
        print("no 15 south")

    # Now try 14 advances
    for rnd in range(8):
        if step_budget(data["frame"]) < 4:
            print("bud low")
            break
        fr15, free, me = dump(data, f"r{rnd}")
        if len(free) != 2:
            break
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
        moved = False
        for cur, ld, lab in [
            (south, (south[0] + 4, south[1]), "Se"),
            (south, (south[0] + 5, south[1]), "Se"),
            (south, (south[0] + 6, south[1]), "Se"),
            (south, (south[0] + 8, south[1]), "Se"),
            (north, (40, 36), "Ny36"),
            (north, (44, 36), "Ny36"),
            (north, (37, 36), "Ny36"),
            (north, (north[0] + 8, north[1]), "Ne"),
            (north, (north[0] + 10, north[1]), "Ne"),
            (north, (south[0] - 12, south[1]), "Nc"),
            (south, (48, 44), "Sg"),
            (south, (52, 44), "Sg"),
            (south, (55, 44), "Sg"),
        ]:
            if ld in DEAD14:
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
                return
            if st == "moved":
                dump(data, "HIT")
                if len(count_free14(data["frame"], lock_other_ship(data["frame"], 14))) != 2:
                    print("FLOCK")
                    return
                moved = True
                break
        if not moved:
            print("stalled")
            break
    dump(data, "END")


if __name__ == "__main__":
    main()
