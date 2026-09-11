"""From early-docked d15=0 bud≈17: alt chrome14 SE chains toward (55,53)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import clear15_corridor, lock_other_ship, near_any
from tools.r11l_seated_clear import clear_l1, reset
from tools._l3_savebud_probe import deep15, do_fin15, dump, move14

GOAL14, GOAL15 = (55, 53), (34, 57)

CHAINS = [
    ("baseline", [("L", (36, 44)), ("N", (48, 32)), ("S", (60, 44)), ("N", (60, 38)), ("S", (60, 48))]),
    ("S6050", [("L", (36, 44)), ("N", (48, 32)), ("S", (60, 50))]),
    ("S5553", [("L", (36, 44)), ("N", (48, 32)), ("S", (55, 53))]),
    ("S6053", [("L", (36, 44)), ("N", (48, 32)), ("S", (60, 53))]),
    ("S5248", [("L", (36, 44)), ("N", (48, 32)), ("S", (52, 48))]),
    ("deepS", [("L", (36, 44)), ("N", (48, 32)), ("S", (60, 44)), ("S", (60, 52))]),
    ("goalish", [("L", (36, 44)), ("N", (48, 32)), ("S", (60, 44)), ("N", (55, 38)), ("S", (55, 53))]),
    ("lag48", [("L", (40, 44)), ("N", (48, 32)), ("S", (55, 48))]),
    ("lag42", [("L", (36, 42)), ("N", (48, 32)), ("S", (55, 50))]),
    ("noN_S48", [("L", (36, 44)), ("S", (48, 48))]),
    ("noN_S55", [("L", (36, 44)), ("S", (52, 48)), ("S", (55, 53))]),
    ("leadE", [("R", (42, 36)), ("L", (36, 44)), ("N", (48, 32)), ("S", (55, 48))]),
]


def boot_docked():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_altse"]},
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
    if not ok:
        return sess, data, False
    data, _ = do_fin15(sess, data)
    freeze14 = lock_other_ship(data["frame"], 15)
    flock15 = list(lock_other_ship(data["frame"], 14))
    west = min(flock15, key=lambda w: w[0])
    data, newc, st = move_wp(sess, data, west, (28, 58), freeze14)
    print(f"  dock {west}->(28,58) {st}->{newc}", flush=True)
    if st != "moved":
        return sess, data, False
    dump(data, "docked")
    return sess, data, True


def main():
    hits = []
    for name, steps in CHAINS:
        print(f"\n===== {name} =====", flush=True)
        sess, data, ok = boot_docked()
        if not ok:
            print("boot fail", flush=True)
            continue
        dead = False
        for who, tgt in steps:
            if "frame" not in data or step_budget(data["frame"]) < 2:
                print("budout", flush=True)
                break
            data, st = move14(sess, data, who, tgt)
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                print("DEAD", flush=True)
                dead = True
                break
            if st != "moved":
                print(f"SOFT {who}->{tgt} {st}", flush=True)
                break
        if dead or "frame" not in data:
            continue
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
        d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
        d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
        tags = []
        if (data.get("levels_completed") or 0) >= 3:
            tags.append("PASS")
        if d15 == 0:
            tags.append("d15=0")
        if d14 < 26:
            tags.append(f"BEAT14:{d14}")
        print(
            f"RESULT {' '.join(tags) or 'LIVE'} {name} "
            f"ship14={me14['c']} d14={d14} d15={d15} bud={step_budget(data['frame'])}",
            flush=True,
        )
        hits.append((name, tags, me14["c"], d14, d15, step_budget(data["frame"])))

    print("\n===== HITS =====", flush=True)
    for h in sorted(hits, key=lambda x: (0 if "PASS" in x[1] else 1, x[3], -x[5])):
        print(h, flush=True)


if __name__ == "__main__":
    main()
