"""SE2644 shortcut: Ny+S without frog — aim d14=34 with bud>10."""
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
        f"{label} ship14={me['c']} d14={d14} free={sorted(free)} n={len(free)} "
        f"d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, free, fr15, step_budget(data["frame"])


def boot_se2644():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_se_short"]},
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
    data, _, st = move_wp(sess, data, lag, (26, 44), fr15)
    print(f"  lag->2644 {st}", flush=True)
    if st != "moved":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    # extend the south pad east (live: pad at 26,44 -> 36,44)
    src = (26, 44) if (26, 44) in free else max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, src, (36, 44), fr15)
    print(f"  {src}->3644 {st}", flush=True)
    if st != "moved":
        return sess, data, False
    dump(data, "SE2644")
    return sess, data, True


def try_ny_s(nyt, s_tgts):
    print(f"\n===== Ny{nyt} + S =====", flush=True)
    sess, data, ok = boot_se2644()
    if not ok:
        print("boot fail", flush=True)
        return None
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    if near_any(nyt, list(fr15), cheb=5) or cheb(nyt, south) < 5:
        print("Ny skip", flush=True)
        return None
    data, _, st = move_wp(sess, data, north, nyt, fr15)
    print(f"  Ny {north}->{nyt} {st}", flush=True)
    if st != "moved":
        return None
    d14, free, fr15, bud = dump(data, "N")
    south = max(free, key=lambda w: (w[1], w[0]))
    others = [w for w in free if w != south]
    for stgt in s_tgts:
        if near_any(stgt, list(fr15), cheb=5):
            continue
        if any(cheb(stgt, o) < 5 for o in others):
            continue
        data, _, st = move_wp(sess, data, south, stgt, fr15)
        print(f"  S {south}->{stgt} {st}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            return None
        if st == "moved":
            break
    d14, free, fr15, bud = dump(data, "S")
    beat = len(free) >= 2 and (d14 < 34 or (d14 <= 34 and bud >= 10))
    strong = len(free) >= 2 and d14 <= 34 and bud >= 8
    print(
        f"=== {'BEAT' if beat else ('STRONG' if strong else 'best')} "
        f"Ny{nyt}: d14={d14} bud={bud} n={len(free)} free={sorted(free)} ===",
        flush=True,
    )
    return d14, bud, free


def main():
    s_tgts = ((48, 42), (44, 44), (40, 46), (48, 44), (42, 44))
    for nyt in ((46, 36), (45, 36), (44, 36), (42, 36), (40, 36), (40, 38), (42, 40)):
        try_ny_s(nyt, s_tgts)
    # Also try bigger S first without Ny
    print("\n===== S-only from SE2644 =====", flush=True)
    sess, data, ok = boot_se2644()
    if ok:
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
        for stgt in ((40, 44), (42, 44), (44, 44), (48, 42), (48, 44), (40, 48)):
            if cheb(stgt, north) < 5 or near_any(stgt, list(fr15), cheb=5):
                continue
            data, _, st = move_wp(sess, data, south, stgt, fr15)
            print(f"  S {south}->{stgt} {st}", flush=True)
            if st == "moved":
                dump(data, "Sonly")
                break
            if st == "dead":
                break


if __name__ == "__main__":
    main()
