"""From free=(40,36)+(48,42) under 4250+5850: find next d14-improving move."""
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


def boot_to_e48():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_next35"]},
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
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    data, _, _ = move_wp(sess, data, min(flock, key=lambda w: w[0]), (42, 50), freeze14)
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    data, _, _ = move_wp(sess, data, max(flock, key=lambda w: w[0]), (58, 50), freeze14)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, _ = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, n, (40, 36), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, s, (40, 44), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, s, (48, 42), fr15)
    print(f"E48 {st}", flush=True)
    dump(data, "pose35")
    return sess, data


# Known: (50,42) noop, (50,44) noop, (45,40) regresses
CANDS = [
    # move east wp further SE / S / E
    ((48, 42), (48, 46)),
    ((48, 42), (48, 48)),
    ((48, 42), (50, 46)),
    ((48, 42), (52, 46)),
    ((48, 42), (52, 44)),
    ((48, 42), (52, 48)),
    ((48, 42), (54, 48)),
    ((48, 42), (50, 48)),
    ((48, 42), (46, 46)),
    ((48, 42), (46, 44)),
    ((48, 42), (44, 46)),
    ((48, 42), (48, 44)),
    ((48, 42), (49, 45)),
    ((48, 42), (51, 45)),
    ((48, 42), (53, 47)),
    ((48, 42), (54, 46)),
    ((48, 42), (54, 50)),
    ((48, 42), (52, 50)),
    ((48, 42), (50, 50)),
    ((48, 42), (48, 50)),
    # move north wp east/south (pull ship)
    ((40, 36), (44, 36)),
    ((40, 36), (45, 38)),
    ((40, 36), (46, 38)),
    ((40, 36), (48, 36)),
    ((40, 36), (43, 38)),
    ((40, 36), (44, 40)),
    ((40, 36), (46, 40)),
    ((40, 36), (48, 40)),
    ((40, 36), (42, 38)),
    ((40, 36), (40, 40)),
    ((40, 36), (40, 42)),
    ((40, 36), (38, 40)),
    ((40, 36), (36, 40)),
    ((40, 36), (44, 42)),
    ((40, 36), (46, 44)),
    ((40, 36), (48, 46)),
    ((40, 36), (50, 40)),
    ((40, 36), (52, 40)),
]


def main():
    sess, data = boot_to_e48()
    d0, free, fr15 = dump(data, "scan")
    for cur_expect, ld in CANDS:
        if step_budget(data["frame"]) < 3:
            print("budout", flush=True)
            break
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if cur_expect not in free:
            # remap: use eastern/northern by role
            if cur_expect[1] >= 40:
                cur = max(free, key=lambda w: (w[0], w[1]))
            else:
                cur = min(free, key=lambda w: (w[1], w[0]))
        else:
            cur = cur_expect
        if ld == cur:
            continue
        if near_any(ld, list(fr15), cheb=5):
            print(f"  skip {ld} near15", flush=True)
            continue
        others = [w for w in free if w != cur]
        if any(cheb(ld, o) < 5 for o in others):
            print(f"  skip {ld} merge", flush=True)
            continue
        if ld in {(46, 40), (42, 40), (42, 42), (42, 45), (42, 46), (43, 40), (43, 42), (50, 42), (50, 44)}:
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
            print("DEAD — reboot needed; stopping", flush=True)
            return
        if st == "moved":
            dump(data, "HIT")
            if d14 < d0:
                print("IMPROVED", flush=True)
            # continue one more round from new pose
            d0 = d14
            continue
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
    dump(data, "end")


if __name__ == "__main__":
    main()
