"""Pre-zig to (42,54); frog leadS+frog+Ny36; S→(40,48) instead of S40."""
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
    return d14


def main():
    key = _api_key()
    for s_tgt in ((40, 48), (42, 48), (40, 46), (38, 48), (40, 44)):
        print(f"\n===== S->{s_tgt} =====", flush=True)
        sess = OnlineSession(key)
        r = sess.s.post(
            f"{BASE}/api/scorecard/open",
            headers=sess._headers(True),
            json={"tags": ["r11l_salt"]},
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
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        data, _, st = move_wp(sess, data, min(flock, key=lambda w: w[0]), (38, 52), freeze14)
        print(f"3852 {st}", flush=True)
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        data, _, st = move_wp(sess, data, min(flock, key=lambda w: w[0]), (42, 54), freeze14)
        print(f"4254 {st}", flush=True)
        dump(data, "pre")

        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        lead = max(free, key=lambda w: w[0])
        data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
        print(f"leadS {st}", flush=True)
        if st != "moved":
            continue
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        lead = max(free, key=lambda w: (w[1], w[0]))
        lag = min(free, key=lambda w: (w[1], w[0]))
        data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
        print(f"frog {st}", flush=True)
        if st != "moved":
            continue
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        n = min(free, key=lambda w: (w[1], w[0]))
        data, _, st = move_wp(sess, data, n, (40, 36), fr15)
        print(f"Ny36 {st}", flush=True)
        if st != "moved":
            continue
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        s = max(free, key=lambda w: (w[1], w[0]))
        n = min(free, key=lambda w: (w[1], w[0]))
        if near_any(s_tgt, list(fr15), cheb=5):
            print(f"S near15 {s_tgt}", flush=True)
            continue
        if cheb(s_tgt, n) < 5:
            print(f"S merge {s_tgt}", flush=True)
            continue
        d0 = dump(data, "pre-S")
        data, newc, st = move_wp(sess, data, s, s_tgt, fr15)
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(
            f"S {s}->{s_tgt} {st}->{newc} ship={me['c']} d14={d14}({d14-d0:+d}) "
            f"bud={step_budget(data['frame'])}",
            flush=True,
        )
        if st == "dead":
            print("DEAD", flush=True)
            continue
        if st == "moved":
            dump(data, "HIT")
            print("SUCCESS", s_tgt, flush=True)
            return
    print("all done", flush=True)


if __name__ == "__main__":
    main()
