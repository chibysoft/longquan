"""Stage 15: (58,42)+(48,42) then deeper; dense 14 scan after frog."""
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


def stage15(sess, data, west2=(42, 50), east2=None):
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    east = max(fr15, key=lambda w: w[0])
    west = min(fr15, key=lambda w: w[0])
    data, newc, st = move_wp(sess, data, east, (58, 42), freeze14)
    print(f"east1 {east}->(58,42) {st}->{newc}", flush=True)
    if st == "dead":
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    west = min(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
    data, newc, st = move_wp(sess, data, west, (48, 42), freeze14)
    print(f"west1 {west}->(48,42) {st}->{newc}", flush=True)
    if st not in ("moved", "already"):
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    east = max(flock, key=lambda w: w[0])
    if west2 and cheb(west2, east) >= 5 and not near_any(west2, list(freeze14), cheb=5):
        data, newc, st = move_wp(sess, data, west, west2, freeze14)
        print(f"west2 {west}->{west2} {st}->{newc}", flush=True)
        if st == "dead":
            return data, False
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        west = min(flock, key=lambda w: w[0])
        east = max(flock, key=lambda w: w[0])
    if east2 and cheb(east2, west) >= 5 and not near_any(east2, list(freeze14), cheb=5):
        data, newc, st = move_wp(sess, data, east, east2, freeze14)
        print(f"east2 {east}->{east2} {st}->{newc}", flush=True)
        if st == "dead":
            return data, False
    return data, True


def frog(sess, data, do_n438=True):
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
    if do_n438:
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        n = min(free, key=lambda w: (w[1], w[0]))
        s = max(free, key=lambda w: (w[1], w[0]))
        for tgt in ((43, 38), (43, 36)):
            if near_any(tgt, list(fr15), cheb=5) or cheb(tgt, s) < 5:
                continue
            data, _, st = move_wp(sess, data, n, tgt, fr15)
            if st == "dead":
                return data, False
            if st == "moved":
                break
    return data, True


def prioritized_cands(n, s):
    """Hand + ring; SE-first."""
    hand = [
        (n, (45, 40)),
        (n, (46, 40)),
        (n, (47, 40)),
        (n, (48, 40)),
        (n, (46, 38)),
        (n, (44, 38)),
        (n, (45, 42)),
        (n, (46, 42)),
        (n, (44, 40)),
        (n, (45, 39)),
        (n, (44, 39)),
        (n, (42, 38)),
        (n, (41, 38)),
        (n, (44, 36)),
        (s, (40, 48)),
        (s, (40, 46)),
        (s, (42, 48)),
        (s, (38, 48)),
        (s, (44, 48)),
        (s, (42, 46)),
        (s, (38, 46)),
        (s, (36, 48)),
        (s, (40, 50)),
        (s, (44, 46)),
        (s, (46, 48)),
        (n, (43, 39)),
        (n, (43, 41)),
        (n, (44, 41)),
        (n, (45, 41)),
    ]
    ban = {(42, 40), (42, 42), (42, 45), (42, 46), (41, 44), (42, 44), (43, 44), (43, 40), (43, 42)}
    out = []
    seen = set()
    for cur, ld in hand:
        if ld in ban or ld in seen or ld == cur:
            continue
        seen.add(ld)
        out.append((cur, ld))
    return out


def scan(sess, data, max_tries=16):
    d0 = dump(data, "scan-start")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) != 2:
        return data, None
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    tries = 0
    for cur, ld in prioritized_cands(n, s):
        if tries >= max_tries or step_budget(data["frame"]) < 4:
            break
        other = s if cur == n else n
        if cheb(ld, other) < 5:
            continue
        if near_any(ld, list(fr15), cheb=5):
            print(f"  skip near15 {ld}", flush=True)
            continue
        if ld[1] <= 36 and ld[0] >= 45:
            continue
        if not (0 <= ld[0] < 64 and 0 <= ld[1] < 64):
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        tries += 1
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
        if len(free) != 2:
            break
        s = max(free, key=lambda w: (w[1], w[0]))
        n = min(free, key=lambda w: (w[1], w[0]))
    return data, None


def run(name, west2, east2, do_n438):
    print(f"\n===== {name} w2={west2} e2={east2} n438={do_n438} =====", flush=True)
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
    data, ok = stage15(sess, data, west2=west2, east2=east2)
    if not ok:
        print("stagefail", flush=True)
        return None
    dump(data, "pre-frog")
    data, ok = frog(sess, data, do_n438=do_n438)
    if not ok:
        print("frogfail", flush=True)
        return None
    data, result = scan(sess, data)
    print(f"result={result}", flush=True)
    return result


def main():
    variants = [
        ("w4250", (42, 50), None, True),
        ("w4250_e5850", (42, 50), (58, 50), True),
        ("w4250_e5850_noN", (42, 50), (58, 50), False),
        ("w4650_e5850", (46, 50), (58, 50), True),
        ("w4848_e5850", (48, 48), (58, 50), True),
        ("w4250_e5648", (42, 50), (56, 48), True),
        ("w4050_e5850", (40, 50), (58, 50), True),
    ]
    best = None
    for name, w2, e2, n438 in variants:
        r = run(name, w2, e2, n438)
        if r == "improved":
            print("SUCCESS", name, flush=True)
            best = name
            break
        if r == "moved" and best is None:
            best = name
            print("KEEP", name, flush=True)
    print("all done best=", best, flush=True)


if __name__ == "__main__":
    main()
