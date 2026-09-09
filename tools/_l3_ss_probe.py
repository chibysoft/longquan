"""From Ny36+S40 (no N438) with deep15: S-south first; also extra translate14."""
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
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14


def boot_deep(sess):
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    lv0 = data.get("levels_completed") or 0
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    east = max(fr15, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, east, (58, 42), freeze14)
    print(f"e1 {st}", flush=True)
    freeze14 = lock_other_ship(data["frame"], 15)
    west = min(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
    data, _, st = move_wp(sess, data, west, (48, 42), freeze14)
    print(f"w1 {st}", flush=True)
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    east = max(flock, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, west, (42, 50), freeze14)
    print(f"w2 {st}", flush=True)
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    east = max(flock, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, east, (58, 50), freeze14)
    print(f"e2 {st}", flush=True)
    return data


def frog_ny_s40(sess, data):
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


def try_moves(sess, data, pairs, label):
    d0 = dump(data, label)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    for cur, ld in pairs:
        if step_budget(data["frame"]) < 4:
            print("budout", flush=True)
            break
        if cur not in free:
            # refresh roles
            free = count_free14(data["frame"], fr15)
            if len(free) != 2:
                break
        if near_any(ld, list(fr15), cheb=5):
            print(f"  skip near15 {ld}", flush=True)
            continue
        other = [w for w in free if w != cur]
        if other and cheb(ld, other[0]) < 5:
            print(f"  skip merge {ld}", flush=True)
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(
            f"  {cur}->{ld} {st}->{newc} ship={me['c']} d14={d14}({d14-d0:+d}) "
            f"bud={step_budget(data['frame'])}",
            flush=True,
        )
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", flush=True)
            return data, "dead"
        if st == "moved":
            dump(data, "HIT")
            return data, ("improved" if d14 < d0 else "moved")
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
    return data, None


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_ss"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"

    data = boot_deep(sess)
    dump(data, "deep")

    # Phase A: extra translate on y36 before frog
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])
    data, res = try_moves(
        sess,
        data,
        [
            (lead, (lead[0] + 4, 36)),
            (lead, (38, 36)),
            (lead, (40, 36)),
            (lag, (lag[0] + 4, 36)),
            (lag, (30, 36)),
        ],
        "xlate",
    )
    if res == "dead":
        return
    if res:
        print("xlate hit", res, flush=True)

    data, ok = frog_ny_s40(sess, data)
    if not ok:
        print("frogfail", flush=True)
        return
    dump(data, "at4044")

    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    # S-south / SE first — avoid N-east known noop/dead
    pairs = [
        (s, (40, 48)),
        (s, (40, 46)),
        (s, (42, 48)),
        (s, (38, 48)),
        (s, (44, 48)),
        (s, (42, 46)),
        (s, (40, 50)),
        (s, (36, 48)),
        (s, (44, 46)),
        (s, (38, 46)),
        (s, (42, 50)),
        (n, (43, 38)),
        (n, (42, 36)),
        (n, (44, 36)),
        (n, (38, 36)),
        (n, (36, 36)),
        (n, (43, 36)),
        (n, (41, 36)),
        (n, (44, 38)),
        (n, (42, 38)),
    ]
    data, res = try_moves(sess, data, pairs, "sscan")
    print("final", res, flush=True)


if __name__ == "__main__":
    main()
