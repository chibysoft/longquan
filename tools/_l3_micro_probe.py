"""From STACK (40,36)+(40,44): safe micro east / south column."""
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

# Import stack builder
from tools._l3_stack2_probe import to_stack, dump, cheb, DEAD

DEAD2 = DEAD | {(45, 36), (52, 44), (45, 47)}


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3micro"]},
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
    data, ok = to_stack(sess, data)
    dump(data, "STACK")
    if not ok:
        return

    # Exhaustive small candidates once
    fr15, free, me = dump(data, "try")
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    cands = []
    for dx in range(1, 9):
        cands.append(("N", north, (north[0] + dx, north[1])))
        cands.append(("S", south, (south[0] + dx, south[1])))
    for dy in (2, 4, 6, 8):
        cands.append(("S", south, (south[0], south[1] + dy)))
        cands.append(("N", north, (north[0], north[1] + dy)))
    for dx, dy in ((2, 2), (4, 2), (2, 4), (4, 4), (6, 2), (2, -2), (4, -2)):
        cands.append(("N", north, (north[0] + dx, north[1] + dy)))
        cands.append(("S", south, (south[0] + dx, south[1] + dy)))
    # also absolute
    for t in ((42, 36), (43, 36), (44, 36), (42, 44), (43, 44), (44, 44), (40, 48), (40, 50), (42, 48), (48, 40)):
        cur = north if abs(t[1] - north[1]) <= abs(t[1] - south[1]) else south
        cands.append(("X", cur, t))

    seen = set()
    for who, cur, ld in cands:
        if ld in seen or ld in DEAD2:
            continue
        seen.add(ld)
        other = south if cur == north else north
        if cheb(ld, other) < 5:
            continue
        if near_any(ld, list(fr15), cheb=5):
            print(f"  near15 {ld}")
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        print(f"  {who} {cur}->{ld} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", ld)
            DEAD2.add(ld)
            # reboot is expensive — stop
            return
        if st == "moved":
            dump(data, "HIT")
            # continue a few more from new state
            for rnd in range(5):
                if step_budget(data["frame"]) < 4:
                    break
                fr15, free, me = dump(data, f"c{rnd}")
                if len(free) != 2:
                    break
                south = max(free, key=lambda w: (w[1], w[0]))
                north = min(free, key=lambda w: (w[1], w[0]))
                progressed = False
                for dx in (2, 3, 4, 5, 6):
                    for cur2, ld2, lab in (
                        (north, (north[0] + dx, north[1]), "Ne"),
                        (south, (south[0] + dx, south[1]), "Se"),
                        (south, (south[0], south[1] + dx), "Ss"),
                    ):
                        if ld2 in DEAD2:
                            continue
                        o2 = south if cur2 == north else north
                        if cheb(ld2, o2) < 5 or near_any(ld2, list(fr15), cheb=5):
                            continue
                        data, newc, st = move_wp(sess, data, cur2, ld2, fr15)
                        print(f"    {lab} {cur2}->{ld2} {st}")
                        if st == "dead" or data.get("state") == "GAME_OVER":
                            print("DEAD", ld2)
                            return
                        if st == "moved":
                            dump(data, "HIT2")
                            progressed = True
                            break
                    if progressed:
                        break
                if not progressed:
                    print("cont stall")
                    break
            dump(data, "END")
            return
    print("none moved")
    dump(data, "END")


if __name__ == "__main__":
    main()
