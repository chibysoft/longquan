"""From N43 after frog-ny: try 15 vacate targets one-reboot-each."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import (
    advance_14_frog_ny_stack,
    clear15_corridor,
    count_free14,
    lock_other_ship,
    near_any,
)
from tools.r11l_seated_clear import clear_l1, reset

# Known deadly for 15
BAD15 = {(45, 52), (48, 46), (41, 48), (52, 44), (45, 47)}


def boot_to_n43():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l315v"]},
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
    data, ok = advance_14_frog_ny_stack(sess, data, (34, 57))
    return sess, data, ok


def unlocks(fr15):
    cells = ((43, 42), (44, 44), (44, 40), (42, 44), (43, 40), (48, 44))
    return {c: near_any(c, list(fr15), cheb=5) for c in cells}


def main():
    tgts = [
        # south / SE from ~(45,42)
        (45, 45),
        (46, 45),
        (47, 45),
        (48, 45),
        (45, 46),
        (46, 46),
        (47, 46),
        (48, 48),
        (50, 48),
        (50, 46),
        (52, 46),
        (52, 48),
        (48, 50),
        (50, 50),
        (34, 52),
        (36, 54),
        (40, 52),
        (42, 50),
        # east along y42
        (48, 42),
        (50, 42),
        (52, 42),
        (54, 42),
        (48, 43),
        (50, 43),
        # east15 move instead
        ("east", (56, 44)),
        ("east", (56, 46)),
        ("east", (58, 42)),
        ("east", (56, 48)),
    ]
    for item in tgts:
        who, tgt = (item[0], item[1]) if isinstance(item, tuple) and item[0] == "east" else ("west", item)
        if isinstance(tgt, tuple) and tgt in BAD15:
            continue
        print(f"=== 15 {who} -> {tgt} ===")
        sess, data, ok = boot_to_n43()
        if not ok or data.get("state") == "GAME_OVER":
            print("boot fail")
            continue
        freeze14 = lock_other_ship(data["frame"], 15)
        fr15 = list(lock_other_ship(data["frame"], 14))
        west15 = min(fr15, key=lambda w: w[0])
        east15 = max(fr15, key=lambda w: w[0])
        cur = east15 if who == "east" else west15
        oth = west15 if who == "east" else east15
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
        print(
            f"  base ship14={me14['c']} ship15={me15['c']} fr15={sorted(fr15)} "
            f"bud={step_budget(data['frame'])} unlock={unlocks(fr15)}"
        )
        if near_any(tgt, list(freeze14), cheb=5):
            print("  near14")
            continue
        if max(abs(tgt[0] - oth[0]), abs(tgt[1] - oth[1])) < 5:
            print("  merge15")
            continue
        data, newc, st = move_wp(sess, data, cur, tgt, freeze14)
        print(f"  {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            BAD15.add(tgt)
            print("  DEAD")
            continue
        if st != "moved":
            continue
        fr15 = list(lock_other_ship(data["frame"], 14))
        u = unlocks(fr15)
        print(f"  AFTER fr15={sorted(fr15)} unlock={u}")
        # Try a 14 move into newly unlocked cell
        free = count_free14(data["frame"], lock_other_ship(data["frame"], 14))
        if len(free) != 2:
            print("  flock", free)
            continue
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
        freeze15 = lock_other_ship(data["frame"], 14)
        for cell in ((43, 42), (44, 40), (44, 44), (42, 44), (43, 40)):
            if u.get(cell):
                continue
            # pick closer wp
            cur14 = north if abs(cell[1] - north[1]) <= abs(cell[1] - south[1]) else south
            other = south if cur14 == north else north
            if max(abs(cell[0] - other[0]), abs(cell[1] - other[1])) < 5:
                continue
            if cell[1] <= 36 and cell[0] >= 45:
                continue
            data, newc, st = move_wp(sess, data, cur14, cell, freeze15)
            print(f"  14 {cur14}->{cell} {st}->{newc}")
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("  14DEAD", cell)
                break
            if st == "moved":
                me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
                d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
                free2 = count_free14(data["frame"], lock_other_ship(data["frame"], 14))
                print(f"  HIT14 ship={me['c']} d14={d14} free={sorted(free2)} bud={step_budget(data['frame'])}")
                return
        # even without 14 move, report if unlock improved
        if not all(u.values()):
            print("  PARTIAL unlock — keep looking for 14 hit")
    print("done BAD15=", BAD15)


if __name__ == "__main__":
    main()
