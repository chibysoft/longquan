"""From N6038 pose (44,38) d14=26 bud=4: dense single-move scan for d14<25."""
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
from tools._l3_savebud_probe import deep15, do_fin15, dump, move14

GOAL14, GOAL15 = (55, 53), (34, 57)


def boot_n6038():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_n6038scan"]},
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
    for who, tgt in (("L", (36, 44)), ("N", (48, 32)), ("S", (60, 44)), ("N", (60, 38))):
        data, st = move14(sess, data, who, tgt)
        if st != "moved":
            return sess, data, False
    dump(data, "N6038")
    return sess, data, True


def gen_tgts():
    tgts = []
    for x in range(44, 63, 2):
        for y in range(38, 56, 2):
            tgts.append((x, y))
    # extras near goal
    for t in ((55, 53), (55, 50), (52, 53), (50, 53), (55, 48), (48, 53), (60, 53), (58, 52)):
        if t not in tgts:
            tgts.append(t)
    return tgts


def main():
    # One boot, try many moves by rebooting — but filter by merge/near first offline
    sess, data, ok = boot_n6038()
    if not ok:
        print("boot fail", flush=True)
        return
    freeze15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], freeze15)
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    print(f"pads N={north} S={south} freeze15={sorted(freeze15)}", flush=True)

    cands = []
    for role, cur, other in (("S", south, north), ("N", north, south)):
        for tgt in gen_tgts():
            if max(abs(tgt[0] - cur[0]), abs(tgt[1] - cur[1])) <= 1:
                continue
            if max(abs(tgt[0] - other[0]), abs(tgt[1] - other[1])) < 5:
                continue
            if near_any(tgt, list(freeze15), cheb=5):
                continue
            # prefer toward goal
            dist = abs(tgt[0] - GOAL14[0]) + abs(tgt[1] - GOAL14[1])
            cands.append((dist, role, tgt))
    cands = sorted(cands)[:40]
    print(f"try {len(cands)} cands", flush=True)

    hits = []
    for dist, role, tgt in cands:
        sess, data, ok = boot_n6038()
        if not ok:
            continue
        data, st = move14(sess, data, role, tgt)
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            print(f"DEAD {role}{tgt}", flush=True)
            continue
        if st != "moved":
            continue
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
        d15 = abs(next(s for s in ships(data["frame"]) if s["chrome"] == 15)["c"][0] - GOAL15[0]) + abs(
            next(s for s in ships(data["frame"]) if s["chrome"] == 15)["c"][1] - GOAL15[1]
        )
        bud = step_budget(data["frame"])
        mark = "HIT" if d14 < 25 else ("EQ" if d14 == 25 else "")
        if d14 <= 26:
            print(f"LIVE {mark} {role}{tgt} ship={me14['c']} d14={d14} d15={d15} bud={bud}", flush=True)
        hits.append((d14, -bud, role, tgt, me14["c"]))
    print("BEST", sorted(hits)[:12], flush=True)


if __name__ == "__main__":
    main()
