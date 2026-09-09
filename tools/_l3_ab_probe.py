"""Option A/B probes for r11l L3 post-Ne bud and 15-first order.

A: skip more before Ne (5850? Ny36? merge S+Ne) — need bud≥8 at d14≤34
B: after 4250+5850, haul/zig 15 toward goal, then frog — keep east x≥56
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, haul15_toward, lock_other_ship, near_any
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
    return d14, free, fr15


def boot():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_ab"]},
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


def stage_c(sess, data, do_5850=True):
    """C path: 5842 → direct 4250 → optional 5850."""
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    print(f"5842 {st} bud={step_budget(data['frame'])}", flush=True)
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, min(flock, key=lambda w: w[0]), (42, 50), freeze14)
    print(f"4250 {st} bud={step_budget(data['frame'])}", flush=True)
    if do_5850:
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        data, _, st = move_wp(sess, data, max(flock, key=lambda w: w[0]), (58, 50), freeze14)
        print(f"5850 {st} bud={step_budget(data['frame'])}", flush=True)
    return data


def frog_to(sess, data, *, do_ny=True, s_tgts=((48, 42), (40, 44)), do_ne=True):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) != 2:
        print(f"bad n={len(free)} free={sorted(free)}", flush=True)
        return data, False
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print(f"leadS {st}", flush=True)
    if st == "dead":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    print(f"frog {st}", flush=True)
    if st != "moved":
        return data, False
    if do_ny:
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
    moved_s = False
    for tgt in s_tgts:
        if near_any(tgt, list(fr15), cheb=5):
            print(f"S {tgt} near15", flush=True)
            continue
        others = [w for w in free if w != s]
        if any(cheb(tgt, o) < 5 for o in others):
            print(f"S {tgt} merge", flush=True)
            continue
        data, _, st = move_wp(sess, data, s, tgt, fr15)
        print(f"S {tgt} {st}", flush=True)
        if st == "dead":
            return data, False
        if st == "moved":
            moved_s = True
            break
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        s = max(free, key=lambda w: (w[1], w[0]))
    if not moved_s:
        dump(data, "S-fail")
        return data, False
    if do_ne:
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) < 2:
            dump(data, "n1-preNe")
            return data, False
        south = max(free, key=lambda w: (w[0], w[1]))
        north = min(free, key=lambda w: (w[1], w[0]))
        if south[0] >= 46:
            data, _, st = move_wp(sess, data, north, (45, 36), fr15)
            print(f"Ne {st}", flush=True)
            if st == "dead":
                return data, False
    dump(data, "pose")
    return data, True


def scan_safe(sess, data, max_tries=4):
    """One-noop-and-stop scan; ban known dead."""
    ban = {(50, 36), (48, 36), (52, 44), (50, 46), (52, 46), (48, 48), (48, 46), (43, 38)}
    cands = [
        ((45, 36), (47, 40)),
        ((45, 36), (48, 40)),
        ((45, 36), (50, 40)),
        ((45, 36), (46, 40)),
        ((45, 36), (44, 40)),
        ((45, 36), (50, 38)),
        ((48, 42), (50, 48)),
        ((48, 42), (54, 48)),
        ((48, 42), (52, 42)),
        ((48, 42), (54, 44)),
        ((48, 42), (46, 44)),
        ((45, 36), (42, 40)),
        ((45, 36), (40, 40)),
    ]
    d0, free, fr15 = dump(data, "scan")
    tries = 0
    for cur0, ld in cands:
        if step_budget(data["frame"]) < 3 or tries >= max_tries:
            break
        if ld in ban or cur0 not in free:
            continue
        if near_any(ld, list(fr15), cheb=5):
            continue
        others = [w for w in free if w != cur0]
        if any(cheb(ld, o) < 5 for o in others):
            continue
        data, newc, st = move_wp(sess, data, cur0, ld, fr15)
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(
            f"  {cur0}->{ld} {st}->{newc} ship={me['c']} d14={d14}({d14-d0:+d}) "
            f"bud={step_budget(data['frame'])}",
            flush=True,
        )
        tries += 1
        if st == "dead":
            print("DEAD", flush=True)
            return data, False
        if st == "moved":
            dump(data, "HIT")
            if d14 < d0:
                print("IMPROVED", flush=True)
            return data, True
        ban.add(ld)
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        break  # one noop only
    return data, False


def zig15(sess, data, steps):
    """Move west15 along steps; keep east fixed if possible."""
    for tgt in steps:
        if step_budget(data["frame"]) < 4:
            break
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        west = min(flock, key=lambda w: w[0])
        east = max(flock, key=lambda w: w[0])
        if east[0] < 56:
            print(f"zig abort east={east}", flush=True)
            break
        if cheb(tgt, east) < 5 or near_any(tgt, list(freeze14), cheb=5):
            print(f"zig skip {tgt}", flush=True)
            continue
        data, newc, st = move_wp(sess, data, west, tgt, freeze14)
        print(f"zig15 {west}->{tgt} {st}->{newc} bud={step_budget(data['frame'])}", flush=True)
        if st == "dead":
            return data, False
        if st == "moved":
            dump(data, f"after-{tgt}")
    return data, True


def main():
    # ----- A1: skip 5850 (risk ownership) -----
    print("\n===== A1 skip5850 =====", flush=True)
    sess, data = boot()
    data = stage_c(sess, data, do_5850=False)
    data, ok = frog_to(sess, data)
    if ok:
        scan_safe(sess, data)

    # ----- A2: skip Ny36, S from frog pose -----
    print("\n===== A2 skip Ny36 =====", flush=True)
    sess, data = boot()
    data = stage_c(sess, data, do_5850=True)
    data, ok = frog_to(sess, data, do_ny=False, s_tgts=((48, 42), (40, 44), (45, 36)))
    if ok:
        scan_safe(sess, data)

    # ----- A3: skip Ne (stop at S4842 with more bud) -----
    print("\n===== A3 skip Ne (S4842 only) =====", flush=True)
    sess, data = boot()
    data = stage_c(sess, data, do_5850=True)
    data, ok = frog_to(sess, data, do_ne=False)
    if ok:
        # try Ne-alternative leaps with saved bud
        scan_safe(sess, data)
        if step_budget(data["frame"]) >= 3:
            fr15 = lock_other_ship(data["frame"], 14)
            free = count_free14(data["frame"], fr15)
            n = min(free, key=lambda w: (w[1], w[0]))
            for tgt in ((45, 36), (48, 36), (50, 38), (46, 40)):
                if near_any(tgt, list(fr15), cheb=5):
                    continue
                others = [w for w in free if w != n]
                if any(cheb(tgt, o) < 5 for o in others):
                    continue
                data, _, st = move_wp(sess, data, n, tgt, fr15)
                print(f"altN {tgt} {st}", flush=True)
                if st == "moved":
                    dump(data, "altN-HIT")
                    scan_safe(sess, data)
                    break
                if st == "dead":
                    break

    # ----- A4: n3 → (50,42) or (52,44) bigger S (one hop) -----
    print("\n===== A4 bigger S from n3 =====", flush=True)
    sess, data = boot()
    data = stage_c(sess, data, do_5850=True)
    # manual frog to n3 only
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
    dump(data, "n3")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    for tgt in ((50, 42), (52, 44), (50, 44), (54, 46), (48, 44), (46, 46)):
        if near_any(tgt, list(fr15), cheb=5):
            continue
        others = [w for w in free if w != s]
        if any(cheb(tgt, o) < 5 for o in others):
            continue
        data, newc, st = move_wp(sess, data, s, tgt, fr15)
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(f"bigS {tgt} {st}->{newc} ship={me['c']} d14={d14} bud={step_budget(data['frame'])}", flush=True)
        if st == "dead":
            break
        if st == "moved":
            dump(data, "bigS-HIT")
            if d14 <= 34 and step_budget(data["frame"]) >= 3:
                # try Ne-like
                fr15 = lock_other_ship(data["frame"], 14)
                free = count_free14(data["frame"], fr15)
                if len(free) >= 2:
                    north = min(free, key=lambda w: (w[1], w[0]))
                    data, _, st2 = move_wp(sess, data, north, (45, 36), fr15)
                    print(f"Ne-after {st2}", flush=True)
                    dump(data, "after")
                    scan_safe(sess, data)
            break

    # ----- B1: stage C then zig15 (keep east 5850) then frog -----
    print("\n===== B1 zig15 then frog =====", flush=True)
    sess, data = boot()
    data = stage_c(sess, data, do_5850=True)
    dump(data, "pre-zig")
    data, ok = zig15(sess, data, ((38, 52), (34, 54), (38, 56), (34, 56)))
    if ok and "frame" in data and data.get("state") != "GAME_OVER":
        # ensure east still ≥56
        fr15 = lock_other_ship(data["frame"], 14)
        east = max(fr15, key=lambda w: w[0]) if fr15 else (0, 0)
        print(f"east-now={east}", flush=True)
        if east[0] >= 56:
            data, ok2 = frog_to(sess, data)
            if ok2:
                scan_safe(sess, data)

    # ----- B2: stage C, limited haul15, frog -----
    print("\n===== B2 haul15x1 then frog =====", flush=True)
    sess, data = boot()
    data = stage_c(sess, data, do_5850=True)
    bud0 = step_budget(data["frame"])
    data, _ = haul15_toward(sess, data, (34, 57), max_step=4, label="15pre")
    dump(data, f"haul Δ{bud0 - step_budget(data['frame'])}")
    fr15 = lock_other_ship(data["frame"], 14)
    east = max(fr15, key=lambda w: w[0]) if fr15 else (0, 0)
    if east[0] < 56:
        freeze14 = lock_other_ship(data["frame"], 15)
        data, _, st = move_wp(sess, data, east, (58, 50), freeze14)
        print(f"re-anchor east {st}", flush=True)
    data, ok = frog_to(sess, data)
    if ok:
        scan_safe(sess, data)


if __name__ == "__main__":
    main()
