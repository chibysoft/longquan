"""Budget variants: skip 3852 / stop at 4250 / extra zig then frog; scan post-S4046."""
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
        f"d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, free, fr15


def stage_to_4250(sess, data):
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    data, _ = advance_14_mid_east(sess, data, data.get("levels_completed") or 0, do_clear15=False)

    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    print(f"stage 5842 {st} bud={step_budget(data['frame'])}", flush=True)
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (48, 42), freeze14
    )
    print(f"stage 4842 {st} bud={step_budget(data['frame'])}", flush=True)
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, min(flock, key=lambda w: w[0]), (42, 50), freeze14)
    print(f"stage 4250 {st} bud={step_budget(data['frame'])}", flush=True)
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(flock, key=lambda w: w[0]), (58, 50), freeze14)
    print(f"stage 5850 {st} bud={step_budget(data['frame'])}", flush=True)
    return data


def frog_ny_s4046(sess, data, prefer_s46=True):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print(f"leadS {st} bud={step_budget(data['frame'])}", flush=True)
    if st == "dead":
        return data, "dead"
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    print(f"frog {st} bud={step_budget(data['frame'])}", flush=True)
    if st == "dead":
        return data, "dead"
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (40, 36), fr15)
    print(f"Ny36 {st} bud={step_budget(data['frame'])}", flush=True)
    dump(data, "n3")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = min(free, key=lambda w: w[1])  # southernmost often 25,44
    # Prefer explicit (25,44) if present
    for w in free:
        if w[1] >= 44:
            s = w
            break
    tgts = ((40, 46), (40, 44)) if prefer_s46 else ((40, 44), (40, 46))
    west15 = min(fr15, key=lambda w: w[0])
    if west15[1] < 54:
        tgts = ((40, 44), (40, 46))
    for ld in tgts:
        data, newc, st = move_wp(sess, data, s, ld, fr15)
        print(f"S {s}->{ld} {st}->{newc} bud={step_budget(data['frame'])}", flush=True)
        if st == "dead":
            return data, "dead"
        if st == "moved":
            dump(data, "postS")
            return data, "ok"
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        for w in free:
            if w[1] >= 44:
                s = w
                break
    dump(data, "postS-fail")
    return data, "fail"


def scan_exits(sess, data, d0):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    ordered = sorted(free, key=lambda w: (-w[1], -w[0]))
    cands = []
    lds = (
        (43, 38),
        (45, 40),
        (44, 38),
        (48, 40),
        (42, 48),
        (40, 48),
        (44, 48),
        (48, 48),
        (40, 50),
        (44, 46),
        (48, 46),
        (36, 44),
        (38, 44),
        (42, 44),
        (44, 44),
        (48, 44),
        (35, 40),
        (38, 40),
        (44, 40),
        (48, 42),
        (50, 42),
        (50, 48),
        (52, 48),
        (52, 44),
        (36, 48),
        (38, 50),
        (34, 48),
        (30, 48),
        (28, 44),
        (32, 44),
    )
    for wp in ordered:
        for ld in lds:
            cands.append((wp, ld))
    tried = set()
    for cur, ld in cands:
        if step_budget(data["frame"]) < 3:
            print("budout", flush=True)
            break
        if (cur, ld) in tried or ld == cur:
            continue
        tried.add((cur, ld))
        if not (0 <= ld[0] < 64 and 0 <= ld[1] < 64):
            continue
        if ld in {(46, 40), (42, 40), (42, 42), (42, 45), (42, 46), (43, 40), (43, 42), (40, 44)}:
            continue
        if near_any(ld, list(fr15), cheb=5):
            continue
        others = [w for w in free if w != cur]
        if any(cheb(ld, o) < 5 for o in others):
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(
            f"  {cur}->{ld} {st}->{newc} ship={me['c']} d14={d14}({d14-d0:+d}) "
            f"bud={step_budget(data['frame'])}",
            flush=True,
        )
        if st == "dead":
            print("DEAD", flush=True)
            return data, False
        if st == "moved":
            dump(data, "EXIT")
            if d14 < d0:
                print("IMPROVED", flush=True)
            return data, True
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
    return data, False


def run_variant(name, zig_steps):
    print(f"\n===== VARIANT {name} zig={zig_steps} =====", flush=True)
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": [f"r11l_{name}"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    data = stage_to_4250(sess, data)
    for tgt in zig_steps:
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        data, _, st = move_wp(sess, data, min(flock, key=lambda w: w[0]), tgt, freeze14)
        print(f"zig {tgt} {st} bud={step_budget(data['frame'])}", flush=True)
        if st == "dead":
            print("DEAD zig", flush=True)
            return
        dump(data, f"after-{tgt}")
    data, st = frog_ny_s4046(sess, data)
    if st != "ok":
        print(f"frog/S fail {st}", flush=True)
        return
    d0, free, _ = dump(data, "scan-start")
    data, hit = scan_exits(sess, data, d0)
    print(f"variant {name} hit={hit}", flush=True)


def main():
    # A: skip 3852, direct 4254
    run_variant("skip3852", [(42, 54)])
    # B: stop at 4250 (no deeper zig) — S may prefer 4044
    run_variant("stop4250", [])
    # C: baseline 3852+4254 for comparison bud
    run_variant("base4254", [(38, 52), (42, 54)])


if __name__ == "__main__":
    main()
