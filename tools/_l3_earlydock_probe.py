"""Dock chrome15 right after early15E (bud~22), then SE for chrome14."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, lock_other_ship, near_any
from tools.r11l_seated_clear import clear_l1, reset
from tools._l3_savebud_probe import deep15, se_to_n6038, do_fin15, dump, move14

GOAL14, GOAL15 = (55, 53), (34, 57)


def boot_after_deep():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_earlydock"]},
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
    data, ok = deep15(sess, data, do_east15b=False, early_tgt=(40, 56))
    return sess, data, ok


def dock15(sess, data):
    """fin15 remnant + west→(28,58)."""
    data, _ = do_fin15(sess, data)
    freeze14 = lock_other_ship(data["frame"], 15)
    flock15 = list(lock_other_ship(data["frame"], 14))
    west = min(flock15, key=lambda w: w[0])
    east = max(flock15, key=lambda w: w[0])
    if west[0] <= 36 and west[1] >= 54:
        for vt in ((28, 58), (28, 56)):
            if max(abs(vt[0] - east[0]), abs(vt[1] - east[1])) < 5:
                continue
            if near_any(vt, list(freeze14), cheb=5):
                continue
            data, newc, st = move_wp(sess, data, west, vt, freeze14)
            print(f"  early-dock {west}->{vt} {st}->{newc}", flush=True)
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                return data, False
            if st == "moved":
                return data, True
    return data, False


def score(data):
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
    d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
    return me14["c"], me15["c"], d14, d15, step_budget(data["frame"])


def main():
    print("===== early dock then SE =====", flush=True)
    sess, data, ok = boot_after_deep()
    if not ok:
        print("deep fail", flush=True)
        return
    dump(data, "after-deep")
    data, ok = dock15(sess, data)
    dump(data, "after-dock")
    if not ok:
        print("dock fail", flush=True)
        return
    ship, ship15, d14, d15, bud = score(data)
    print(f"docked ship15={ship15} d15={d15} d14={d14} bud={bud}", flush=True)
    if d15 != 0:
        print("d15 not clear — abort", flush=True)
        return

    # Now SE for 14 with leftover bud
    data, ok = se_to_n6038(sess, data)
    dump(data, "after-SE")
    ship, ship15, d14, d15, bud = score(data)
    tags = []
    if d15 == 0:
        tags.append("d15=0")
    if d14 < 20:
        tags.append(f"d14={d14}")
    if (data.get("levels_completed") or 0) >= 3:
        tags.append("PASS")
    print(
        f"RESULT {' '.join(tags) or 'LIVE'} after-SE "
        f"ship14={ship} ship15={ship15} d14={d14} d15={d15} bud={bud}",
        flush=True,
    )

    # Opportunistic south pulls while bud allows
    for name, who, tgt in [
        ("S6048", "S", (60, 48)),
        ("S6050", "S", (60, 50)),
        ("S5553", "S", (55, 53)),
        ("S5248", "S", (52, 48)),
        ("N6052", "N", (60, 52)),
    ]:
        if "frame" not in data or step_budget(data["frame"]) < 2:
            break
        before = score(data)
        data, st = move14(sess, data, who, tgt)
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            print(f"DEAD {name}", flush=True)
            break
        if st != "moved":
            print(f"SOFT {name} {st}", flush=True)
            continue
        after = score(data)
        print(
            f"  pull {name} d14 {before[2]}->{after[2]} d15={after[3]} bud={after[4]} "
            f"ship14={after[0]}",
            flush=True,
        )
        if (data.get("levels_completed") or 0) >= 3:
            print("PASS L3", flush=True)
            break
    dump(data, "final")


if __name__ == "__main__":
    main()
