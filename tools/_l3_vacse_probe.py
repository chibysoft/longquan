"""Post-E48: vacate west15 then retry SE; also try N-wp pulls."""
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
    return d14, free, fr15


def boot_e48():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_vacse"]},
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
    s = max(free, key=lambda w: (w[0], w[1]))
    data, _, _ = move_wp(sess, data, s, (48, 42), fr15)
    dump(data, "e48")
    return sess, data


def try_se(sess, data, ld):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        print("n<2", flush=True)
        return data, "skip"
    east = max(free, key=lambda w: (w[0], w[1]))
    if near_any(ld, list(fr15), cheb=5):
        print(f"  SE {ld} near15", flush=True)
        return data, "near"
    others = [w for w in free if w != east]
    if any(cheb(ld, o) < 5 for o in others):
        print(f"  SE {ld} merge", flush=True)
        return data, "merge"
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    d0 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    data, newc, st = move_wp(sess, data, east, ld, fr15)
    me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(
        f"  SE {east}->{ld} {st}->{newc} ship={me['c']} d14={d14}({d14-d0:+d}) "
        f"bud={step_budget(data['frame'])}",
        flush=True,
    )
    return data, st


def main():
    # A: vacate west15 then SE
    print("\n===== A vacate then SE =====", flush=True)
    sess, data = boot_e48()
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    for wt in ((38, 52), (34, 54), (42, 54), (38, 50)):
        if step_budget(data["frame"]) < 3:
            break
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        west = min(flock, key=lambda w: w[0])
        east = max(flock, key=lambda w: w[0])
        if max(abs(wt[0] - east[0]), abs(wt[1] - east[1])) < 5:
            continue
        data, newc, st = move_wp(sess, data, west, wt, freeze14)
        print(f"vac15 {west}->{wt} {st}->{newc} bud={step_budget(data['frame'])}", flush=True)
        if st == "dead":
            print("DEAD vac", flush=True)
            break
        if st == "moved":
            dump(data, "after-vac")
            break
    else:
        dump(data, "no-vac")

    if "frame" in data and data.get("state") != "GAME_OVER":
        for ld in ((52, 46), (52, 44), (50, 46), (54, 48), (52, 48), (48, 46), (50, 48)):
            if step_budget(data["frame"]) < 3:
                break
            data, st = try_se(sess, data, ld)
            if st == "dead":
                break
            if st == "moved":
                dump(data, "HIT")
                print("IMPROVED?" , flush=True)
                break

    # B: N-wp pull without vacate
    print("\n===== B N-pull =====", flush=True)
    sess, data = boot_e48()
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    for ld in ((44, 40), (46, 38), (43, 38), (48, 40), (45, 40), (44, 38), (40, 40), (46, 40)):
        if step_budget(data["frame"]) < 3:
            break
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        north = min(free, key=lambda w: (w[1], w[0]))
        if near_any(ld, list(fr15), cheb=5):
            print(f"N {ld} near15", flush=True)
            continue
        others = [w for w in free if w != north]
        if any(cheb(ld, o) < 5 for o in others):
            print(f"N {ld} merge", flush=True)
            continue
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        d0 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        data, newc, st = move_wp(sess, data, north, ld, fr15)
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(
            f"N {north}->{ld} {st}->{newc} ship={me['c']} d14={d14}({d14-d0:+d}) "
            f"bud={step_budget(data['frame'])}",
            flush=True,
        )
        if st == "dead":
            print("DEAD N", flush=True)
            break
        if st == "moved":
            dump(data, "N-HIT")
            if d14 < d0:
                print("IMPROVED", flush=True)
            # continue SE if bud
            if step_budget(data["frame"]) >= 3:
                for ld2 in ((52, 46), (52, 44), (50, 46), (54, 48)):
                    data, st2 = try_se(sess, data, ld2)
                    if st2 in ("dead", "moved"):
                        if st2 == "moved":
                            dump(data, "SE-after-N")
                        break
            break

    # C: vacate BEFORE E48 (after S), then big SE
    print("\n===== C vac-before-E48 =====", flush=True)
    # reuse boot but stop before E48 — redo manually
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_vacpre"]},
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
    dump(data, "postS")
    # vacate then SE leap
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, west, (38, 52), freeze14)
    print(f"vac {st} bud={step_budget(data['frame'])}", flush=True)
    if st == "moved":
        dump(data, "vac3852")
        for ld in ((48, 42), (52, 46), (52, 44), (50, 46), (54, 48), (48, 46)):
            data, st = try_se(sess, data, ld)
            if st == "dead":
                break
            if st == "moved":
                dump(data, "HIT")
                break


if __name__ == "__main__":
    main()
