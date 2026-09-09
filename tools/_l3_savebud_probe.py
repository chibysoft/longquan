"""Arrive at Ne(45,36) with more bud: skip 4250 / skip 4842 staging / 15-first."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, haul15_toward, lock_other_ship, near_any
from tools.r11l_seated_clear import clear_l1, reset


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me['c']} d14={d14} free={sorted(free)} "
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
        json={"tags": ["r11l_savebud"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    data, _ = advance_14_mid_east(sess, data, data.get("levels_completed") or 0, do_clear15=False)
    return sess, data


def stage15(sess, data, do_4842=True, do_4250=True, do_5850=True):
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    print(f"5842 {st} bud={step_budget(data['frame'])}", flush=True)
    if do_4842:
        freeze14 = lock_other_ship(data["frame"], 15)
        data, _, st = move_wp(
            sess,
            data,
            min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]),
            (48, 42),
            freeze14,
        )
        print(f"4842 {st} bud={step_budget(data['frame'])}", flush=True)
    if do_4250:
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        data, _, st = move_wp(sess, data, min(flock, key=lambda w: w[0]), (42, 50), freeze14)
        print(f"4250 {st} bud={step_budget(data['frame'])}", flush=True)
    if do_5850:
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        data, _, st = move_wp(sess, data, max(flock, key=lambda w: w[0]), (58, 50), freeze14)
        print(f"5850 {st} bud={step_budget(data['frame'])}", flush=True)
    return data


def frog_se_ne(sess, data):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) != 2:
        print(f"bad free n={len(free)}", flush=True)
        return data, False
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print(f"leadS {st}", flush=True)
    if st == "dead":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    print(f"frog {st}", flush=True)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (40, 36), fr15)
    print(f"Ny36 {st}", flush=True)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    # Prefer direct SE
    for tgt in ((48, 42), (40, 44)):
        if near_any(tgt, list(fr15), cheb=5):
            continue
        others = [w for w in free if w != s]
        if any(max(abs(tgt[0] - o[0]), abs(tgt[1] - o[1])) < 5 for o in others):
            continue
        data, _, st = move_wp(sess, data, s, tgt, fr15)
        print(f"S {tgt} {st}", flush=True)
        if st == "dead":
            return data, False
        if st == "moved":
            break
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        dump(data, "n1")
        return data, False
    south = max(free, key=lambda w: (w[0], w[1]))
    north = min(free, key=lambda w: (w[1], w[0]))
    if south[0] >= 46:
        data, _, st = move_wp(sess, data, north, (45, 36), fr15)
        print(f"Ne {st}", flush=True)
    dump(data, "done")
    return data, True


def scan_few(sess, data):
    d0, free, fr15 = dump(data, "scan")
    cands = [
        ((45, 36), (50, 38)),
        ((45, 36), (48, 40)),
        ((45, 36), (50, 40)),
        ((48, 42), (52, 44)),
        ((48, 42), (50, 46)),
        ((48, 42), (54, 48)),
        ((45, 36), (48, 36)),
    ]
    for cur0, ld in cands:
        if step_budget(data["frame"]) < 3:
            print("budout", flush=True)
            return
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if cur0 not in free:
            continue
        if near_any(ld, list(fr15), cheb=5):
            continue
        others = [w for w in free if w != cur0]
        if any(max(abs(ld[0] - o[0]), abs(ld[1] - o[1])) < 5 for o in others):
            continue
        data, newc, st = move_wp(sess, data, cur0, ld, fr15)
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(
            f"  {cur0}->{ld} {st}->{newc} ship={me['c']} d14={d14}({d14-d0:+d}) "
            f"bud={step_budget(data['frame'])}",
            flush=True,
        )
        if st == "dead":
            print("DEAD", flush=True)
            return
        if st == "moved" and d14 < d0:
            print("IMPROVED", flush=True)
            dump(data, "HIT")
            return
        if st == "moved":
            d0 = d14
            dump(data, "moved")
            return


def main():
    # A: baseline (expect bud~4)
    print("\n===== A baseline =====", flush=True)
    sess, data = boot_l2()
    data = stage15(sess, data, True, True, True)
    data, ok = frog_se_ne(sess, data)
    if ok:
        scan_few(sess, data)

    # B: skip 4250 — frog under 4842+5850?
    print("\n===== B skip4250 =====", flush=True)
    sess, data = boot_l2()
    data = stage15(sess, data, True, False, True)
    data, ok = frog_se_ne(sess, data)
    if ok:
        scan_few(sess, data)

    # C: skip 4842 — only 5842 then 5850? need west somehow
    print("\n===== C skip4842 keep4250 =====", flush=True)
    sess, data = boot_l2()
    # 5842, then west from wherever to 4250, then 5850
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, _ = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, min(flock, key=lambda w: w[0]), (42, 50), freeze14)
    print(f"direct4250 {st} bud={step_budget(data['frame'])}", flush=True)
    if st == "moved":
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        data, _, _ = move_wp(sess, data, max(flock, key=lambda w: w[0]), (58, 50), freeze14)
        data, ok = frog_se_ne(sess, data)
        if ok:
            scan_few(sess, data)

    # D: haul15 after mid-east before frog (spend ~8 on 15)
    print("\n===== D haul15 then shallow frog =====", flush=True)
    sess, data = boot_l2()
    g15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    # goal hardcoded
    data, _ = haul15_toward(sess, data, (34, 57), max_step=6, label="15pre")
    dump(data, "after-haul")
    data = stage15(sess, data, True, True, True)
    data, ok = frog_se_ne(sess, data)
    if ok:
        scan_few(sess, data)


if __name__ == "__main__":
    main()
