"""Verify: after N4832+S(52,42), is the east pad still movable by 14? (lock misclass)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, lock_other_ship, manh, near_any
from tools.r11l_seated_clear import clear_l1, reset


def dump_raw(data, label):
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    wps = [w["c"] for w in r11l.waypoints(data["frame"])]
    d14 = abs(me14["c"][0] - 55) + abs(me14["c"][1] - 53)
    print(f"{label} ship14={me14['c']} d14={d14} ship15={me15['c']} all_wps={sorted(wps)} bud={step_budget(data['frame'])}", flush=True)
    for c in sorted(wps):
        d14m = manh(c, me14["c"])
        d15m = manh(c, me15["c"])
        print(f"  wp {c} d14={d14m} d15={d15m} closer={'15' if d15m+8<d14m and d15m<=16 else '14?'}", flush=True)
    return d14, wps


def boot():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_flipchk"]},
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
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, _ = move_wp(
        sess, data, max(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (58, 50), freeze14
    )
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lag = min(free, key=lambda w: w[0])
    data, _, _ = move_wp(sess, data, lag, (26, 44), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    src = (26, 44) if (26, 44) in free else max(free, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, src, (36, 44), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, north, (46, 36), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, south, (48, 42), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, north, (48, 32), fr15)
    dump_raw(data, "N4832")
    return sess, data


def main():
    for stgt in ((51, 42), (52, 42), (53, 42), (54, 42)):
        print(f"\n===== try S->{stgt} then micro =====", flush=True)
        sess, data = boot()
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        south = max(free, key=lambda w: (w[1], w[0]))
        data, newc, st = move_wp(sess, data, south, stgt, fr15)
        print(f"  S {south}->{stgt} {st}->{newc}", flush=True)
        if st != "moved":
            continue
        d1, wps = dump_raw(data, "afterS")
        # Try move the landed pad further with EMPTY freeze (prove still ours)
        if newc not in wps:
            print("pad vanished", flush=True)
            continue
        # freeze only true 15 pads at 4250/5850
        hard15 = [c for c in wps if c in ((42, 50), (58, 50)) or (c[0] >= 58 and c[1] >= 48)]
        # also freeze north pad
        north = min([c for c in wps if c != newc], key=lambda w: (w[1], w[0]), default=None)
        freeze = list(hard15)
        if north:
            freeze.append(north)
        for t2 in ((newc[0] + 2, newc[1]), (newc[0], newc[1] + 2), (newc[0] + 2, newc[1] + 2), (55, 48)):
            if not (0 <= t2[0] < 64 and 0 <= t2[1] < 64):
                continue
            if near_any(t2, hard15, cheb=5):
                continue
            if north and max(abs(t2[0] - north[0]), abs(t2[1] - north[1])) < 5:
                continue
            if step_budget(data["frame"]) < 3:
                break
            data, nc2, st2 = move_wp(sess, data, newc, t2, freeze)
            print(f"  cont {newc}->{t2} {st2}->{nc2} bud={step_budget(data['frame']) if 'frame' in data else '?'}", flush=True)
            if st2 == "moved":
                dump_raw(data, "afterCont")
                break
            if st2 == "dead":
                break


if __name__ == "__main__":
    main()
