"""Stage west15 to (34/36,54) — clear both N-east and S-south seals; skip N438."""
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


def stage(sess, data, west2, east2=(58, 50)):
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    print(f"e1 {st}", flush=True)
    if st == "dead":
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (48, 42), freeze14
    )
    print(f"w1 {st}", flush=True)
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    east = max(flock, key=lambda w: w[0])
    if cheb(west2, east) >= 5 and not near_any(west2, list(freeze14), cheb=5):
        data, newc, st = move_wp(sess, data, west, west2, freeze14)
        print(f"w2 {west}->{west2} {st}->{newc}", flush=True)
        if st == "dead":
            return data, False
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        west = min(flock, key=lambda w: w[0])
        east = max(flock, key=lambda w: w[0])
    else:
        print(f"w2 skip {west2}", flush=True)
    if east2 and cheb(east2, west) >= 5 and not near_any(east2, list(freeze14), cheb=5):
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


def scan(sess, data):
    d0 = dump(data, "scan")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) != 2:
        return None
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    for cur, ld in (
        (s, (40, 48)),
        (s, (40, 46)),
        (s, (42, 48)),
        (s, (38, 48)),
        (s, (44, 48)),
        (s, (42, 46)),
        (n, (45, 40)),
        (n, (46, 40)),
        (n, (43, 38)),
        (n, (44, 38)),
        (n, (46, 38)),
        (s, (40, 50)),
        (s, (36, 48)),
    ):
        if step_budget(data["frame"]) < 4:
            print("budout", flush=True)
            break
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
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", flush=True)
            return "dead"
        if st == "moved":
            dump(data, "HIT")
            return "improved" if d14 < d0 else "moved"
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) != 2:
            break
        s = max(free, key=lambda w: (w[1], w[0]))
        n = min(free, key=lambda w: (w[1], w[0]))
    return None


def run(name, west2):
    print(f"\n===== {name} w2={west2} =====", flush=True)
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
    lv0 = data.get("levels_completed") or 0
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
    data, ok = stage(sess, data, west2)
    if not ok:
        print("stagefail", flush=True)
        return None
    dump(data, "pre-frog")
    data, ok = frog_no_n(sess, data)
    if not ok:
        print("frogfail", flush=True)
        return None
    return scan(sess, data)


def main():
    for name, w2 in (
        ("w3654", (36, 54)),
        ("w3454", (34, 54)),
        ("w3854", (38, 54)),
        ("w3456", (34, 56)),
        ("w3254", (32, 54)),
        ("w3652", (36, 52)),
        ("w4054", (40, 54)),
    ):
        r = run(name, w2)
        print(f"result={r}", flush=True)
        if r in ("improved", "moved"):
            print("SUCCESS", name, flush=True)
            break
    print("all done", flush=True)


if __name__ == "__main__":
    main()
