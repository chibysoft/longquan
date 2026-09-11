"""Alt plant corridor toward goal-west (skip classic 26/20 → x60 SE)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_sync_probe import (
    _plane,
    clear15_corridor,
    count_free14,
    leap14_once,
    lock_other_ship,
    near_any,
)
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


def boot_l2():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_plantg"]},
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
    freeze15 = lock_other_ship(data["frame"], 14)
    data, _ = leap14_once(sess, data, freeze15, lv0, stride=12)
    dump(data, "after-hop1")
    return sess, data, lv0


def plant_pair(sess, data, dests):
    """Plant up to 2 corridor pads at given dests (order = priority)."""
    freeze15 = lock_other_ship(data["frame"], 14)
    g = _plane(data["frame"])
    placed = []
    for dest in dests:
        if len(placed) >= 2:
            break
        freeze15 = lock_other_ship(data["frame"], 14)
        cur = count_free14(data["frame"], freeze15)
        cands = sorted(
            [w for w in cur if w[1] < 34 and w[0] > 14],
            key=lambda w: (-w[1], abs(w[0] - dest[0])),
        )
        if not cands:
            cands = sorted(cur, key=lambda w: abs(w[0] - dest[0]) + abs(w[1] - dest[1]))
        for wp in cands:
            if wp in placed or dest in cur:
                continue
            others = [c for c in cur if c != wp] + placed
            if near_any(dest, others + list(freeze15), cheb=5):
                continue
            if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
                continue
            if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
                continue
            travel = abs(dest[0] - wp[0]) + abs(dest[1] - wp[1])
            if travel < 4 or travel > 40:
                continue
            data, newc, st = move_wp(sess, data, wp, dest, freeze15)
            print(f"  plant {wp}->{dest} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}", flush=True)
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                return data, False, placed
            if st == "moved":
                placed.append(newc if isinstance(newc, tuple) else dest)
                g = _plane(data["frame"])
                break
    return data, len(placed) >= 1, placed


def try_follow(sess, data, steps):
    """Optional follow-up 2wp moves: ('R'|'L'|'N'|'S'|'any', tgt) where any=nearest free."""
    for who, tgt in steps:
        if "frame" not in data or step_budget(data["frame"]) < 4:
            return data, "budout"
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if not free:
            return data, "nfree"
        if who == "any":
            cur = min(free, key=lambda w: abs(w[0] - tgt[0]) + abs(w[1] - tgt[1]))
        elif who == "R":
            cur = max(free, key=lambda w: w[0])
        elif who == "L":
            cur = min(free, key=lambda w: w[0])
        elif who == "N":
            cur = min(free, key=lambda w: (w[1], w[0]))
        else:
            cur = max(free, key=lambda w: (w[1], w[0]))
        others = [w for w in free if w != cur]
        if others and cheb(tgt, others[0]) < 5 and len(free) == 2:
            # with n>2 allow closer
            pass
        if near_any(tgt, list(fr15), cheb=5):
            return data, "near15"
        if others and len(free) == 2 and cheb(tgt, others[0]) < 5:
            return data, "merge"
        data, newc, st = move_wp(sess, data, cur, tgt, fr15)
        print(f"  follow {who} {cur}->{tgt} {st}->{newc}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, "dead"
        if st != "moved":
            return data, st
        dump(data, f"after-{tgt}")
    return data, "ok"


# (name, plant_dests, follow_steps)
CASES = [
    ("classic2620", [(26, 36), (20, 36)], []),
    ("e3236", [(32, 36), (26, 36)], []),
    ("e3630", [(36, 36), (30, 36)], []),
    ("e4034", [(40, 36), (34, 36)], []),
    ("s3240", [(32, 40), (26, 40)], []),
    ("s3642", [(36, 42), (30, 42)], []),
    ("s4044", [(40, 44), (34, 44)], []),
    ("gw4842", [(48, 42), (42, 36)], []),
    ("gw5048", [(50, 48), (44, 42)], []),
    ("gw5550", [(55, 50), (48, 44)], []),
    ("gw5553", [(55, 53), (48, 48)], []),
    # plant east then nudge south
    ("e3630-S4044", [(36, 36), (30, 36)], [("R", (40, 44)), ("L", (34, 44))]),
    ("e4034-S4848", [(40, 36), (34, 36)], [("R", (48, 48)), ("L", (40, 48))]),
    ("s4044-R5050", [(40, 44), (34, 44)], [("R", (50, 50)), ("L", (44, 50))]),
    ("gw4842-R5553", [(48, 42), (42, 36)], [("R", (55, 53)), ("L", (48, 48))]),
]


def main():
    hits = []
    for name, dests, follow in CASES:
        print(f"\n===== {name} dests={dests} =====", flush=True)
        sess, data, lv0 = boot_l2()
        d0, _, _ = dump(data, "start")
        data, ok, placed = plant_pair(sess, data, dests)
        if not ok or "frame" not in data:
            print("SOFT plant", flush=True)
            continue
        d1, free, _ = dump(data, "planted")
        tag = "IMPROVED" if d1 < d0 else ("FLAT" if d1 == d0 else "WORSE")
        print(f"  plant-result {tag} d14 {d0}->{d1} placed={placed} n={len(free)}", flush=True)
        if follow:
            data, st = try_follow(sess, data, follow)
            if st == "dead":
                print("DEAD follow", flush=True)
                continue
            if st != "ok":
                print(f"SOFT follow {st}", flush=True)
            if "frame" in data:
                d2, free2, _ = dump(data, "final")
                tag2 = "IMPROVED" if d2 < d0 else ("FLAT" if d2 == d0 else "WORSE")
                beat = " BEAT25" if d2 < 25 else ""
                print(
                    f"RESULT {tag2}{beat} {name} d14 {d0}->{d2} "
                    f"bud={step_budget(data['frame'])} free={sorted(free2)}",
                    flush=True,
                )
                hits.append((tag2, name, d0, d2, step_budget(data["frame"]), len(free2)))
                if (data.get("levels_completed") or 0) >= 3:
                    print("PASS L3!", flush=True)
                continue
        if "frame" in data:
            beat = " BEAT25" if d1 < 25 else ""
            print(
                f"RESULT {tag}{beat} {name} d14 {d0}->{d1} "
                f"bud={step_budget(data['frame'])} free={sorted(free)}",
                flush=True,
            )
            hits.append((tag, name, d0, d1, step_budget(data["frame"]), len(free)))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    best = sorted(
        [h for h in hits if h[0] in ("IMPROVED", "PASS")],
        key=lambda x: (x[3], -x[4], -x[5]),
    )
    print("BEST", best[:8] or "none", flush=True)
    print(
        "BEAT25",
        [h for h in hits if isinstance(h[3], int) and h[3] < 25] or "none",
        flush=True,
    )


if __name__ == "__main__":
    main()
