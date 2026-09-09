"""From frog state (33,40)/(25,44): safe advances toward (55,53)."""
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


def to_frog(sess, data):
    data, _ = haul15_toward(sess, data, (34, 57), max_step=6, label="15e")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print("leadS", st)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    print("frog", st)
    return data, st == "moved"


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3frog2"]},
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
    data, ok = to_frog(sess, data)
    if data.get("state") == "GAME_OVER":
        print("GO setup")
        return
    fr15, free, me = dump(data, "FROG")
    if len(free) != 2:
        return

    # Avoid known dead (27,48). Try east on y44, catch north to y44, SE soft.
    cands_south = []  # south wp moves
    cands_north = []
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    for dx, dy in (
        (4, 0), (5, 0), (6, 0), (3, 0), (8, 0),
        (4, 2), (2, 2), (0, 2), (-2, 2),
        (4, -2), (2, 4), (6, 2),
        (0, 4),  # careful
    ):
        cands_south.append((south[0] + dx, south[1] + dy))
    for dx, dy in (
        (0, 4), (-2, 4), (2, 4), (0, 2),
        (-4, 4), (2, 0), (-2, 0),
    ):
        cands_north.append((north[0] + dx, north[1] + dy))

    for rnd in range(8):
        if step_budget(data["frame"]) < 6:
            print("bud low")
            break
        fr15, free, me = dump(data, f"r{rnd}")
        if len(free) != 2:
            print("broke")
            break
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
        moved = False
        # Prefer catching north to same y as south first (frog style invert)
        if south[1] - north[1] >= 3:
            for gd in (
                (north[0], south[1]),
                (north[0] - 2, south[1]),
                (north[0] + 2, south[1]),
                (south[0] - 5, south[1]),
                (north[0], north[1] + 4),
            ):
                if max(abs(gd[0] - south[0]), abs(gd[1] - south[1])) < 5:
                    continue
                if near_any(gd, list(fr15), cheb=5):
                    continue
                data, newc, st = move_wp(sess, data, north, gd, fr15)
                print(f"  N {north}->{gd} {st}->{newc}")
                if st == "dead" or data.get("state") == "GAME_OVER":
                    print("DEAD N", gd)
                    return
                if st == "moved":
                    dump(data, "Nhit")
                    moved = True
                    break
            if moved:
                continue

        # Advance south wp east toward goal
        for ld in (
            (south[0] + 4, south[1]),
            (south[0] + 5, south[1]),
            (south[0] + 6, south[1]),
            (south[0] + 3, south[1]),
            (south[0] + 4, south[1] + 2),
            (south[0] + 2, south[1] + 2),
            (south[0] + 6, south[1] + 2),
            (south[0], south[1] + 2),
        ):
            if max(abs(ld[0] - north[0]), abs(ld[1] - north[1])) < 5:
                continue
            if near_any(ld, list(fr15), cheb=5):
                print(f"  near15 {ld}")
                continue
            data, newc, st = move_wp(sess, data, south, ld, fr15)
            print(f"  S {south}->{ld} {st}->{newc}")
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD S", ld)
                return
            if st == "moved":
                fr15, free, me = dump(data, "Shit")
                if len(free) != 2:
                    print("FLOCK BREAK")
                    return
                moved = True
                break
        if not moved:
            print("stalled")
            break
    dump(data, "END")


if __name__ == "__main__":
    main()
