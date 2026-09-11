"""After early-dock + L + N4832 + S6044 (d14≈30 bud≈7): scan N/S2 for better d14."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import clear15_corridor, lock_other_ship
from tools.r11l_seated_clear import clear_l1, reset
from tools._l3_savebud_probe import deep15, do_fin15, dump, move14

GOAL14, GOAL15 = (55, 53), (34, 57)

CHAINS = [
    ("base_N6038_S6048", [("N", (60, 38)), ("S", (60, 48))]),
    ("N6038_hold", [("N", (60, 38))]),
    ("N5538_S5550", [("N", (55, 38)), ("S", (55, 50))]),
    ("N5538_S5553", [("N", (55, 38)), ("S", (55, 53))]),
    ("N5238_S5250", [("N", (52, 38)), ("S", (52, 50))]),
    ("N6038_S6050", [("N", (60, 38)), ("S", (60, 50))]),
    ("N6038_S5553", [("N", (60, 38)), ("S", (55, 53))]),
    ("N6038_S5248", [("N", (60, 38)), ("S", (52, 48))]),
    ("S6048_direct", [("S", (60, 48))]),
    ("S6050_direct", [("S", (60, 50))]),
    ("N4840_S5550", [("N", (48, 40)), ("S", (55, 50))]),
    ("N6036_S6048", [("N", (60, 36)), ("S", (60, 48))]),
    ("N5640_S5650", [("N", (56, 40)), ("S", (56, 50))]),
    ("N6038_N5550", [("N", (60, 38)), ("N", (55, 50))]),  # may nfree
    ("S5644_N6038", [("S", (56, 44)), ("N", (60, 38))]),
]


def boot_s6044():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_posts6044"]},
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
    west = min(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
    data, _, st = move_wp(sess, data, west, (28, 58), freeze14)
    if st != "moved":
        return sess, data, False
    for who, tgt in (("L", (36, 44)), ("N", (48, 32)), ("S", (60, 44))):
        data, st = move14(sess, data, who, tgt)
        if st != "moved":
            print(f"boot soft {who}->{tgt} {st}", flush=True)
            return sess, data, False
    dump(data, "S6044")
    return sess, data, True


def main():
    hits = []
    for name, steps in CHAINS:
        print(f"\n===== {name} =====", flush=True)
        sess, data, ok = boot_s6044()
        if not ok:
            print("boot fail", flush=True)
            continue
        for who, tgt in steps:
            if "frame" not in data or step_budget(data["frame"]) < 2:
                print("budout", flush=True)
                break
            data, st = move14(sess, data, who, tgt)
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                print("DEAD", flush=True)
                break
            if st != "moved":
                print(f"SOFT {who}->{tgt} {st}", flush=True)
                break
        if "frame" not in data:
            continue
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
        d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
        d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
        tags = []
        if (data.get("levels_completed") or 0) >= 3:
            tags.append("PASS")
        if d14 < 26:
            tags.append(f"BEAT:{d14}")
        print(
            f"RESULT {' '.join(tags) or 'LIVE'} {name} "
            f"ship14={me14['c']} d14={d14} d15={d15} bud={step_budget(data['frame'])}",
            flush=True,
        )
        hits.append((d14, -step_budget(data["frame"]), name, me14["c"], d15))
    print("\n===== BEST =====", flush=True)
    for h in sorted(hits)[:10]:
        print(h, flush=True)


if __name__ == "__main__":
    main()
