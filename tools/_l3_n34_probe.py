"""From (45,36)+(48,42) d14=34 bud≈4: find next improving move."""
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
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(
        f"{label} ship={me['c']} d14={d14} free={sorted(free)} "
        f"fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, free, fr15


def boot():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_n34"]},
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
    data, _, _ = move_wp(sess, data, s, (48, 42), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, n, (45, 36), fr15)
    dump(data, "pose34")
    return sess, data


CANDS = [
    ((45, 36), (50, 36)),
    ((45, 36), (48, 36)),
    ((45, 36), (47, 38)),
    ((45, 36), (48, 38)),
    ((45, 36), (50, 38)),
    ((45, 36), (45, 40)),
    ((45, 36), (48, 40)),
    ((48, 42), (52, 44)),
    ((48, 42), (50, 46)),
    ((48, 42), (48, 46)),
    ((48, 42), (52, 42)),
    ((48, 42), (50, 40)),
    ((48, 42), (54, 44)),
]


def main():
    for cur0, ld in CANDS:
        print(f"\n--- {cur0}->{ld} ---", flush=True)
        sess, data = boot()
        if step_budget(data["frame"]) < 3:
            print("budout at pose", flush=True)
            return
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        d0 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        if cur0 not in free:
            print("missing", flush=True)
            continue
        if near_any(ld, list(fr15), cheb=5):
            print("near15", flush=True)
            continue
        others = [w for w in free if w != cur0]
        if any(cheb(ld, o) < 5 for o in others):
            print("merge", flush=True)
            continue
        data, newc, st = move_wp(sess, data, cur0, ld, fr15)
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        free2 = count_free14(data["frame"], lock_other_ship(data["frame"], 14))
        print(
            f"  {st}->{newc} ship={me['c']} d14={d14}({d14-d0:+d}) "
            f"free={sorted(free2)} bud={step_budget(data['frame'])}",
            flush=True,
        )
        if st == "moved" and d14 < d0:
            print("IMPROVED", flush=True)
            dump(data, "HIT")
            return
        if st == "moved":
            print("FLAT", flush=True)


if __name__ == "__main__":
    main()
