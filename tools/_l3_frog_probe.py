"""After lead S4 to y40: lag leapfrog to y44 (past lead), then swap roles."""
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


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3frog"]},
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
    data, _ = haul15_toward(sess, data, (34, 57), max_step=6, label="15e")
    fr15, free, me = dump(data, "GATE")
    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])

    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print(f"leadS {st}")
    fr15, free, me = dump(data, "afterLead")
    if len(free) != 2:
        return
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))

    # Leapfrog lag past lead
    for gd in (
        (lag[0] + 2, lead[1] + 4),  # (25,44)
        (lag[0], lead[1] + 4),
        (lag[0] + 4, lead[1] + 4),
        (lag[0] + 2, lead[1] + 6),
        (lag[0] + 2, 44),
        (25, 44),
        (22, 44),
        (20, 44),
        (28, 44),
        (24, 48),
    ):
        if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
            print("skip cheb", gd)
            continue
        if near_any(gd, list(fr15), cheb=5):
            print("skip 15", gd)
            continue
        data, newc, st = move_wp(sess, data, lag, gd, fr15)
        print(f"  frog {lag}->{gd} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD")
            return
        if st == "moved":
            fr15, free, me = dump(data, "FROG")
            break
    else:
        print("no frog")
        dump(data, "END")
        return

    if len(free) != 2:
        print("broke")
        return

    # Now the southern wp is the new lead — advance it, then old lead catches
    for rnd in range(4):
        if step_budget(data["frame"]) < 8:
            break
        fr15, free, me = dump(data, f"r{rnd}")
        if len(free) != 2:
            break
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
        # advance south wp further
        for ld in (
            (south[0], south[1] + 4),
            (south[0] + 2, south[1] + 4),
            (south[0] + 4, south[1]),
            (south[0] + 4, south[1] + 2),
        ):
            if max(abs(ld[0] - north[0]), abs(ld[1] - north[1])) < 5:
                continue
            if near_any(ld, list(fr15), cheb=5):
                continue
            data, newc, st = move_wp(sess, data, south, ld, fr15)
            print(f"  S {south}->{ld} {st}")
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD S")
                return
            if st == "moved":
                dump(data, "Sok")
                break
        else:
            # catch north toward south
            for gd in (
                (north[0], north[1] + 4),
                (north[0] + 2, north[1] + 4),
                (south[0] - 5, south[1]),
            ):
                if max(abs(gd[0] - south[0]), abs(gd[1] - south[1])) < 5:
                    continue
                data, newc, st = move_wp(sess, data, north, gd, fr15)
                print(f"  N {north}->{gd} {st}")
                if st == "moved":
                    dump(data, "Nok")
                    break
                if st == "dead" or data.get("state") == "GAME_OVER":
                    print("DEAD N")
                    return
            else:
                break
    dump(data, "END")


if __name__ == "__main__":
    main()
