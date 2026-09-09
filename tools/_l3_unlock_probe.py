"""At (40,44)+(23,40): haul15 first, then N-catch / S-east past seal."""
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


def setup_to_chain(sess, data, seast_to=40):
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
    data, _, st = move_wp(sess, data, north, (23, 40), fr15)
    print("Nwest", st)
    for x in (32, 36, 40):
        if x > seast_to:
            break
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        south = max(free, key=lambda w: (w[1], w[0]))
        data, _, st = move_wp(sess, data, south, (x, 44), fr15)
        print(f"Seast->{x}", st)
        if st != "moved":
            break
    return data


def try_move(sess, data, cur, ld, other, fr15, label):
    if cheb(ld, other) < 5:
        print(f"  skip merge {label} {ld}")
        return data, False
    if near_any(ld, list(fr15), cheb=5):
        print(f"  skip near15 {label} {ld}")
        return data, False
    data, newc, st = move_wp(sess, data, cur, ld, fr15)
    print(f"  {label} {cur}->{ld} {st}->{newc}")
    if st == "dead" or data.get("state") == "GAME_OVER":
        print("DEAD", ld)
        return data, False
    if st == "moved":
        dump(data, "HIT")
        if len(count_free14(data["frame"], lock_other_ship(data["frame"], 14))) != 2:
            print("FLOCK")
            return data, False
        return data, True
    return data, False


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3unlock"]},
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

    # Stop Seast at 36 to save bud, haul15, then continue
    data = setup_to_chain(sess, data, seast_to=36)
    dump(data, "AT36")

    for h in range(4):
        if step_budget(data["frame"]) < 8:
            break
        data, ok = haul15_toward(sess, data, (34, 57), max_step=8, label=f"15h{h}")
        dump(data, f"H{h}")
        fr15 = lock_other_ship(data["frame"], 14)
        # Can we place S at (40,44) or (44,44) now?
        free = count_free14(data["frame"], fr15)
        if len(free) != 2:
            print("broke")
            return
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
        for ld in ((40, 44), (44, 44), (48, 44), (42, 44), (40, 46)):
            data, ok = try_move(sess, data, south, ld, north, fr15, "S")
            if ok:
                break
            if data.get("state") == "GAME_OVER":
                return
        else:
            continue
        break

    dump(data, "POST")
    for rnd in range(8):
        if step_budget(data["frame"]) < 4:
            print("bud low")
            break
        fr15, free, me = dump(data, f"r{rnd}")
        if len(free) != 2:
            break
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
        # N first
        moved = False
        for ld in (
            (north[0], south[1]),
            (north[0] + 2, south[1]),
            (south[0] - 10, south[1]),
            (south[0] - 8, south[1]),
            (north[0] + 6, north[1]),
            (north[0] + 8, north[1]),
            (40, 36),
            (44, 36),
            (37, 36),
            (south[0] + 4, south[1]),
            (south[0] + 5, south[1]),
            (south[0] + 8, south[1]),
            (48, 44),
            (52, 44),
            (50, 48),
            (55, 44),
            (55, 48),
        ):
            # pick closer wp
            if abs(ld[1] - south[1]) + abs(ld[0] - south[0]) <= abs(ld[1] - north[1]) + abs(
                ld[0] - north[0]
            ):
                cur, other, lab = south, north, "S"
            else:
                cur, other, lab = north, south, "N"
            # force N for y36 targets
            if ld[1] <= 36:
                cur, other, lab = north, south, "N"
            data, ok = try_move(sess, data, cur, ld, other, fr15, lab)
            if data.get("state") == "GAME_OVER":
                return
            if ok:
                moved = True
                break
        if not moved:
            data, _ = haul15_toward(sess, data, (34, 57), max_step=6, label="15more")
            dump(data, "more15")
            if step_budget(data["frame"]) < 4:
                break
            # if still stall
            fr15, free, me = dump(data, "chk")
            if len(free) != 2:
                break
            print("stalled")
            break
    dump(data, "END")


if __name__ == "__main__":
    main()
