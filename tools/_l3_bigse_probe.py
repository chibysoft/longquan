"""Try larger SE leaps from S(40,44) and N pulls under 4250+5850."""
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


def boot_post_s():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_bigse"]},
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
    return sess, data


def try_ld(label, ld, from_south=True):
    print(f"\n=== {label} {ld} ===", flush=True)
    sess, data = boot_post_s()
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    d0 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    cur = max(free, key=lambda w: (w[1], w[0])) if from_south else min(free, key=lambda w: (w[1], w[0]))
    if near_any(ld, list(fr15), cheb=5):
        print("near15", flush=True)
        return
    others = [w for w in free if w != cur]
    if any(cheb(ld, o) < 5 for o in others):
        print("merge", flush=True)
        return
    data, newc, st = move_wp(sess, data, cur, ld, fr15)
    me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    free2 = count_free14(data["frame"], lock_other_ship(data["frame"], 14))
    print(
        f"  {cur}->{ld} {st}->{newc} ship={me['c']} d14={d14}({d14-d0:+d}) "
        f"free={sorted(free2)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    if st == "moved" and d14 <= 34:
        print("GOOD", flush=True)
        # try one more from here if bud
        if step_budget(data["frame"]) >= 3:
            fr15 = lock_other_ship(data["frame"], 14)
            free = count_free14(data["frame"], fr15)
            east = max(free, key=lambda w: (w[0], w[1]))
            for ld2 in ((52, 46), (54, 48), (52, 48), (50, 46), (48, 46), (54, 50)):
                if near_any(ld2, list(fr15), cheb=5):
                    continue
                others = [w for w in free if w != east]
                if any(cheb(ld2, o) < 5 for o in others):
                    continue
                if ld2 == east:
                    continue
                data, newc, st2 = move_wp(sess, data, east, ld2, fr15)
                me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
                d2 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
                print(
                    f"  cont {east}->{ld2} {st2}->{newc} ship={me['c']} d14={d2} "
                    f"bud={step_budget(data['frame'])}",
                    flush=True,
                )
                if st2 == "dead":
                    break
                if st2 == "moved":
                    print("CONT_HIT", flush=True)
                    break
                fr15 = lock_other_ship(data["frame"], 14)
                free = count_free14(data["frame"], fr15)
                east = max(free, key=lambda w: (w[0], w[1]))


def main():
    for ld in (
        (48, 42),
        (50, 46),
        (52, 46),
        (52, 44),
        (54, 48),
        (52, 48),
        (48, 46),
        (46, 46),
        (44, 48),
        (50, 48),
    ):
        try_ld(f"S", ld, from_south=True)
    for ld in ((44, 40), (46, 38), (43, 38), (48, 40), (45, 40)):
        try_ld(f"N", ld, from_south=False)


if __name__ == "__main__":
    main()
