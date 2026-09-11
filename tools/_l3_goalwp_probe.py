"""From mid-east (no x60 SE): plant 2wp toward goal-west of (55,53)."""
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
        f"{label} ship14={me14['c']} d14={d14} free={sorted(free)} n={len(free)} "
        f"d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, free, fr15


def boot(*, light15=False):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_goalwp"]},
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
    if light15:
        # Only push east15 out of choke — keep west, skip (58,54)
        freeze14 = lock_other_ship(data["frame"], 15)
        fr15 = list(lock_other_ship(data["frame"], 14))
        data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
        print(f"  light E5842 {st} bud={step_budget(data['frame'])}", flush=True)
        if st == "moved":
            freeze14 = lock_other_ship(data["frame"], 15)
            data, _, st = move_wp(
                sess,
                data,
                min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]),
                (42, 50),
                freeze14,
            )
            print(f"  light W4250 {st} bud={step_budget(data['frame'])}", flush=True)
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
    other = [w for w in free if w != cur]
    other = other[0] if other else cur
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


# Plans: who is R/L/N/S relative to current free pair.
PLANS = [
    # Direct lead SE toward goal band
    ("R4044-R4848-R5553", False, [("R", (40, 44)), ("R", (48, 48)), ("R", (55, 53))]),
    ("R4544-R5050-R5553", False, [("R", (45, 44)), ("R", (50, 50)), ("R", (55, 53))]),
    ("R4844-L3044-R5550", False, [("R", (48, 44)), ("L", (30, 44)), ("R", (55, 50))]),
    ("R5050-L4050", False, [("R", (50, 50)), ("L", (40, 50))]),
    ("R5550-L4550", False, [("R", (55, 50)), ("L", (45, 50))]),
    ("R5248-L4248", False, [("R", (52, 48)), ("L", (42, 48))]),
    ("R5048-L4048-R5553", False, [("R", (50, 48)), ("L", (40, 48)), ("R", (55, 53))]),
    # Same-row east then south
    ("R3836-R4536-R4550-R5553", False, [("R", (38, 36)), ("R", (45, 36)), ("R", (45, 50)), ("R", (55, 53))]),
    ("R3436-R4044-R5048", False, [("R", (40, 36)), ("R", (40, 44)), ("R", (50, 48))]),
    # With light15 corridor clear
    ("L15-R4848-R5553", True, [("R", (48, 48)), ("R", (55, 53))]),
    ("L15-R5050-L4050", True, [("R", (50, 50)), ("L", (40, 50))]),
    ("L15-R5248-L4248-R5553", True, [("R", (52, 48)), ("L", (42, 48)), ("R", (55, 53))]),
    ("L15-R4544-R5550", True, [("R", (45, 44)), ("R", (55, 50))]),
    ("L15-lag2644-R4044-R5550", True, [("L", (26, 44)), ("R", (40, 44)), ("R", (55, 50))]),
    # Diagonal pairs around goal
    ("R5553-L4553", False, [("R", (55, 53)), ("L", (45, 53))]),
    ("R5553-L5048", False, [("R", (55, 53)), ("L", (50, 48))]),
    ("R6053-L5053", False, [("R", (60, 53)), ("L", (50, 53))]),
]


def main():
    hits = []
    for name, light, steps in PLANS:
        print(f"\n===== {name} =====", flush=True)
        sess, data, ok = boot(light15=light)
        if not ok:
            print("boot fail", flush=True)
            continue
        d0, _, _ = dump(data, "start")
        failed = False
        best_d = d0
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
            if d1 < best_d:
                best_d = d1
                print(f"  progress d14 {d0}->{d1}", flush=True)
            if (data.get("levels_completed") or 0) >= 3:
                print("PASS L3!", flush=True)
                hits.append(("PASS", name, d0, 0, step_budget(data["frame"])))
                break
        if "frame" not in data:
            continue
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        d1 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
        tag = "IMPROVED" if d1 < d0 else ("FLAT" if d1 == d0 else "WORSE")
        if failed and d1 >= d0:
            continue
        beat = ""
        if d1 < 25:
            beat = " BEAT25"
        if d1 < 20:
            beat = " BEAT20"
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
    print("BEAT25", [h for h in hits if h[3] < 25] or "none", flush=True)


if __name__ == "__main__":
    main()
