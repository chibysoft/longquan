"""mid-east + light15 (E5842+W4250, no E5854): stepwise 2wp toward goal, avoid x60."""
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

GOAL14 = (55, 53)


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me14['c']} d14={d14} free={sorted(free)} "
        f"d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, free, fr15


def boot():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l15g"]},
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
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    print(f"  E5842 {st}", flush=True)
    if st != "moved":
        return sess, data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    print(f"  W4250 {st} bud={step_budget(data['frame'])}", flush=True)
    if st != "moved":
        return sess, data, False
    dump(data, "gate")
    return sess, data, True


def step(sess, data, who, tgt):
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
    print(
        f"  {who} {cur}->{tgt} {st}->{newc} "
        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}",
        flush=True,
    )
    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, "dead"
    if st != "moved":
        return data, st
    return data, "moved"


PLANS = [
    # Step through y44 then south to goal column
    ("L3644-R4044-R4848-R5553", [("L", (36, 44)), ("R", (40, 44)), ("R", (48, 48)), ("R", (55, 53))]),
    ("L3644-R4044-R5050-R5553", [("L", (36, 44)), ("R", (40, 44)), ("R", (50, 50)), ("R", (55, 53))]),
    ("L3644-R4044-R5248-L4248", [("L", (36, 44)), ("R", (40, 44)), ("R", (52, 48)), ("L", (42, 48))]),
    ("L3644-R4544-R5550", [("L", (36, 44)), ("R", (45, 44)), ("R", (55, 50))]),
    ("L3644-R4844-R5550", [("L", (36, 44)), ("R", (48, 44)), ("R", (55, 50))]),
    ("L3644-R5044-R5553", [("L", (36, 44)), ("R", (50, 44)), ("R", (55, 53))]),
    # N4832 unlock then goal-south instead of S6044
    ("L3644-N4832-S5248-S5553", [("L", (36, 44)), ("N", (48, 32)), ("S", (52, 48)), ("S", (55, 53))]),
    ("L3644-N4832-S5544-S5553", [("L", (36, 44)), ("N", (48, 32)), ("S", (55, 44)), ("S", (55, 53))]),
    ("L3644-N4832-S5242-S5248-S5550", [("L", (36, 44)), ("N", (48, 32)), ("S", (52, 42)), ("S", (52, 48)), ("S", (55, 50))]),
    # Lead-only chain from gate
    ("R3844-R4544-R5248-R5553", [("R", (38, 44)), ("R", (45, 44)), ("R", (52, 48)), ("R", (55, 53))]),
    ("R4044-R4848-L3848-R5553", [("R", (40, 44)), ("R", (48, 48)), ("L", (38, 48)), ("R", (55, 53))]),
    # Pair at goal
    ("L3644-R4044-R5553-L4553", [("L", (36, 44)), ("R", (40, 44)), ("R", (55, 53)), ("L", (45, 53))]),
    ("L3644-R5550-L4550", [("L", (36, 44)), ("R", (55, 50)), ("L", (45, 50))]),
    # Compare: known S6048 path for d14 baseline with light15 only (no E5854)
    ("base-N4832-S6044-N6038-S6048", [("L", (36, 44)), ("N", (48, 32)), ("S", (60, 44)), ("N", (60, 38)), ("S", (60, 48))]),
]


def main():
    hits = []
    for name, steps in PLANS:
        print(f"\n===== {name} =====", flush=True)
        sess, data, ok = boot()
        if not ok:
            print("boot fail", flush=True)
            continue
        d0, _, _ = dump(data, "start")
        failed = False
        for who, tgt in steps:
            if "frame" not in data or step_budget(data["frame"]) < 3:
                print("budout", flush=True)
                failed = True
                break
            data, st = step(sess, data, who, tgt)
            if st == "dead":
                print("DEAD", flush=True)
                failed = True
                break
            if st != "moved":
                print(f"SOFT {st}", flush=True)
                failed = True
                break
            d1, free, _ = dump(data, f"after-{who}{tgt}")
            if d1 < d0:
                print(f"  progress d14 {d0}->{d1}", flush=True)
            if (data.get("levels_completed") or 0) >= 3:
                print("PASS L3!", flush=True)
                hits.append(("PASS", name, d0, 0, step_budget(data["frame"])))
                failed = False
                break
        if failed or "frame" not in data:
            continue
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        d1 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
        tag = "IMPROVED" if d1 < d0 else ("FLAT" if d1 == d0 else "WORSE")
        beat = " BEAT25" if d1 < 25 else (" BEAT20" if d1 < 20 else "")
        free2 = count_free14(data["frame"], lock_other_ship(data["frame"], 14))
        print(
            f"RESULT {tag}{beat} {name} d14 {d0}->{d1} "
            f"bud={step_budget(data['frame'])} free={sorted(free2)}",
            flush=True,
        )
        hits.append((tag, name, d0, d1, step_budget(data["frame"])))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    best = sorted(
        [h for h in hits if h[0] in ("IMPROVED", "PASS")],
        key=lambda x: (0 if x[0] == "PASS" else 1, x[3], -x[4]),
    )
    print("BEST", best[:10] or "none", flush=True)
    print("BEAT25", [h for h in hits if isinstance(h[3], int) and h[3] < 25] or "none", flush=True)


if __name__ == "__main__":
    main()
