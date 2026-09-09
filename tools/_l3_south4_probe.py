"""After gate: lead south+4 to y40 (HIT), catch lag, continue SE/east."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east, translate2_nudge
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, lock_other_ship, near_any, haul15_toward
from tools.r11l_seated_clear import clear_l1, reset


def dump(data, label):
    wps = [w["c"] for w in r11l.waypoints(data["frame"])]
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(f"{label} ship={me['c']} d14={d14} free={free} wps={wps} fr15={fr15} bud={step_budget(data['frame'])}")
    return fr15, free, me


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3s4"]},
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
    # soft unseal
    data, _ = haul15_toward(sess, data, (34, 57), max_step=6, label="15e")
    fr15, free, me = dump(data, "GATE")

    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])
    # Proven: +4 south
    data, newc, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print(f"leadS4 {lead}->{lead[0], lead[1]+4} {st}->{newc}")
    if st != "moved":
        print("leadS4 failed", st)
        return
    fr15, free, me = dump(data, "afterS4")
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))

    # Catch lag south/east toward lead y
    for gd in (
        (lag[0] + 2, lead[1]),
        (lag[0] + 4, lead[1]),
        (lag[0], lead[1]),
        (lag[0] + 2, lag[1] + 4),
        (lag[0] + 4, lag[1] + 4),
        (lead[0] - 6, lead[1]),
        (lead[0] - 5, lead[1]),
    ):
        if step_budget(data["frame"]) < 6:
            break
        if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
            continue
        if near_any(gd, list(fr15), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, lag, gd, fr15)
        print(f"  catch {lag}->{gd} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD catch")
            return
        if st == "moved":
            fr15, free, me = dump(data, "catchHIT")
            lag = min(free, key=lambda w: (w[1], w[0])) if len(free) >= 2 else lag
            lead = max(free, key=lambda w: (w[1], w[0])) if len(free) >= 2 else lead
            if lead[1] - lag[1] <= 1:
                break

    fr15, free, me = dump(data, "ALIGNED")
    if len(free) != 2:
        print("need 2")
        return
    lead = max(free, key=lambda w: (w[0], w[1]))
    lag = min(free, key=lambda w: (w[0], w[1]))

    # Continue: east at y40, or more south+4, or SE
    for ld in (
        (lead[0] + 4, lead[1]),
        (lead[0] + 5, lead[1]),
        (lead[0] + 6, lead[1]),
        (lead[0], lead[1] + 4),
        (lead[0] + 2, lead[1] + 4),
        (lead[0] + 4, lead[1] + 4),
        (lead[0] + 6, lead[1] + 2),
        (40, lead[1]),
        (42, lead[1]),
        (45, lead[1]),
        (lead[0], lead[1] + 6),
        (36, 44),
        (38, 44),
        (40, 44),
    ):
        if step_budget(data["frame"]) < 6:
            print("bud low")
            break
        fr15, free, me = dump(data, "cont")
        if len(free) != 2:
            print("broke", free)
            break
        lead = max(free, key=lambda w: (w[0], w[1]))
        lag = min(free, key=lambda w: (w[0], w[1]))
        if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
            continue
        if near_any(ld, list(fr15), cheb=5):
            print(f"  near15 {ld}")
            continue
        data, newc, st = move_wp(sess, data, lead, ld, fr15)
        print(f"  L {lead}->{ld} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", ld)
            return
        if st == "moved":
            fr15, free, me = dump(data, "HIT")
            # one lag catch attempt
            if len(free) == 2:
                lead = max(free, key=lambda w: (w[1], w[0]))
                lag = min(free, key=lambda w: (w[1], w[0]))
                for gd in ((lag[0] + 4, lead[1]), (lag[0] + 2, lead[1]), (lead[0] - 6, lead[1])):
                    if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
                        continue
                    data, newc, st = move_wp(sess, data, lag, gd, fr15)
                    print(f"  G {lag}->{gd} {st}")
                    if st == "moved":
                        dump(data, "G-HIT")
                        break
                    if st == "dead" or data.get("state") == "GAME_OVER":
                        print("DEAD G")
                        return
            # don't break — keep trying more lead moves from new state
            continue

    dump(data, "END")


if __name__ == "__main__":
    main()
