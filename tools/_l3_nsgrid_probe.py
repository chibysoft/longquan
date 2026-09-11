"""Micro-variants after early-dock: N unlock + S toward goal14."""
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

# After L(36,44): try N variants then S variants
N_TGTS = [(48, 32), (50, 34), (46, 34), (52, 36), (44, 32), (48, 36), (48, 40)]
S_TGTS = [(60, 44), (58, 46), (56, 48), (54, 48), (52, 50), (55, 50), (60, 48), (62, 46), (50, 46)]


def boot_docked():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_nsgrid"]},
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
    data, newc, st = move_wp(sess, data, west, (28, 58), freeze14)
    if st != "moved":
        return sess, data, False
    return sess, data, True


def score(data):
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
    d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
    return me14["c"], d14, d15, step_budget(data["frame"])


def main():
    hits = []
    # Phase1: each N after L, dump pose
    for nt in N_TGTS:
        print(f"\n===== N{nt} =====", flush=True)
        sess, data, ok = boot_docked()
        if not ok:
            print("boot fail", flush=True)
            continue
        data, st = move14(sess, data, "L", (36, 44))
        if st != "moved":
            print(f"SOFT L {st}", flush=True)
            continue
        data, st = move14(sess, data, "N", nt)
        if st != "moved":
            print(f"SOFT N {st}", flush=True)
            continue
        ship, d14, d15, bud = score(data)
        print(f"  after-N ship={ship} d14={d14} bud={bud}", flush=True)
        # try all S
        for stgt in S_TGTS:
            sess2, data2, ok2 = boot_docked()
            if not ok2:
                continue
            data2, st = move14(sess2, data2, "L", (36, 44))
            if st != "moved":
                continue
            data2, st = move14(sess2, data2, "N", nt)
            if st != "moved":
                continue
            data2, st = move14(sess2, data2, "S", stgt)
            if st == "dead" or data2.get("state") == "GAME_OVER" or "frame" not in data2:
                print(f"  DEAD S{stgt}", flush=True)
                continue
            if st != "moved":
                continue  # silent noop
            ship, d14, d15, bud = score(data2)
            tag = f"d14={d14}"
            if d14 <= 25:
                tag = f"HIT {tag}"
            print(f"  LIVE N{nt}+S{stgt} ship={ship} {tag} d15={d15} bud={bud}", flush=True)
            hits.append((nt, stgt, ship, d14, bud))

    print("\n===== BEST =====", flush=True)
    for h in sorted(hits, key=lambda x: (x[3], -x[4]))[:15]:
        print(h, flush=True)


if __name__ == "__main__":
    main()
