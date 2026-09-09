"""Save more bud: skip 5850 / direct S→(48,42); continue from (40,36)+(48,42)."""
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


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def boot(do_5850=True, do_4250=True):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_se48"]},
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
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, _ = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, _ = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (48, 42), freeze14
    )
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
    dump(data, "pre-frog")
    # frog
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print(f"leadS {st}", flush=True)
    if st == "dead":
        return sess, data, "dead"
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    print(f"frog {st}", flush=True)
    if st == "dead":
        return sess, data, "dead"
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (40, 36), fr15)
    print(f"Ny36 {st}", flush=True)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, s, (40, 44), fr15)
    print(f"S4044 {st}", flush=True)
    if st != "moved":
        dump(data, "Sfail")
        return sess, data, "Sfail"
    dump(data, "postS")
    return sess, data, "ok"


CURATED = (
    (45, 40),
    (48, 42),
    (50, 42),
    (48, 44),
    (50, 44),
    (52, 44),
    (48, 46),
    (50, 46),
    (52, 46),
    (48, 48),
    (50, 48),
    (52, 48),
    (54, 48),
    (45, 44),
    (45, 46),
    (43, 38),
    (46, 42),
    (44, 42),
    (50, 40),
    (52, 40),
    (48, 40),
    (50, 50),
    (52, 50),
    (54, 50),
    (52, 52),
    (48, 50),
    (44, 48),
    (40, 48),
    (42, 48),
)


def chain(sess, data, path_labels):
    """Try a fixed chain of (prefer_east_wp, ld) moves."""
    for label, ld in path_labels:
        if step_budget(data["frame"]) < 3:
            print("budout", flush=True)
            return data
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        # prefer easternmost free for SE chain
        cur = max(free, key=lambda w: (w[0], w[1]))
        if near_any(ld, list(fr15), cheb=5):
            print(f"{label} {ld} near15 skip", flush=True)
            continue
        others = [w for w in free if w != cur]
        if any(cheb(ld, o) < 5 for o in others):
            print(f"{label} {ld} merge skip", flush=True)
            continue
        d0, _, _ = dump(data, f"pre-{label}")
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(
            f"{label} {cur}->{ld} {st}->{newc} ship={me['c']} d14={d14}({d14-d0:+d}) "
            f"bud={step_budget(data['frame'])}",
            flush=True,
        )
        if st == "dead":
            print("DEAD", flush=True)
            return data
        if st != "moved":
            return data
    dump(data, "chain-end")
    return data


def scan_from(sess, data, max_noops=5):
    d0, free, fr15 = dump(data, "scan")
    ordered = sorted(free, key=lambda w: (-w[0], -w[1]))
    noops = 0
    for cur in ordered:
        for ld in CURATED:
            if step_budget(data["frame"]) < 3:
                print("budout", flush=True)
                return data
            if ld == cur or near_any(ld, list(fr15), cheb=5):
                continue
            others = [w for w in free if w != cur]
            if any(cheb(ld, o) < 5 for o in others):
                continue
            if ld in {(46, 40), (42, 40), (42, 42), (42, 45), (42, 46), (43, 40), (43, 42)}:
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
                return data
            if st == "moved":
                dump(data, "HIT")
                if d14 < d0:
                    print("IMPROVED", flush=True)
                return data
            noops += 1
            fr15 = lock_other_ship(data["frame"], 14)
            free = count_free14(data["frame"], fr15)
            if noops >= max_noops:
                return data
    return data


def main():
    # A: stop4250+5850, chain N45→4842→keep scanning
    print("\n===== A stop4250+5850 chain =====", flush=True)
    sess, data, st = boot(do_5850=True, do_4250=True)
    if st == "ok":
        data = chain(sess, data, [("N45", (45, 40)), ("E48", (48, 42)), ("E50", (50, 44)), ("E52", (52, 46))])

    # B: skip 5850 — save 3 bud
    print("\n===== B skip5850 =====", flush=True)
    sess, data, st = boot(do_5850=False, do_4250=True)
    if st == "ok":
        data = chain(sess, data, [("N45", (45, 40)), ("E48", (48, 42)), ("E50", (50, 44)), ("E52", (52, 46))])
        if step_budget(data["frame"]) >= 3:
            scan_from(sess, data)

    # C: skip 4250 and 5850 — frog under 4842+5842
    print("\n===== C shallow15 =====", flush=True)
    sess, data, st = boot(do_5850=False, do_4250=False)
    if st == "ok":
        data = chain(sess, data, [("N45", (45, 40)), ("E48", (48, 42))])
        if step_budget(data["frame"]) >= 3:
            scan_from(sess, data)

    # D: stop4250+5850 but S→4842 directly (skip N45)
    print("\n===== D direct S→4842 =====", flush=True)
    sess, data, st = boot(do_5850=True, do_4250=True)
    if st == "ok":
        data = chain(sess, data, [("E48", (48, 42)), ("E50", (50, 44)), ("E52", (52, 46))])
        if step_budget(data["frame"]) >= 3:
            scan_from(sess, data)


if __name__ == "__main__":
    main()
