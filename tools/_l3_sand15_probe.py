"""From d15=4 bud=6: two-step south sandwich to dock ship15 on (34,57)."""
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


def boot_d15_4():
    """skip-e54, skip S6048, fin15 only → d15=4 bud≈6."""
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_sand15"]},
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
    # no S6048
    data, _ = do_fin15(sess, data)
    dump(data, "d15_4")
    return sess, data, True


def try_move(sess, data, cur, tgt):
    fr15 = list(lock_other_ship(data["frame"], 14))
    freeze14 = lock_other_ship(data["frame"], 15)
    # snap cur to live
    cur = min(fr15, key=lambda w: abs(w[0] - cur[0]) + abs(w[1] - cur[1]))
    other = next((w for w in fr15 if w != cur), cur)
    if max(abs(tgt[0] - other[0]), abs(tgt[1] - other[1])) < 5:
        return data, "merge", cur
    if near_any(tgt, list(freeze14), cheb=5):
        return data, "near14", cur
    data, newc, st = move_wp(sess, data, cur, tgt, freeze14)
    print(
        f"  {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}",
        flush=True,
    )
    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, "dead", cur
    return data, st, newc if st == "moved" else cur


CHAINS = [
    # (name, steps as (who_hint_x, tgt))
    ("Rw-Lw", [("R", (40, 58)), ("L", (28, 58))]),
    ("Lw-Rw", [("L", (28, 58)), ("R", (40, 58))]),
    ("R36-L32", [("R", (36, 58)), ("L", (32, 58))]),
    ("L32-R36", [("L", (32, 58)), ("R", (36, 58))]),
    ("R34-L32", [("R", (34, 58)), ("L", (28, 58))]),
    ("finw-R36", [("L", (28, 56)), ("R", (36, 58))]),
    ("finw-L32", [("L", (28, 56)), ("L", (32, 58))]),  # second uses new west
    ("finw-R34", [("L", (28, 56)), ("R", (34, 58))]),
    ("finw-R4058", [("L", (28, 56)), ("R", (40, 58))]),
    ("R4058-finw", [("R", (40, 58)), ("L", (28, 56))]),
    ("R3658-L2858", [("R", (36, 58)), ("L", (28, 58))]),
    ("L2858-R3658", [("L", (28, 58)), ("R", (36, 58))]),
]


def main():
    hits = []
    for name, steps in CHAINS:
        print(f"\n===== {name} =====", flush=True)
        sess, data, ok = boot_d15_4()
        if not ok:
            print("boot fail", flush=True)
            continue
        dead = False
        for who, tgt in steps:
            if "frame" not in data or step_budget(data["frame"]) < 2:
                print("budout", flush=True)
                break
            fr15 = list(lock_other_ship(data["frame"], 14))
            cur = max(fr15, key=lambda w: w[0]) if who == "R" else min(fr15, key=lambda w: w[0])
            data, st, _ = try_move(sess, data, cur, tgt)
            if st == "dead":
                print("DEAD", flush=True)
                dead = True
                break
            if st != "moved":
                print(f"SOFT {st}", flush=True)
                break
            dump(data, f"after-{tgt}")
        if dead or "frame" not in data:
            continue
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
        d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
        d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
        tags = []
        if d15 == 0:
            tags.append("D15CLEAR")
        if me15["c"] == GOAL15:
            tags.append("ON_GOAL")
        if d15 < 4:
            tags.append(f"d15={d15}")
        if (data.get("levels_completed") or 0) >= 3:
            tags.append("PASS")
        print(
            f"RESULT {' '.join(tags) or 'LIVE'} {name} "
            f"ship15={me15['c']} d14={d14} d15={d15} bud={step_budget(data['frame'])}",
            flush=True,
        )
        hits.append((name, tags, me15["c"], d14, d15, step_budget(data["frame"])))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    best = sorted(hits, key=lambda x: (0 if "PASS" in x[1] or "D15CLEAR" in x[1] else 1, x[4], x[3], -x[5]))
    print("BEST", best[:8] or "none", flush=True)


if __name__ == "__main__":
    main()
