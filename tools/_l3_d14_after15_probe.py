"""After d15=0 (skip post-S6048): scan chrome14 south pulls with leftover bud."""
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
from tools._l3_savebud_probe import deep15, se_to_n6038, do_fin15, dump

GOAL14, GOAL15 = (55, 53), (34, 57)


def boot_d15_clear(do_s6048: bool = False):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_d14_after15"]},
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
    data, ok = se_to_n6038(sess, data)
    if not ok:
        return sess, data, False
    data, _ = do_fin15(sess, data)
    # dock15: west → (28,58)
    freeze14 = lock_other_ship(data["frame"], 15)
    flock15 = list(lock_other_ship(data["frame"], 14))
    west = min(flock15, key=lambda w: w[0])
    east = max(flock15, key=lambda w: w[0])
    data, newc, st = move_wp(sess, data, west, (28, 58), freeze14)
    print(f"  dock15 {west}->(28,58) {st}->{newc}", flush=True)
    if st != "moved":
        return sess, data, False
    if do_s6048:
        from tools.r11l_l3_sync_probe import count_free14

        freeze15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], freeze15)
        south = max(free, key=lambda w: (w[1], w[0]))
        data, newc, st = move_wp(sess, data, south, (60, 48), freeze15)
        print(f"  S6048 {south}->(60,48) {st}->{newc}", flush=True)
    dump(data, "d15_0")
    return sess, data, True


def score(data):
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
    d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
    return me14["c"], me15["c"], d14, d15, step_budget(data["frame"])


# Single moves from free14 pads toward pulling ship SE
CANDS = [
    ("S6048", (60, 48)),
    ("S6050", (60, 50)),
    ("S6052", (60, 52)),
    ("S6053", (60, 53)),
    ("S5848", (58, 48)),
    ("S5553", (55, 53)),
    ("S5248", (52, 48)),
    ("S5048", (50, 48)),
    ("S4844", (48, 44)),
    ("S4448", (44, 48)),
    ("N6050", (60, 50)),  # same as S if south is north? pick by role
    ("W4838", (48, 38)),
    ("W4438", (44, 38)),
    ("W4053", (40, 53)),
    ("W4853", (48, 53)),
    ("W5253", (52, 53)),
    ("W5550", (55, 50)),
    ("W5539", (55, 39)),
]


def try_one(sess, data, role, tgt):
    from tools.r11l_l3_sync_probe import count_free14

    freeze15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], freeze15)
    if len(free) < 2:
        return data, "nofree", None
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    cur = south if role.startswith("S") else north
    other = north if cur == south else south
    if near_any(tgt, list(freeze15), cheb=5):
        return data, "near15", cur
    if max(abs(tgt[0] - other[0]), abs(tgt[1] - other[1])) < 5:
        return data, "merge", cur
    if max(abs(tgt[0] - cur[0]), abs(tgt[1] - cur[1])) <= 1:
        return data, "already", cur
    data, newc, st = move_wp(sess, data, cur, tgt, freeze15)
    return data, st, newc


def main():
    hits = []
    # Phase A: no S6048, single cand
    for name, tgt in CANDS:
        role = name[:1]
        print(f"\n===== {name} {tgt} =====", flush=True)
        sess, data, ok = boot_d15_clear(do_s6048=False)
        if not ok:
            print("boot fail", flush=True)
            continue
        ship0, _, d14_0, d15_0, bud0 = score(data)
        print(f"  start ship14={ship0} d14={d14_0} d15={d15_0} bud={bud0}", flush=True)
        if bud0 < 2:
            print("budout", flush=True)
            continue
        data, st, _ = try_one(sess, data, role, tgt)
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            print("DEAD", flush=True)
            continue
        if st != "moved":
            print(f"SOFT {st}", flush=True)
            continue
        ship, ship15, d14, d15, bud = score(data)
        tag = []
        if d14 < d14_0:
            tag.append(f"d14-{d14_0 - d14}")
        if d15 > 0:
            tag.append(f"d15={d15}")
        if (data.get("levels_completed") or 0) >= 3:
            tag.append("PASS")
        print(
            f"RESULT {' '.join(tag) or 'LIVE'} {name} "
            f"ship14={ship} ship15={ship15} d14={d14} d15={d15} bud={bud}",
            flush=True,
        )
        hits.append((name, tag, ship, d14, d15, bud, d14_0 - d14))

    print("\n===== HITS (by d14 gain) =====", flush=True)
    for h in sorted(hits, key=lambda x: (-x[6], x[3], -x[5])):
        print(h, flush=True)


if __name__ == "__main__":
    main()
