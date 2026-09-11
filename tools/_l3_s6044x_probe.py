"""From S6044 pose free~(48,32)+(60,44) d14≈30 bud≈11: try goal approaches without N6038."""
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
    return d14, free, fr15


def to_s6044(sess, data):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lag = min(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lag, (36, 44), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (48, 32), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, (60, 44), fr15)
    print(f"  S6044 {st} bud={step_budget(data['frame'])}", flush=True)
    return data, st == "moved"


def boot():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_s6044x"]},
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
    data, ok = to_s6044(sess, data)
    if not ok:
        return sess, data, False
    dump(data, "S6044")
    return sess, data, True


PLANS = [
    ("N5238-S5248", [("N", (52, 38)), ("S", (52, 48))]),
    ("N5238-S5553", [("N", (52, 38)), ("S", (55, 53))]),
    ("N5638-S5553", [("N", (56, 38)), ("S", (55, 53))]),
    ("vacE-S5553", [("E", (52, 58)), ("S", (55, 53))]),
    ("vacE-S5252", [("E", (52, 58)), ("S", (52, 52))]),
    ("vacE-S5052", [("E", (52, 58)), ("S", (50, 52))]),
    ("vacE-N5238-S5553", [("E", (52, 58)), ("N", (52, 38)), ("S", (55, 53))]),
    ("S5248", [("S", (52, 48))]),
    ("S5448", [("S", (54, 48))]),
    ("S5550", [("S", (55, 50))]),
    ("S4850", [("S", (48, 50))]),
    ("N4838-S5550", [("N", (48, 38)), ("S", (55, 50))]),
    ("N5238-S6048", [("N", (52, 38)), ("S", (60, 48))]),
    ("N6038", [("N", (60, 38))]),  # baseline
]


def main():
    hits = []
    for name, steps in PLANS:
        print(f"\n===== {name} =====", flush=True)
        sess, data, ok = boot()
        if not ok:
            print("boot fail", flush=True)
            continue
        d0, free, fr15 = dump(data, "start")
        failed = False
        for who, tgt in steps:
            if "frame" not in data or step_budget(data["frame"]) < 3:
                print("budout", flush=True)
                failed = True
                break
            fr15 = lock_other_ship(data["frame"], 14)
            free = count_free14(data["frame"], fr15)
            if len(free) < 2:
                print(f"n={len(free)}", flush=True)
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
        if failed or "frame" not in data:
            continue
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        d1 = abs(me14["c"][0] - 55) + abs(me14["c"][1] - 53)
        me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
        d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
        free2 = count_free14(data["frame"], lock_other_ship(data["frame"], 14))
        tag = "IMPROVED" if d1 < d0 else ("FLAT" if d1 == d0 else "WORSE")
        print(
            f"RESULT {tag} {name} d14 {d0}->{d1} d15={d15} "
            f"bud={step_budget(data['frame'])} free={sorted(free2)}",
            flush=True,
        )
        hits.append((tag, name, d0, d1, d15, step_budget(data["frame"])))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    best = sorted([h for h in hits if h[0] == "IMPROVED"], key=lambda x: (x[3], -x[5]))
    print("BEST IMPROVED", best[:5] or "none", flush=True)


if __name__ == "__main__":
    main()
