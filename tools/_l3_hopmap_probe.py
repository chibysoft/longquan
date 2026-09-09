"""Map west15 hops from (42,50); and (48,50) pose S-south safety."""
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


def to_mid_deep(sess, west2=(42, 50), east2=(58, 50)):
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    lv0 = data.get("levels_completed") or 0
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, _ = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, _ = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (48, 42), freeze14
    )
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    east = max(flock, key=lambda w: w[0])
    if west2:
        data, newc, st = move_wp(sess, data, west, west2, freeze14)
        print(f"w2 {west}->{west2} {st}->{newc}", flush=True)
        if st == "dead":
            return data, False
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        west = min(flock, key=lambda w: w[0])
        east = max(flock, key=lambda w: w[0])
    if east2:
        data, newc, st = move_wp(sess, data, east, east2, freeze14)
        print(f"e2 {east}->{east2} {st}->{newc}", flush=True)
        if st == "dead":
            return data, False
    return data, True


def frog_no_n(sess, data):
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


def main():
    key = _api_key()

    # Part A: hop map from (42,50)
    print("===== hopmap from 4250 =====", flush=True)
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_hop"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    data, ok = to_mid_deep(sess, (42, 50), (58, 50))
    if not ok:
        print("setupfail", flush=True)
        return
    dump(data, "at4250")
    tgts = [
        (40, 52),
        (38, 52),
        (42, 54),
        (44, 54),
        (36, 50),
        (38, 50),
        (40, 50),
        (44, 50),
        (42, 52),
        (38, 54),
        (36, 52),
        (34, 52),
        (40, 54),
        (45, 52),
        (48, 54),
    ]
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    east = max(flock, key=lambda w: w[0])
    for tgt in tgts:
        # fresh card each hop to avoid dead ending — reopen
        sess2 = OnlineSession(key)
        r2 = sess2.s.post(
            f"{BASE}/api/scorecard/open",
            headers=sess2._headers(True),
            json={"tags": ["r11l_hop2"]},
            timeout=90,
        )
        sess2.card_id = r2.json()["card_id"]
        sess2.game_id = "r11l-495a7899"
        d2, ok = to_mid_deep(sess2, (42, 50), (58, 50))
        if not ok:
            print(f"{tgt} setupfail", flush=True)
            continue
        freeze14 = lock_other_ship(d2["frame"], 15)
        flock = list(lock_other_ship(d2["frame"], 14))
        west = min(flock, key=lambda w: w[0])
        east = max(flock, key=lambda w: w[0])
        if cheb(tgt, east) < 5:
            print(f"{tgt} merge", flush=True)
            continue
        if near_any(tgt, list(freeze14), cheb=5):
            print(f"{tgt} near14", flush=True)
            continue
        d2, newc, st = move_wp(sess2, d2, west, tgt, freeze14)
        print(f"hop {west}->{tgt} {st}->{newc} bud={step_budget(d2['frame'])}", flush=True)
        if st == "moved":
            dump(d2, f"HIT15-{tgt}")
            # one success is enough to know path; continue mapping

    # Part B: (48,50) frog + S try
    print("\n===== pose 4850 S-scan =====", flush=True)
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_4850"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    data, ok = to_mid_deep(sess, (48, 50), (58, 50))
    if not ok:
        print("4850fail", flush=True)
        return
    dump(data, "pre4850")
    data, ok = frog_no_n(sess, data)
    if not ok:
        print("frogfail", flush=True)
        return
    dump(data, "scan4850")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    d0 = abs(next(z for z in ships(data["frame"]) if z["chrome"] == 14)["c"][0] - 55) + abs(
        next(z for z in ships(data["frame"]) if z["chrome"] == 14)["c"][1] - 53
    )
    for cur, ld in (
        (s, (40, 46)),
        (s, (42, 46)),
        (s, (38, 46)),
        (s, (40, 48)),
        (s, (42, 48)),
        (n, (43, 38)),
        (n, (45, 40)),
        (n, (44, 38)),
    ):
        if step_budget(data["frame"]) < 4:
            break
        if near_any(ld, list(fr15), cheb=5):
            print(f"skip near15 {ld}", flush=True)
            continue
        if cheb(ld, n if cur == s else s) < 5:
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
            break
        if st == "moved":
            dump(data, "HIT14")
            print("SUCCESS", flush=True)
            return
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) != 2:
            break
        s = max(free, key=lambda w: (w[1], w[0]))
        n = min(free, key=lambda w: (w[1], w[0]))
    print("done", flush=True)


if __name__ == "__main__":
    main()
