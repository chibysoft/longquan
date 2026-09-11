"""Continue from S5242 / S5642 poses toward goal (no x60)."""
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
from tools._l3_n4832g_probe import to_n4832


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me14["c"][0] - 55) + abs(me14["c"][1] - 53)
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me14['c']} d14={d14} free={sorted(free)} "
        f"d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14


def boot(first_s):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_s52x"]},
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
    data, ok = to_n4832(sess, data)
    if not ok:
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, first_s, fr15)
    print(f"  firstS {first_s} {st} bud={step_budget(data['frame'])}", flush=True)
    if st != "moved":
        return sess, data, False
    dump(data, f"S{first_s}")
    return sess, data, True


PLANS = [
    ((52, 42), "S5248", [("S", (52, 48))]),
    ((52, 42), "S5250", [("S", (52, 50))]),
    ((52, 42), "S5550", [("S", (55, 50))]),
    ((52, 42), "vacE-S5553", [("E", (52, 58)), ("S", (55, 53))]),
    ((52, 42), "vacE-S5252", [("E", (52, 58)), ("S", (52, 52))]),
    ((52, 42), "N4536-S5550", [("N", (45, 36)), ("S", (55, 50))]),
    ((52, 42), "N4836-S5248", [("N", (48, 36)), ("S", (52, 48))]),
    ((52, 42), "S5248-S5553", [("S", (52, 48)), ("S", (55, 53))]),
    ((56, 42), "S5648", [("S", (56, 48))]),
    ((56, 42), "S5650", [("S", (56, 50))]),
    ((56, 42), "vacE-S5553", [("E", (52, 58)), ("S", (55, 53))]),
    ((56, 42), "S5648-S5553", [("S", (56, 48)), ("S", (55, 53))]),
    ((56, 42), "N5238-S5648", [("N", (52, 38)), ("S", (56, 48))]),
]


def main():
    hits = []
    for first, name, steps in PLANS:
        print(f"\n===== {first}-{name} =====", flush=True)
        sess, data, ok = boot(first)
        if not ok:
            print("boot fail", flush=True)
            continue
        d0 = dump(data, "start")
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
            if who == "E":
                flock = [c for c in fr15 if c not in (north, south)] or list(fr15)
                cur = next(
                    (c for c in flock if c in ((58, 54), (58, 50))),
                    max(flock, key=lambda w: w[1]),
                )
                lock = [north, south]
            else:
                cur = south if who == "S" else north
                other = north if who == "S" else south
                if cheb(tgt, other) < 5:
                    print(f"  {who}->{tgt} merge", flush=True)
                    failed = True
                    break
                if near_any(tgt, list(fr15), cheb=5):
                    print(f"  {who}->{tgt} near15", flush=True)
                    failed = True
                    break
                lock = fr15
            data, newc, st = move_wp(sess, data, cur, tgt, lock)
            print(
                f"  {who} {cur}->{tgt} {st}->{newc} "
                f"bud={step_budget(data['frame']) if 'frame' in data else '?'}",
                flush=True,
            )
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
            continue
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        d1 = abs(me14["c"][0] - 55) + abs(me14["c"][1] - 53)
        tag = "IMPROVED" if d1 < d0 else ("FLAT" if d1 == d0 else "WORSE")
        free2 = count_free14(data["frame"], lock_other_ship(data["frame"], 14))
        print(
            f"RESULT {tag} {name} d14 {d0}->{d1} "
            f"bud={step_budget(data['frame'])} free={sorted(free2)}",
            flush=True,
        )
        hits.append((tag, name, first, d0, d1, step_budget(data["frame"])))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    best = sorted([h for h in hits if h[0] == "IMPROVED"], key=lambda x: (x[4], -x[5]))
    print("BEST", best[:8] or "none", flush=True)


if __name__ == "__main__":
    main()
