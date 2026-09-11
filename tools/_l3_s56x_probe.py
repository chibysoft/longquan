"""After N6038+vacE: measure S5648/S5848 d14, then continue scan."""
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
from tools._l3_s6048_probe import deep15
from tools._l3_pre6248_probe import to_n6038

GOAL14 = (55, 53)


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
    print(
        f"{label} ship14={me14['c']} d14={d14} free={sorted(free)} "
        f"fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, free, fr15


def boot_vac():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_s56x"]},
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
    if not ok:
        return sess, data, False
    data, ok = to_n6038(sess, data)
    if not ok:
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    east = next((c for c in fr15 if c in ((58, 54), (58, 50))), max(fr15, key=lambda w: w[1]))
    data, _, st = move_wp(sess, data, east, (48, 58), [north, south])
    print(f"  vacE {st} bud={step_budget(data['frame'])}", flush=True)
    if st != "moved":
        return sess, data, False
    return sess, data, True


PLANS = [
    ("S5648", [("S", (56, 48))]),
    ("S5848", [("S", (58, 48))]),
    ("S5448", [("S", (54, 48))]),
    ("S5248", [("S", (52, 48))]),
    ("S5048", [("S", (50, 48))]),
    ("S5648-N5542", [("S", (56, 48)), ("N", (55, 42))]),
    ("S5648-N5242", [("S", (56, 48)), ("N", (52, 42))]),
    ("S5648-S5452", [("S", (56, 48)), ("S", (54, 52))]),
    ("S5648-S5252", [("S", (56, 48)), ("S", (52, 52))]),
    ("S5648-S5550", [("S", (56, 48)), ("S", (55, 50))]),
    ("S5448-S5550", [("S", (54, 48)), ("S", (55, 50))]),
    ("S5248-S5550", [("S", (52, 48)), ("S", (55, 50))]),
    ("S5048-S5553", [("S", (50, 48)), ("S", (55, 53))]),
    ("S5648-S5448-S5550", [("S", (56, 48)), ("S", (54, 48)), ("S", (55, 50))]),
]


def main():
    hits = []
    for name, steps in PLANS:
        print(f"\n===== {name} =====", flush=True)
        sess, data, ok = boot_vac()
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
            fr15 = lock_other_ship(data["frame"], 14)
            free = count_free14(data["frame"], fr15)
            if len(free) < 2:
                failed = True
                break
            north = min(free, key=lambda w: (w[1], w[0]))
            south = max(free, key=lambda w: (w[1], w[0]))
            cur = south if who == "S" else north
            other = north if who == "S" else south
            if cheb(tgt, other) < 5:
                print(f"  merge {tgt}", flush=True)
                failed = True
                break
            if near_any(tgt, list(fr15), cheb=5):
                print(f"  near15 {tgt}", flush=True)
                failed = True
                break
            data, newc, st = move_wp(sess, data, cur, tgt, fr15)
            print(f"  {who} {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}", flush=True)
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                print("DEAD", flush=True)
                failed = True
                break
            if st != "moved":
                print(f"SOFT {st}", flush=True)
                failed = True
                break
            dump(data, f"after-{tgt}")
        if failed or "frame" not in data:
            # still record partial if we moved once
            continue
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        d1 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
        tag = "IMPROVED" if d1 < d0 else ("FLAT" if d1 == d0 else "WORSE")
        beat = " BEAT25" if d1 < 25 else ""
        print(f"RESULT {tag}{beat} {name} d14 {d0}->{d1} bud={step_budget(data['frame'])}", flush=True)
        hits.append((tag, name, d0, d1, step_budget(data["frame"])))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    print("BEAT25", [h for h in hits if h[3] < 25] or "none", flush=True)


if __name__ == "__main__":
    main()
