"""Vacate east15 off (58,50) to unlock 14 SE south; measure d14/bud."""
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
    advance_14_frog_ny_stack,
    clear15_corridor,
    count_free14,
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
        f"{label} ship14={me['c']} d14={d14} free={sorted(free)} "
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, free, fr15


def boot_mid():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_vacE"]},
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
    return sess, data


def deep15(sess, data):
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
    dump(data, "deep15")
    return data


def vac_east(sess, data, tgts):
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    east = max(flock, key=lambda w: w[0])
    west = min(flock, key=lambda w: w[0])
    for tgt in tgts:
        if max(abs(tgt[0] - west[0]), abs(tgt[1] - west[1])) < 5:
            continue
        if near_any(tgt, list(lock_other_ship(data["frame"], 15)), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, east, tgt, freeze14)
        print(f"  vacE {east}->{tgt} {st}->{newc} bud={step_budget(data['frame'])}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            return data, False
        if st == "moved":
            dump(data, "after-vacE")
            return data, True
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        east = max(flock, key=lambda w: w[0])
        west = min(flock, key=lambda w: w[0])
    return data, False


def try_s_south(sess, data, tgts):
    """After vac, try 14 S south from current free."""
    hits = []
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return data, hits
    d0, free, fr15 = dump(data, "preS")
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    for tgt in tgts:
        if step_budget(data["frame"]) < 3:
            break
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) < 2:
            break
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
        if cheb(tgt, north) < 5 or near_any(tgt, list(fr15), cheb=5):
            print(f"  skip S->{tgt}", flush=True)
            continue
        data, newc, st = move_wp(sess, data, south, tgt, fr15)
        bud = step_budget(data["frame"]) if "frame" in data else -1
        print(f"  S {south}->{tgt} {st}->{newc} bud={bud}", flush=True)
        if st == "dead":
            break
        if st != "moved":
            continue
        d1, free1, _ = dump(data, "afterS")
        if len(free1) == 2 and d1 < d0:
            print(f"IMPROVED {d0}->{d1}", flush=True)
            hits.append((tgt, d0, d1, bud, sorted(free1)))
            d0 = d1
            break
        if len(free1) != 2:
            print("FLOCK", flush=True)
            break
    return data, hits


def main():
    east_tgts = ((58, 54), (62, 52), (58, 56), (62, 50), (56, 54), (60, 54), (54, 52))
    s_tgts = ((62, 48), (60, 48), (58, 48), (62, 46), (56, 48), (64, 46), (54, 48))

    # A: vacE after deep15, then full seny (may re-deep — check)
    print("\n===== A vacE@deep then seny =====", flush=True)
    sess, data = boot_mid()
    data = deep15(sess, data)
    data, ok = vac_east(sess, data, east_tgts)
    print(f"  vac ok={ok}", flush=True)
    data, ok = advance_14_frog_ny_stack(sess, data, (34, 57))
    print(f"  seny ok={ok}", flush=True)
    dump(data, "FINAL-A")

    # B: full seny first, then vacE, then S south
    print("\n===== B seny then vacE then S =====", flush=True)
    sess, data = boot_mid()
    data, ok = advance_14_frog_ny_stack(sess, data, (34, 57))
    print(f"  seny ok={ok}", flush=True)
    dump(data, "post-seny")
    if ok and step_budget(data["frame"]) >= 4:
        data, vok = vac_east(sess, data, east_tgts)
        print(f"  vac ok={vok}", flush=True)
        if vok:
            data, hits = try_s_south(sess, data, s_tgts)
            print(f"  hits={hits}", flush=True)
    dump(data, "FINAL-B")

    # C: after S6044-equivalent (seny without burning N6038) — modify by stopping early
    # Use seny then if at N6038, still vacE
    print("\n===== C vacE@deep keep east south, manual SE =====", flush=True)
    sess, data = boot_mid()
    data = deep15(sess, data)
    data, ok = vac_east(sess, data, ((58, 54), (62, 52), (60, 54)))
    if not ok:
        print("vac fail", flush=True)
        return
    # manual lagSE path without re-deeping 5850
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) != 2:
        print(f"bad free {free}", flush=True)
        return
    lag = min(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lag, (26, 44), fr15)
    print(f"  lagSE {st}", flush=True)
    if st != "moved":
        return
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    src = (26, 44) if (26, 44) in free else max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, src, (36, 44), fr15)
    print(f"  extE {st}", flush=True)
    if st != "moved":
        return
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (46, 36), fr15)
    print(f"  Ny {st}", flush=True)
    if st != "moved":
        return
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (48, 32), fr15)
    print(f"  N4832 {st}", flush=True)
    if st != "moved":
        return
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    # Prefer deep S now that east15 vacated
    for stgt in ((60, 48), (62, 46), (60, 44), (58, 48), (56, 48)):
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
        if near_any(stgt, list(fr15), cheb=5) or cheb(stgt, north) < 5:
            print(f"  skip {stgt}", flush=True)
            continue
        data, newc, st = move_wp(sess, data, south, stgt, fr15)
        print(f"  S {south}->{stgt} {st}->{newc}", flush=True)
        if st == "moved":
            break
        if st == "dead":
            break
    dump(data, "FINAL-C")
    # try N6038-like
    if step_budget(data["frame"]) >= 4:
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) >= 2:
            north = min(free, key=lambda w: (w[1], w[0]))
            south = max(free, key=lambda w: (w[1], w[0]))
            for nt in ((60, 38), (56, 38), (52, 38)):
                if near_any(nt, list(fr15), cheb=5) or cheb(nt, south) < 5:
                    continue
                data, newc, st = move_wp(sess, data, north, nt, fr15)
                print(f"  N {north}->{nt} {st}->{newc}", flush=True)
                if st == "moved":
                    dump(data, "FINAL-C2")
                    break


if __name__ == "__main__":
    main()
