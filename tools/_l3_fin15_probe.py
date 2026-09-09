"""Finish chrome15 to (34,57) from mid-east; leave 14 parked; then frog 14."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import (
    clear15_corridor,
    count_free14,
    haul15_toward,
    lock_other_ship,
    near_any,
)
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
        f"{label} ship14={me['c']} d14={d14} free14={sorted(free)} "
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d15


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_fin15"]},
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

    # Stage to 3454 + keep east eastish then haul
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
    for tgt in ((38, 52), (42, 54), (38, 50), (34, 54)):
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        west = min(flock, key=lambda w: w[0])
        east = max(flock, key=lambda w: w[0])
        if cheb(tgt, east) < 5:
            continue
        data, newc, st = move_wp(sess, data, west, tgt, freeze14)
        print(f"zig {west}->{tgt} {st}->{newc} bud={step_budget(data['frame'])}", flush=True)
        if st == "dead":
            print("15DEAD", flush=True)
            return
    dump(data, "at3454")

    # Micro probes from 3454 toward goal (avoid known noops first try)
    for tgt in ((34, 55), (33, 56), (35, 56), (32, 55), (34, 57), (36, 57), (32, 57), (30, 56)):
        if step_budget(data["frame"]) < 4:
            break
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        west = min(flock, key=lambda w: w[0])
        east = max(flock, key=lambda w: w[0])
        if cheb(tgt, east) < 5 or near_any(tgt, list(freeze14), cheb=5):
            print(f"skip {tgt}", flush=True)
            continue
        if cheb(tgt, west) == 0:
            continue
        data, newc, st = move_wp(sess, data, west, tgt, freeze14)
        print(f"wfin {west}->{tgt} {st}->{newc}", flush=True)
        if st == "dead":
            print("15DEAD", flush=True)
            return
        if st == "moved":
            dump(data, "wfin-hit")
            break

    # Soft haul15
    while step_budget(data["frame"]) >= 6:
        me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
        d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
        if d15 <= 2:
            break
        data, moved = haul15_toward(sess, data, (34, 57), max_step=4, label="15fin")
        dump(data, f"haul moved={moved}")
        if data.get("state") == "GAME_OVER" or "frame" not in data:
            print("GO", flush=True)
            return
        if not moved:
            break

    # Try east closer without killing corridor
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    east = max(flock, key=lambda w: w[0])
    for tgt in ((52, 54), (50, 56), (46, 56), (40, 56), (36, 56), (34, 56)):
        if step_budget(data["frame"]) < 4:
            break
        if cheb(tgt, west) < 5 or near_any(tgt, list(freeze14), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, east, tgt, freeze14)
        print(f"efin {east}->{tgt} {st}->{newc}", flush=True)
        if st == "dead":
            print("15DEAD", flush=True)
            return
        if st == "moved":
            freeze14 = lock_other_ship(data["frame"], 15)
            flock = list(lock_other_ship(data["frame"], 14))
            west = min(flock, key=lambda w: w[0])
            east = max(flock, key=lambda w: w[0])
            dump(data, "efin-hit")

    d15 = dump(data, "final15")
    print(f"done d15={d15} bud={step_budget(data['frame'])}", flush=True)


if __name__ == "__main__":
    main()
