"""After mid-east+deep15: vacE first, then SE toward goal column (avoid x60 trap)."""
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


def vacE(sess, data, tgt=(52, 58)):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    freeze14 = list(free) if len(free) >= 2 else list(lock_other_ship(data["frame"], 15))
    flock = list(fr15)
    east = next((c for c in flock if c in ((58, 54), (58, 50))), max(flock, key=lambda w: w[1]))
    west = min(flock, key=lambda w: w[0])
    if max(abs(tgt[0] - west[0]), abs(tgt[1] - west[1])) < 5:
        return data, False
    data, newc, st = move_wp(sess, data, east, tgt, freeze14)
    print(f"  vacE {east}->{tgt} {st}->{newc} bud={step_budget(data['frame'])}", flush=True)
    return data, st == "moved"


def boot(do_vac=True):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_vace1st"]},
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
    dump(data, "deep")
    if do_vac:
        data, ok = vacE(sess, data)
        if not ok:
            return sess, data, False
        dump(data, "vacE")
    return sess, data, True


def step(sess, data, who, tgt):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return data, "nfree"
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])
    if who == "S":
        cur, other = south, north
    elif who == "N":
        cur, other = north, south
    elif who == "L":
        cur, other = lag, lead
    elif who == "R":
        cur, other = lead, lag
    else:
        return data, "badwho"
    if cheb(tgt, other) < 5:
        return data, "merge"
    if near_any(tgt, list(fr15), cheb=5):
        return data, "near15"
    data, newc, st = move_wp(sess, data, cur, tgt, fr15)
    print(f"  {who} {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}", flush=True)
    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, "dead"
    if st != "moved":
        return data, st
    return data, "moved"


PLANS = [
    # After vacE: classic SE but then goal push with open band
    ("lag-N-S60-N60-S6048-S5553", [("L", (36, 44)), ("N", (48, 32)), ("S", (60, 44)), ("N", (60, 38)), ("S", (60, 48)), ("S", (55, 53))]),
    ("lag-N-S60-N60-S6048-S5652", [("L", (36, 44)), ("N", (48, 32)), ("S", (60, 44)), ("N", (60, 38)), ("S", (60, 48)), ("S", (56, 52))]),
    ("lag-N-S60-N60-S6048-S5252", [("L", (36, 44)), ("N", (48, 32)), ("S", (60, 44)), ("N", (60, 38)), ("S", (60, 48)), ("S", (52, 52))]),
    # Goal column earlier
    ("lag-N-S5242-S5248-S5553", [("L", (36, 44)), ("N", (48, 32)), ("S", (52, 42)), ("S", (52, 48)), ("S", (55, 53))]),
    ("lag-N-S5642-S5648-S5553", [("L", (36, 44)), ("N", (48, 32)), ("S", (56, 42)), ("S", (56, 48)), ("S", (55, 53))]),
    ("lag-N-S5550", [("L", (36, 44)), ("N", (48, 32)), ("S", (55, 50))]),
    ("lag-N-S5553", [("L", (36, 44)), ("N", (48, 32)), ("S", (55, 53))]),
    ("lag-R4044-S5550", [("L", (36, 44)), ("R", (40, 44)), ("S", (55, 50))]),
    # Lead-first toward goal from gate
    ("R4044-R4844-S5550", [("R", (40, 44)), ("R", (48, 44)), ("S", (55, 50))]),
    ("R4544-L3044-S5553", [("R", (45, 44)), ("L", (30, 44)), ("S", (55, 53))]),
    ("L2644-R3644-S5242-S5550", [("L", (26, 44)), ("R", (36, 44)), ("S", (52, 42)), ("S", (55, 50))]),
]


def main():
    hits = []
    for name, steps in PLANS:
        print(f"\n===== {name} =====", flush=True)
        sess, data, ok = boot(do_vac=True)
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
            dump(data, f"after-{who}{tgt}")
        if failed or "frame" not in data:
            continue
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        d1 = abs(me14["c"][0] - 55) + abs(me14["c"][1] - 53)
        me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
        d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
        free2 = count_free14(data["frame"], lock_other_ship(data["frame"], 14))
        tag = "IMPROVED" if d1 < d0 else ("FLAT" if d1 == d0 else "WORSE")
        # Also flag if beat frontier d14=25
        beat = " BEAT25" if d1 < 25 else ""
        print(
            f"RESULT {tag}{beat} {name} d14 {d0}->{d1} d15={d15} "
            f"bud={step_budget(data['frame'])} free={sorted(free2)}",
            flush=True,
        )
        hits.append((tag, name, d0, d1, d15, step_budget(data["frame"])))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    beat = [h for h in hits if h[3] < 25]
    print("BEAT25", beat or "none", flush=True)
    best = sorted([h for h in hits if h[0] == "IMPROVED"], key=lambda x: (x[3], -x[5]))
    print("BEST", best[:8] or "none", flush=True)


if __name__ == "__main__":
    main()
