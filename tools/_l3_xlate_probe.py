"""After mid-east+deep15: vacate west15 and/or dual-translate toward goal (no x60)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east, translate2
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, lock_other_ship, near_any
from tools.r11l_seated_clear import clear_l1, reset
from tools._l3_d15gw_probe import deep15

GOAL14, GOAL15 = (55, 53), (34, 57)


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
    d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
    print(
        f"{label} ship14={me14['c']} d14={d14} free={sorted(free)} "
        f"d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, d15, free, fr15


def boot():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_xlate"]},
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
    data, ok = deep15(sess, data)
    return sess, data, ok


def vac_west15(sess, data, tgts):
    """Move western chrome15 pad through tgts (first success)."""
    freeze14 = lock_other_ship(data["frame"], 15)
    flock15 = list(lock_other_ship(data["frame"], 14))
    if not flock15:
        return data, False
    west = min(flock15, key=lambda w: w[0])
    east = max(flock15, key=lambda w: w[0])
    for tgt in tgts:
        if cheb(tgt, east) < 5 or near_any(tgt, list(freeze14), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, west, tgt, freeze14)
        print(f"  vacW {west}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st == "moved":
            return data, True
    return data, False


def step14(sess, data, who, tgt):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return data, "nfree"
    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    cur = {"R": lead, "L": lag, "N": north, "S": south}[who]
    other = next(w for w in free if w != cur)
    if cheb(tgt, other) < 5:
        return data, "merge"
    if near_any(tgt, list(fr15), cheb=5):
        return data, "near15"
    data, newc, st = move_wp(sess, data, cur, tgt, fr15)
    print(f"  {who} {cur}->{tgt} {st}->{newc}", flush=True)
    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, "dead"
    if st != "moved":
        return data, st
    return data, "moved"


PLANS = [
    # vacate west15 toward goal15, then SE for 14
    ("vacW3456-L-N-S5242-S5553", "vac", [(34, 56), (36, 56), (38, 56), (34, 52)], [("L", (36, 44)), ("N", (48, 32)), ("S", (52, 42)), ("S", (55, 53))]),
    ("vacW3456-L-R4848-R5553", "vac", [(34, 56), (38, 56)], [("L", (36, 44)), ("R", (48, 48)), ("R", (55, 53))]),
    ("vacW3856-L-N-S5242-L4248", "vac", [(38, 56), (34, 56)], [("L", (36, 44)), ("N", (48, 32)), ("S", (52, 42)), ("L", (42, 48))]),
    # dual translate east/south (no SE stack)
    ("xlate5x2", "xlate", [(5, 0), (5, 0)], []),
    ("xlate5-dy4", "xlate", [(5, 0), (0, 4)], []),
    ("xlate5-dy4-dx5", "xlate", [(5, 0), (0, 4), (5, 0)], []),
    ("xlate_dy5x2", "xlate", [(0, 5), (0, 5)], []),
    # vac then xlate
    ("vacW-xlate5x2", "vacx", [(34, 56), (38, 56)], [(5, 0), (5, 0)]),
    # baseline x60 after vac (compare)
    ("vacW-base60", "vac", [(34, 56), (38, 56)], [("L", (36, 44)), ("N", (48, 32)), ("S", (60, 44)), ("N", (60, 38)), ("S", (60, 48))]),
]


def main():
    hits = []
    for item in PLANS:
        name, kind = item[0], item[1]
        print(f"\n===== {name} =====", flush=True)
        sess, data, ok = boot()
        if not ok:
            print("boot fail", flush=True)
            continue
        d0, d15_0, _, _ = dump(data, "start")
        failed = False
        if kind == "vac":
            _, vac_tgts, steps = item[1], item[2], item[3]
            data, vok = vac_west15(sess, data, vac_tgts)
            if not vok:
                print("SOFT vac", flush=True)
                failed = True
            else:
                dump(data, "after-vac")
                for who, tgt in steps:
                    if "frame" not in data or step_budget(data["frame"]) < 3:
                        print("budout", flush=True)
                        failed = True
                        break
                    data, st = step14(sess, data, who, tgt)
                    if st == "dead":
                        print("DEAD", flush=True)
                        failed = True
                        break
                    if st != "moved":
                        print(f"SOFT {st}", flush=True)
                        failed = True
                        break
                    dump(data, f"after-{who}{tgt}")
        elif kind == "xlate":
            _, moves, _ = item[1], item[2], item[3]
            for dx, dy in moves:
                if "frame" not in data or step_budget(data["frame"]) < 6:
                    print("budout", flush=True)
                    failed = True
                    break
                freeze15 = lock_other_ship(data["frame"], 14)
                print(f"--- xlate dx={dx} dy={dy} ---", flush=True)
                data, xok = translate2(sess, data, freeze15, dx=dx, dy=dy)
                if data.get("state") == "GAME_OVER" or "frame" not in data:
                    print("DEAD xlate", flush=True)
                    failed = True
                    break
                dump(data, f"xlate{dx},{dy}")
                if not xok:
                    print("SOFT xlate", flush=True)
                    # keep going — partial may still help
        elif kind == "vacx":
            vac_tgts, moves = item[2], item[3]
            data, vok = vac_west15(sess, data, vac_tgts)
            if not vok:
                print("SOFT vac", flush=True)
                failed = True
            else:
                dump(data, "after-vac")
                for dx, dy in moves:
                    if "frame" not in data or step_budget(data["frame"]) < 6:
                        print("budout", flush=True)
                        failed = True
                        break
                    freeze15 = lock_other_ship(data["frame"], 14)
                    print(f"--- xlate dx={dx} dy={dy} ---", flush=True)
                    data, xok = translate2(sess, data, freeze15, dx=dx, dy=dy)
                    if data.get("state") == "GAME_OVER" or "frame" not in data:
                        print("DEAD xlate", flush=True)
                        failed = True
                        break
                    dump(data, f"xlate{dx},{dy}")

        if failed or "frame" not in data:
            continue
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
        d1 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
        d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
        tag = "IMPROVED" if d1 < d0 else ("FLAT" if d1 == d0 else "WORSE")
        beat = " BEAT25" if d1 < 25 else ""
        free = count_free14(data["frame"], lock_other_ship(data["frame"], 14))
        print(
            f"RESULT {tag}{beat} {name} d14 {d0}->{d1} d15 {d15_0}->{d15} "
            f"bud={step_budget(data['frame'])} free={sorted(free)}",
            flush=True,
        )
        hits.append((tag, name, d0, d1, d15, step_budget(data["frame"])))
        if (data.get("levels_completed") or 0) >= 3:
            print("PASS L3!", flush=True)

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    best = sorted(
        [h for h in hits if h[0] in ("IMPROVED", "FLAT")],
        key=lambda x: (x[3], x[4], -x[5]),
    )
    print("BEST", best[:10] or "none", flush=True)
    print("BEAT25", [h for h in hits if h[3] < 25] or "none", flush=True)


if __name__ == "__main__":
    main()
