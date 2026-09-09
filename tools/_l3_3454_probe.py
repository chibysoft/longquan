"""Reach west15@(34,54) efficiently; move east15 closer; frog+scan with leftover bud."""
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
        f"{label} ship14={me['c']} d14={d14} free={sorted(free)} "
        f"d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, d15


def boot(sess):
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    lv0 = data.get("levels_completed") or 0
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
    return data


def mv(sess, data, wp, tgt, freeze, label):
    data, newc, st = move_wp(sess, data, wp, tgt, freeze)
    print(f"{label} {wp}->{tgt} {st}->{newc} bud={step_budget(data['frame'])}", flush=True)
    return data, newc, st


def to_3454(sess, data):
    """Proven chain to west@(34,54). Avoid known noops."""
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = mv(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14, "e1")
    if st == "dead":
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = mv(
        sess,
        data,
        min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]),
        (48, 42),
        freeze14,
        "w1",
    )
    if st not in ("moved", "already"):
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    data, _, st = mv(sess, data, min(flock, key=lambda w: w[0]), (42, 50), freeze14, "w2")
    if st != "moved":
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    data, _, st = mv(sess, data, max(flock, key=lambda w: w[0]), (58, 50), freeze14, "e2")
    if st == "dead":
        return data, False
    # Chain: 4250→3852→4254→3850→3454 (skip noop 3652/3654/3456)
    for tgt in ((38, 52), (42, 54), (38, 50), (34, 54)):
        if step_budget(data["frame"]) < 6:
            break
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        west = min(flock, key=lambda w: w[0])
        east = max(flock, key=lambda w: w[0])
        if west[0] <= tgt[0] and west[1] >= tgt[1] and west != (48, 42):
            # rough past-check: if already at 3454 stop
            if west == (34, 54):
                break
        if cheb(tgt, east) < 5 or near_any(tgt, list(freeze14), cheb=5):
            print(f"skip {tgt}", flush=True)
            continue
        if cheb(tgt, west) == 0:
            continue
        data, newc, st = mv(sess, data, west, tgt, freeze14, "wzig")
        if st == "dead":
            return data, False
        if st != "moved":
            continue
    # Try pull east closer toward goal
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    east = max(flock, key=lambda w: w[0])
    for tgt in ((52, 54), (48, 54), (44, 56), (40, 56), (50, 56), (56, 54)):
        if step_budget(data["frame"]) < 6:
            break
        if cheb(tgt, west) < 5 or near_any(tgt, list(freeze14), cheb=5):
            continue
        data, newc, st = mv(sess, data, east, tgt, freeze14, "ezig")
        if st == "dead":
            return data, False
        if st == "moved":
            freeze14 = lock_other_ship(data["frame"], 15)
            flock = list(lock_other_ship(data["frame"], 14))
            west = min(flock, key=lambda w: w[0])
            east = max(flock, key=lambda w: w[0])
            # one success then try more
            continue
    # Final west nudge toward (34,57)
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    east = max(flock, key=lambda w: w[0])
    for tgt in ((34, 56), (34, 57), (32, 56), (36, 56), (34, 55)):
        if step_budget(data["frame"]) < 4:
            break
        if cheb(tgt, east) < 5 or near_any(tgt, list(freeze14), cheb=5):
            continue
        if cheb(tgt, west) == 0:
            continue
        data, newc, st = mv(sess, data, west, tgt, freeze14, "wfin")
        if st == "dead":
            return data, False
        if st == "moved":
            break
    return data, True


def frog(sess, data):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return data, False
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print(f"leadS {st}", flush=True)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return data, False
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    frog_t = (lag[0] + 2, lead[1] + 4)
    if near_any(frog_t, list(fr15), cheb=5):
        print("frog near15", frog_t, flush=True)
        return data, False
    data, _, st = move_wp(sess, data, lag, frog_t, fr15)
    print(f"frog {st}", flush=True)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    if near_any((40, 36), list(fr15), cheb=5):
        print("Ny36 near15", flush=True)
    else:
        data, _, st = move_wp(sess, data, n, (40, 36), fr15)
        print(f"Ny36 {st}", flush=True)
        if st == "dead":
            return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return data, True
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    if not near_any((40, 44), list(fr15), cheb=5) and cheb((40, 44), n) >= 5:
        data, _, st = move_wp(sess, data, s, (40, 44), fr15)
        print(f"S40 {st}", flush=True)
        if st == "dead":
            return data, False
    if step_budget(data["frame"]) >= 8:
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        n = min(free, key=lambda w: (w[1], w[0]))
        s = max(free, key=lambda w: (w[1], w[0]))
        for tgt in ((43, 38), (45, 40), (44, 38)):
            if near_any(tgt, list(fr15), cheb=5) or cheb(tgt, s) < 5:
                continue
            if tgt == (46, 40):
                continue
            data, _, st = move_wp(sess, data, n, tgt, fr15)
            print(f"N {tgt} {st}", flush=True)
            if st == "dead":
                return data, False
            if st == "moved":
                break
    return data, True


def scan(sess, data):
    d0, _ = dump(data, "scan")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return data, None
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    ban = {(46, 40), (42, 40), (42, 42), (42, 45), (42, 46), (41, 44), (42, 44), (43, 44), (43, 40), (43, 42)}
    for cur, ld in (
        (n, (45, 40)),
        (n, (43, 38)),
        (n, (44, 38)),
        (n, (48, 40)),
        (n, (47, 40)),
        (s, (40, 48)),
        (s, (42, 48)),
        (s, (40, 46)),
        (s, (44, 48)),
        (s, (48, 48)),
        (n, (50, 40)),
        (n, (44, 40)),
        (s, (42, 46)),
        (s, (38, 48)),
    ):
        if step_budget(data["frame"]) < 4:
            break
        if ld in ban or near_any(ld, list(fr15), cheb=5):
            if ld not in ban:
                print(f"skip near15 {ld}", flush=True)
            continue
        other = s if cur == n else n
        if cheb(ld, other) < 5:
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
            return data, "dead"
        if st == "moved":
            dump(data, "HIT")
            return data, ("improved" if d14 < d0 else "moved")
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) < 2:
            break
        s = max(free, key=lambda w: (w[1], w[0]))
        n = min(free, key=lambda w: (w[1], w[0]))
    return data, None


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_3454"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    data = boot(sess)
    data, ok = to_3454(sess, data)
    if not ok:
        print("stagefail", flush=True)
        return
    dump(data, "pre-frog")
    # If bud low, try continue 14 lead without full frog
    if step_budget(data["frame"]) < 14:
        print("low bud — leadS only chain", flush=True)
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        lead = max(free, key=lambda w: w[0])
        data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
        print(f"leadS {st}", flush=True)
        dump(data, "after-lead")
        data, res = scan(sess, data)
        print(f"result={res}", flush=True)
        return
    data, ok = frog(sess, data)
    if not ok:
        print("frogfail", flush=True)
        dump(data, "frog-end")
        return
    data, res = scan(sess, data)
    print(f"result={res}", flush=True)
    dump(data, "end")


if __name__ == "__main__":
    main()
