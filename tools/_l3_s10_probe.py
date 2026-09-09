"""From S4842 pose (40,36)+(48,42) bud≈10: dense exit scan before Ne.
Also B-lite: one zig to (38,52) then frog (S4842 alive?)."""
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
    return d14, free, fr15


def boot_to_s4842(zig_one=False):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_s10"]},
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
    flock = list(lock_other_ship(data["frame"], 14))
    data, _, _ = move_wp(sess, data, min(flock, key=lambda w: w[0]), (42, 50), freeze14)
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    data, _, _ = move_wp(sess, data, max(flock, key=lambda w: w[0]), (58, 50), freeze14)
    if zig_one:
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        west = min(flock, key=lambda w: w[0])
        data, _, st = move_wp(sess, data, west, (38, 52), freeze14)
        print(f"zig3852 {st}", flush=True)
        if st == "dead":
            return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    if st != "moved":
        print(f"leadS {st}", flush=True)
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    if st != "moved":
        print(f"frog {st}", flush=True)
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (40, 36), fr15)
    if st != "moved":
        print(f"Ny {st}", flush=True)
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, s, (48, 42), fr15)
    print(f"S4842 {st}", flush=True)
    if st != "moved":
        return sess, data, False
    dump(data, "S4842")
    return sess, data, True


# Known bad
BAN = {
    (50, 36),
    (48, 36),
    (52, 44),
    (50, 46),
    (52, 46),
    (48, 48),
    (48, 46),
    (43, 38),
    (50, 48),
    (50, 42),
    (50, 44),
    (46, 40),
    (42, 40),
}


def one_shot(cur0, ld):
    print(f"\n--- {cur0}->{ld} ---", flush=True)
    sess, data, ok = boot_to_s4842()
    if not ok:
        print("boot fail", flush=True)
        return
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    d0 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    if cur0 not in free:
        # role remap
        if cur0[1] <= 36:
            cur = min(free, key=lambda w: (w[1], w[0]))
        else:
            cur = max(free, key=lambda w: (w[0], w[1]))
    else:
        cur = cur0
    if ld in BAN or near_any(ld, list(fr15), cheb=5):
        print("skip near/ban", flush=True)
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
        f"  {st}->{newc} ship={me['c']} d14={d14}({d14-d0:+d}) "
        f"free={sorted(free2)} n={len(free2)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    if st == "moved" and d14 < d0 and len(free2) == 2:
        print("IMPROVED", flush=True)
        dump(data, "HIT")
        # if bud left, one more hop
        if step_budget(data["frame"]) >= 3:
            fr15 = lock_other_ship(data["frame"], 14)
            free = count_free14(data["frame"], fr15)
            east = max(free, key=lambda w: (w[0], w[1]))
            for ld2 in ((52, 48), (54, 48), (50, 46), (52, 46), (48, 46), (54, 50), (52, 44)):
                if ld2 in BAN or near_any(ld2, list(fr15), cheb=5):
                    continue
                others = [w for w in free if w != east]
                if any(cheb(ld2, o) < 5 for o in others):
                    continue
                data, newc, st2 = move_wp(sess, data, east, ld2, fr15)
                me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
                d2 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
                print(
                    f"  hop2 {east}->{ld2} {st2} ship={me['c']} d14={d2} "
                    f"bud={step_budget(data['frame'])}",
                    flush=True,
                )
                if st2 == "dead":
                    break
                if st2 == "moved":
                    dump(data, "HOP2")
                    if d2 < d14:
                        print("IMPROVED2", flush=True)
                    break
        return True
    if st == "moved":
        print("FLAT/STEAL", flush=True)
    return False


def main():
    # Priority: beats Ne's d14=34 in one hop, or equals with more bud left
    cands = [
        # north east pulls (alternative to Ne 45,36)
        ((40, 36), (45, 36)),  # baseline Ne
        ((40, 36), (46, 38)),
        ((40, 36), (48, 38)),
        ((40, 36), (44, 40)),
        ((40, 36), (48, 40)),
        ((40, 36), (50, 40)),
        ((40, 36), (47, 40)),
        ((40, 36), (45, 40)),
        ((40, 36), (42, 38)),
        ((40, 36), (44, 38)),
        ((40, 36), (40, 40)),
        ((40, 36), (40, 42)),
        # south SE (avoid known dead)
        ((48, 42), (52, 48)),
        ((48, 42), (54, 48)),
        ((48, 42), (54, 46)),
        ((48, 42), (52, 42)),
        ((48, 42), (54, 44)),
        ((48, 42), (46, 44)),
        ((48, 42), (48, 44)),
        ((48, 42), (51, 45)),
        ((48, 42), (49, 45)),
    ]
    for cur, ld in cands:
        if one_shot(cur, ld):
            print("STOP on improve", flush=True)
            break

    # B-lite: zig 3852 then frog
    print("\n===== B-lite zig3852 =====", flush=True)
    sess, data, ok = boot_to_s4842(zig_one=True)
    if ok:
        dump(data, "B-lite")
        # try Ne
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) >= 2:
            north = min(free, key=lambda w: (w[1], w[0]))
            data, _, st = move_wp(sess, data, north, (45, 36), fr15)
            print(f"Ne {st}", flush=True)
            dump(data, "B-Ne")


if __name__ == "__main__":
    main()
