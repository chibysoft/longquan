"""Staggered south: lead+4, lag catch only partway (keep dy>=2), repeat."""
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
        json={"tags": ["r11l_l3stag"]},
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

    for rnd in range(6):
        if step_budget(data["frame"]) < 8:
            print("bud low")
            break
        fr15, free, me = dump(data, f"r{rnd}")
        if len(free) != 2:
            print("broke")
            break
        lead = max(free, key=lambda w: (w[1], w[0]))
        lag = min(free, key=lambda w: (w[1], w[0]))
        dy = lead[1] - lag[1]

        # Lead south+4 first when same-row (gate) OR when dy in 1..3.
        # NEVER fully catch lag to dy=0 then lead again (eats flock).
        if dy == 0 and lead[1] <= 38:
            # Opening south leap from corridor
            pass  # fall through to leadS
        elif dy < 1:
            print("deep-aligned — stop before flock eat")
            break
        elif dy >= 4:
            target_y = lead[1] - 2
            for gd in (
                (lag[0] + 2, target_y),
                (lag[0] + 4, target_y),
                (lag[0], target_y),
                (lead[0] - 6, target_y),
                (lag[0] + 2, lag[1] + 4),
            ):
                if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
                    continue
                if near_any(gd, list(fr15), cheb=5):
                    continue
                data, newc, st = move_wp(sess, data, lag, gd, fr15)
                print(f"  partialG {lag}->{gd} {st}->{newc}")
                if st == "dead" or data.get("state") == "GAME_OVER":
                    print("DEAD G")
                    return
                if st == "moved":
                    dump(data, "partial")
                    break
            continue

        # Lead advance south+4
        for ld in (
            (lead[0], lead[1] + 4),
            (lead[0] + 2, lead[1] + 4),
            (lead[0] - 2, lead[1] + 4),
            (lead[0] + 4, lead[1] + 2),
        ):
            if near_any(ld, list(fr15), cheb=5):
                print(f"  near15 {ld}")
                continue
            if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
                continue
            data, newc, st = move_wp(sess, data, lead, ld, fr15)
            print(f"  leadS {lead}->{ld} {st}->{newc}")
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD L")
                return
            if st == "moved":
                fr15, free, me = dump(data, "leadHIT")
                if len(free) != 2:
                    print("FLOCK BREAK")
                    return
                break
        else:
            print("lead stuck")
            break

    dump(data, "END")


if __name__ == "__main__":
    main()
