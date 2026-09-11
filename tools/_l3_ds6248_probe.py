"""After N4832: try direct S6248 (skip N6038); also S6044→S6248; budget variants.

Goal: land south of y44 with bud≥6 so we can keep pushing toward (55,53).
"""
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


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me['c']} d14={d14} free={sorted(free)} n={len(free)} "
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} "
        f"bud={step_budget(data['frame'])} lv={data.get('levels_completed')}",
        flush=True,
    )
    return d14, d15, free, fr15, step_budget(data["frame"])


def open_to_gate():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_ds6248"]},
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
    return sess, data


def deep15(sess, data):
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    print(f"  E5842 {st} bud={step_budget(data['frame'])}", flush=True)
    if st != "moved":
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    print(f"  W4250 {st} bud={step_budget(data['frame'])}", flush=True)
    if st != "moved":
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    east = max(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
    data, _, st = move_wp(sess, data, east, (58, 54), freeze14)
    print(f"  E5854 {st} bud={step_budget(data['frame'])}", flush=True)
    return data, st == "moved"


def to_n4832(sess, data, *, skip_ny=False, big_ext=False):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) != 2:
        return data, False
    lag = min(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lag, (26, 44), fr15)
    print(f"  lagSE {st} bud={step_budget(data['frame'])}", flush=True)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    src = (26, 44) if (26, 44) in free else max(free, key=lambda w: (w[1], w[0]))
    ext = (40, 44) if big_ext else (36, 44)
    # try big_ext with fallbacks
    for et in ((ext,) if not big_ext else ((40, 44), (38, 44), (36, 44))):
        others = [w for w in free if w != src]
        if near_any(et, list(fr15), cheb=5):
            continue
        if any(cheb(et, o) < 5 for o in others):
            continue
        data, _, st = move_wp(sess, data, src, et, fr15)
        print(f"  extE {src}->{et} {st} bud={step_budget(data['frame'])}", flush=True)
        if st == "moved":
            break
        if st == "dead" or data.get("state") == "GAME_OVER":
            return data, False
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        src = max(free, key=lambda w: (w[1], w[0]))
    else:
        return data, False

    if not skip_ny:
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        north = min(free, key=lambda w: (w[1], w[0]))
        data, _, st = move_wp(sess, data, north, (46, 36), fr15)
        print(f"  Ny46 {st} bud={step_budget(data['frame'])}", flush=True)
        if st != "moved":
            return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    for nt in ((48, 32), (50, 32), (46, 32)):
        if cheb(nt, south) < 5 or near_any(nt, list(fr15), cheb=5):
            continue
        data, _, st = move_wp(sess, data, north, nt, fr15)
        print(f"  N4832 {north}->{nt} {st} bud={step_budget(data['frame'])}", flush=True)
        if st == "moved":
            dump(data, "N4832")
            return data, True
        if st == "dead" or data.get("state") == "GAME_OVER":
            return data, False
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) < 2:
            return data, False
        north = min(free, key=lambda w: (w[1], w[0]))
        south = max(free, key=lambda w: (w[1], w[0]))
    return data, False


def try_move(sess, data, who, tgt):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        print(f"  flock n={len(free)}", flush=True)
        return data, "flock"
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    cur = north if who == "N" else south
    other = south if who == "N" else north
    if cheb(tgt, other) < 5:
        print(f"  {who}->{tgt} merge", flush=True)
        return data, "merge"
    if near_any(tgt, list(fr15), cheb=5):
        print(f"  {who}->{tgt} near15", flush=True)
        return data, "near15"
    if cheb(tgt, cur) <= 1:
        print(f"  {who}->{tgt} tiny", flush=True)
        return data, "tiny"
    data, newc, st = move_wp(sess, data, cur, tgt, fr15)
    bud = step_budget(data["frame"]) if "frame" in data else -1
    print(f"  {who} {cur}->{tgt} {st}->{newc} bud={bud}", flush=True)
    if st == "dead" or data.get("state") == "GAME_OVER":
        return data, "dead"
    if st != "moved":
        return data, st
    return data, "moved"


# Plans: name, prep kwargs, steps after N4832
PLANS = [
    (
        "direct-S6248",
        {},
        [("S", (62, 48)), ("S", (60, 50)), ("S", (58, 50)), ("N", (56, 42)), ("N", (54, 42))],
    ),
    (
        "direct-S6048",
        {},
        [("S", (60, 48)), ("S", (62, 48)), ("N", (56, 42))],
    ),
    (
        "direct-S6250",
        {},
        [("S", (62, 50)), ("S", (60, 50)), ("S", (62, 48))],
    ),
    (
        "S6044-then-S6248",
        {},
        [("S", (60, 44)), ("S", (62, 48)), ("S", (60, 50)), ("N", (56, 42))],
    ),
    (
        "S6044-N6038-S6248",  # baseline chain
        {},
        [("S", (60, 44)), ("N", (60, 38)), ("S", (62, 48)), ("S", (60, 50))],
    ),
    (
        "bigext-direct-S6248",
        {"big_ext": True},
        [("S", (62, 48)), ("S", (60, 50))],
    ),
    (
        "skipny-S6044-S6248",
        {"skip_ny": True},
        [("S", (60, 44)), ("S", (62, 48))],
    ),
]


def main():
    summary = []
    for name, prep, steps in PLANS:
        print(f"\n===== {name} =====", flush=True)
        sess, data = open_to_gate()
        data, ok = deep15(sess, data)
        if not ok:
            print("deep fail", flush=True)
            summary.append((name, "deep-fail", None, None, None))
            continue
        data, ok = to_n4832(sess, data, **prep)
        if not ok:
            dump(data, "n4832-fail")
            summary.append((name, "n4832-fail", None, None, None))
            continue
        d0, d15_0, _, _, bud0 = dump(data, "start")
        best = (d0, d15_0, bud0)
        failed = False
        for who, tgt in steps:
            if step_budget(data["frame"]) < 3:
                print("budout", flush=True)
                break
            data, st = try_move(sess, data, who, tgt)
            if st == "dead":
                failed = True
                break
            if st != "moved":
                continue
            d14, d15, free, _, bud = dump(data, f"after-{tgt}")
            if d14 < best[0] or (d14 == best[0] and d15 < best[1]) or (
                d14 == best[0] and d15 == best[1] and bud > best[2]
            ):
                best = (d14, d15, bud)
            if len(free) != 2:
                print(f"  warn n={len(free)}", flush=True)
        tag = "dead" if failed else "ok"
        summary.append((name, tag, best[0], best[1], best[2]))
        print(f"BEST {name} d14={best[0]} d15={best[1]} bud={best[2]}", flush=True)

    print("\n===== SUMMARY =====", flush=True)
    for row in summary:
        print(row, flush=True)


if __name__ == "__main__":
    main()
