"""A: zigzag 15 toward goal (no frog). B: shallow frog then post-vacate+scan (safe bans)."""
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
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, d15, free, fr15


def boot(sess):
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    lv0 = data.get("levels_completed") or 0
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
    return data


def base15(sess, data):
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    print(f"e1 {st}", flush=True)
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (48, 42), freeze14
    )
    print(f"w1 {st}", flush=True)
    return data, st in ("moved", "already")


def zig_west(sess, data, hops):
    for tgt in hops:
        if step_budget(data["frame"]) < 6:
            print("budout zig", flush=True)
            break
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        west = min(flock, key=lambda w: w[0])
        east = max(flock, key=lambda w: w[0])
        if cheb(tgt, east) < 5 or near_any(tgt, list(freeze14), cheb=5):
            print(f"skip {tgt}", flush=True)
            continue
        data, newc, st = move_wp(sess, data, west, tgt, freeze14)
        print(f"zig {west}->{tgt} {st}->{newc} bud={step_budget(data['frame'])}", flush=True)
        if st == "dead":
            print("15DEAD", flush=True)
            return data, False
        if st == "moved":
            dump(data, f"after-{newc}")
    return data, True


def try14_from_mid(sess, data):
    """From mid-east 2wp with deep15: try SE leads without frog."""
    d0, _, free, fr15 = dump(data, "mid14")
    if len(free) < 2:
        return data, None
    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])
    cands = [
        (lead, (lead[0], lead[1] + 4)),
        (lead, (lead[0] + 2, lead[1] + 4)),
        (lead, (lead[0] + 4, lead[1] + 2)),
        (lead, (38, 40)),
        (lead, (40, 40)),
        (lead, (36, 40)),
        (lead, (40, 36)),
        (lag, (lag[0] + 4, lag[1] + 4)),
        (lag, (lag[0] + 2, lead[1] + 4)),
        (lag, (30, 40)),
        (lag, (28, 40)),
    ]
    for cur, ld in cands:
        if step_budget(data["frame"]) < 4:
            break
        other = lead if cur == lag else lag
        if cheb(ld, other) < 5:
            continue
        if near_any(ld, list(fr15), cheb=5):
            print(f"skip near15 {ld}", flush=True)
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        free2 = count_free14(data["frame"], lock_other_ship(data["frame"], 14))
        print(
            f"  14 {cur}->{ld} {st}->{newc} ship={me['c']} d14={d14}({d14-d0:+d}) "
            f"n={len(free2)} bud={step_budget(data['frame'])}",
            flush=True,
        )
        if st == "dead":
            print("DEAD", flush=True)
            return data, "dead"
        if st == "moved":
            dump(data, "HIT14")
            if d14 < d0 and len(free2) >= 2:
                return data, "improved"
            if len(free2) < 2:
                print("n1 after move", flush=True)
                return data, "n1"
            # refresh and continue chaining
            d0 = d14
            fr15 = lock_other_ship(data["frame"], 14)
            free = count_free14(data["frame"], fr15)
            if len(free) >= 2:
                lead = max(free, key=lambda w: w[0])
                lag = min(free, key=lambda w: w[0])
            return data, "moved"
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) >= 2:
            lead = max(free, key=lambda w: w[0])
            lag = min(free, key=lambda w: w[0])
    return data, None


def frog_shallow(sess, data):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (40, 36), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    if not near_any((40, 44), list(fr15), cheb=5) and cheb((40, 44), n) >= 5:
        data, _, st = move_wp(sess, data, s, (40, 44), fr15)
        if st == "dead":
            return data, False
    return data, True


def safe_scan(sess, data):
    d0, _, free, fr15 = dump(data, "safe-scan")
    if len(free) < 2:
        return data, None
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    # Ban known dead from (40,36): (46,40); S y44 east; same-col N south
    ban = {
        (46, 40),
        (42, 40),
        (42, 42),
        (42, 45),
        (42, 46),
        (41, 44),
        (42, 44),
        (43, 44),
        (43, 40),
        (43, 42),
    }
    cands = [
        (n, (43, 38)),
        (n, (44, 38)),
        (n, (45, 40)),
        (n, (44, 40)),
        (n, (42, 38)),
        (n, (41, 38)),
        (s, (40, 46)),
        (s, (42, 46)),
        (s, (38, 46)),
        (s, (38, 44)),
        (s, (36, 44)),
        (n, (42, 36)),
        (n, (38, 36)),
    ]
    for cur, ld in cands:
        if step_budget(data["frame"]) < 4:
            break
        if ld in ban or ld == cur:
            continue
        if near_any(ld, list(fr15), cheb=5):
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

    # Part A: zigzag 15 hard, then mid14 tries
    print("===== A zig15 then mid14 =====", flush=True)
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_zigA"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    data = boot(sess)
    data, ok = base15(sess, data)
    if not ok:
        print("basefail", flush=True)
        return
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, min(flock, key=lambda w: w[0]), (42, 50), freeze14)
    print(f"w2 {st}", flush=True)
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(flock, key=lambda w: w[0]), (58, 50), freeze14)
    print(f"e2 {st}", flush=True)
    data, ok = zig_west(
        sess,
        data,
        [
            (38, 52),
            (42, 54),
            (38, 50),
            (36, 52),
            (34, 54),
            (36, 54),
            (34, 56),
            (32, 54),
            (34, 57),
            (36, 56),
            (40, 56),
            (38, 54),
            (42, 56),
        ],
    )
    if not ok:
        return
    dump(data, "zig-done")
    data, res = try14_from_mid(sess, data)
    print(f"A result={res}", flush=True)
    if res in ("improved", "moved"):
        print("SUCCESS A", flush=True)
        return

    # Part B: shallow 4842 only → frog → vacate → safe scan
    print("\n===== B shallow frog + post vac =====", flush=True)
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_shB"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    data = boot(sess)
    data, ok = base15(sess, data)
    if not ok:
        return
    dump(data, "pre-frog-shallow")
    data, ok = frog_shallow(sess, data)
    if not ok:
        print("frogfail", flush=True)
        return
    dump(data, "post-frog")
    # post vacate with remaining bud
    if step_budget(data["frame"]) >= 8:
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        west = min(flock, key=lambda w: w[0])
        east = max(flock, key=lambda w: w[0])
        if east[0] < 56:
            data, _, st = move_wp(sess, data, east, (58, 50), freeze14)
            print(f"post-e {st}", flush=True)
            freeze14 = lock_other_ship(data["frame"], 15)
            flock = list(lock_other_ship(data["frame"], 14))
            west = min(flock, key=lambda w: w[0])
            east = max(flock, key=lambda w: w[0])
        for tgt in ((42, 50), (38, 52), (48, 50)):
            if step_budget(data["frame"]) < 6:
                break
            if cheb(tgt, east) < 5 or near_any(tgt, list(freeze14), cheb=5):
                continue
            data, newc, st = move_wp(sess, data, west, tgt, freeze14)
            print(f"post-w {west}->{tgt} {st}->{newc}", flush=True)
            if st == "dead":
                print("15DEAD", flush=True)
                return
            if st == "moved":
                freeze14 = lock_other_ship(data["frame"], 15)
                flock = list(lock_other_ship(data["frame"], 14))
                west = min(flock, key=lambda w: w[0])
                east = max(flock, key=lambda w: w[0])
                break
    data, res = safe_scan(sess, data)
    print(f"B result={res}", flush=True)
    if res in ("improved", "moved"):
        print("SUCCESS B", flush=True)
        return
    dump(data, "end")
    print("done", flush=True)


if __name__ == "__main__":
    main()
