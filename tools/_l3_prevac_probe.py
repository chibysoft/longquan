"""Vacate 15 south BEFORE frog-ny; then stack and scan 14 exits with more bud."""
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
    return fr15, free


def mid_and_deep15(sess, data, lv0, west_tgts):
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    east = max(fr15, key=lambda w: w[0])
    data, newc, st = move_wp(sess, data, east, (58, 42), freeze14)
    print(f"east15 {east}->(58,42) {st}->{newc}", flush=True)
    if st == "dead":
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    west = min(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
    data, newc, st = move_wp(sess, data, west, (48, 42), freeze14)
    print(f"west15 {west}->(48,42) {st}->{newc}", flush=True)
    if st != "moved" and st != "already":
        print("west15fail", flush=True)
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    east = max(flock, key=lambda w: w[0])
    for tgt in west_tgts:
        if cheb(tgt, east) < 5:
            continue
        if near_any(tgt, list(freeze14), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, west, tgt, freeze14)
        print(f"pre-frog vac {west}->{tgt} {st}->{newc} bud={step_budget(data['frame'])}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            return data, False
        if st == "moved":
            west = newc
            freeze14 = lock_other_ship(data["frame"], 15)
            flock = list(lock_other_ship(data["frame"], 14))
            east = max(flock, key=lambda w: w[0])
            # one successful deep vacate is enough for this variant
            break
    return data, True


def frog_to_n438(sess, data):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print(f"leadS {st}", flush=True)
    if st != "moved":
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
    if not near_any((40, 44), list(fr15), cheb=5):
        data, _, st = move_wp(sess, data, s, (40, 44), fr15)
        print(f"S40 {st}", flush=True)
        if st == "dead":
            return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    s = max(free, key=lambda w: (w[1], w[0]))
    for tgt in ((43, 38), (43, 36)):
        if near_any(tgt, list(fr15), cheb=5):
            continue
        if cheb(tgt, s) < 5:
            continue
        data, _, st = move_wp(sess, data, n, tgt, fr15)
        print(f"N {tgt} {st}", flush=True)
        if st == "dead":
            return data, False
        if st == "moved":
            return data, True
    return data, False


def scan14(sess, data):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) != 2:
        return data, False
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    ban = {(42, 40), (42, 42), (42, 45), (42, 46), (41, 44), (42, 44), (43, 44), (43, 40), (43, 42)}
    cands = [
        (n, (45, 40)),
        (n, (46, 38)),
        (n, (46, 40)),
        (n, (44, 38)),
        (n, (48, 40)),
        (n, (47, 40)),
        (n, (44, 40)),
        (n, (45, 42)),
        (n, (46, 42)),
        (s, (38, 44)),
        (s, (36, 44)),
        (s, (40, 48)),
        (s, (38, 48)),
        (s, (36, 48)),
        (s, (42, 48)),
        (s, (44, 48)),
        (s, (40, 46)),
        (n, (41, 38)),
        (n, (42, 38)),
        (n, (44, 36)),
    ]
    for cur, ld in cands:
        if step_budget(data["frame"]) < 4:
            print("bud low scan", flush=True)
            break
        if ld in ban or ld == cur:
            continue
        if not (0 <= ld[0] < 64 and 0 <= ld[1] < 64):
            continue
        other = s if cur == n else n
        if cheb(ld, other) < 5:
            continue
        if near_any(ld, list(fr15), cheb=5):
            print(f"skip near15 {ld}", flush=True)
            continue
        if ld[1] <= 36 and ld[0] >= 45:
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(
            f"14 {cur}->{ld} {st}->{newc} ship={me['c']} d14={d14} bud={step_budget(data['frame'])}",
            flush=True,
        )
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", flush=True)
            return data, False
        if st == "moved":
            dump(data, "HIT")
            return data, True
        # refresh free after noop burn
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) != 2:
            break
        s = max(free, key=lambda w: (w[1], w[0]))
        n = min(free, key=lambda w: (w[1], w[0]))
    return data, False


def main():
    variants = [
        ("v4848", [(48, 48)]),
        ("v4850", [(48, 50)]),
        ("v4650", [(46, 50), (48, 48)]),
        ("v4250", [(42, 50)]),
        ("v4052", [(40, 52)]),
        ("v4846", [(48, 46)]),
        ("v4548", [(45, 48)]),
    ]
    key = _api_key()
    for name, tgts in variants:
        print(f"\n===== {name} {tgts} =====", flush=True)
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
        data, ok = mid_and_deep15(sess, data, lv0, tgts)
        if not ok:
            print("deepfail", flush=True)
            continue
        dump(data, "pre-frog")
        data, ok = frog_to_n438(sess, data)
        if not ok:
            print("frogfail", flush=True)
            continue
        dump(data, "post-stack")
        data, hit = scan14(sess, data)
        if hit:
            print("SUCCESS", name, flush=True)
            return
        if data.get("state") == "GAME_OVER":
            print("GO", flush=True)
            continue
        dump(data, "end")
    print("all done", flush=True)


if __name__ == "__main__":
    main()
