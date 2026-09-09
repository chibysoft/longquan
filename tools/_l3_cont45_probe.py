"""From post-(45,40) pose under skip3852 / stop4250: continue scanning for d14 drop."""
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


def boot(zig):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_cont45"]},
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
    for tgt in zig:
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        data, _, st = move_wp(sess, data, min(flock, key=lambda w: w[0]), tgt, freeze14)
        print(f"zig {tgt} {st}", flush=True)
    # frog
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
    west15 = min(fr15, key=lambda w: w[0])
    stgt = (40, 46) if west15[1] >= 54 else (40, 44)
    data, _, st = move_wp(sess, data, s, stgt, fr15)
    print(f"S {stgt} {st}", flush=True)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, (45, 40), fr15)
    print(f"N45 {st}", flush=True)
    dump(data, "pose45")
    return sess, data


CURATED = (
    # SE toward goal from (45,40)/(40,36)
    (48, 42),
    (50, 42),
    (48, 44),
    (50, 44),
    (52, 44),
    (48, 46),
    (50, 46),
    (52, 46),
    (48, 48),
    (50, 48),
    (52, 48),
    (54, 48),
    (45, 44),
    (45, 46),
    (45, 48),
    (43, 44),
    (43, 46),
    (44, 48),
    (46, 48),
    (40, 48),
    (42, 48),
    (40, 50),
    (44, 50),
    (48, 50),
    (50, 50),
    (52, 50),
    (46, 42),
    (44, 42),
    (48, 40),
    (50, 40),
    (52, 40),
    (43, 38),
    (46, 38),
    (48, 38),
    (50, 38),
    (40, 42),
    (38, 42),
    (36, 44),
    (38, 44),
    (38, 48),
    (36, 48),
    (42, 50),
    (44, 52),
    (46, 52),
    (48, 52),
    (50, 52),
    (52, 52),
    (54, 50),
    (54, 52),
    (55, 48),
    (55, 50),
)


def scan_deep(sess, data, rounds=4):
    for rnd in range(rounds):
        if step_budget(data["frame"]) < 3:
            print("budout", flush=True)
            break
        d0, free, fr15 = dump(data, f"r{rnd}")
        # Prefer moving eastern wp first
        ordered = sorted(free, key=lambda w: (-w[0], -w[1]))
        hit = False
        noops = 0
        for cur in ordered:
            for ld in CURATED:
                if step_budget(data["frame"]) < 3:
                    break
                if ld == cur:
                    continue
                if near_any(ld, list(fr15), cheb=5):
                    continue
                others = [w for w in free if w != cur]
                if any(cheb(ld, o) < 5 for o in others):
                    continue
                if ld in {(46, 40), (42, 40), (42, 42), (42, 45), (42, 46), (43, 40), (43, 42)}:
                    continue
                if cur[1] == 44 and ld[1] == 44 and ld[0] > cur[0]:
                    continue
                data, newc, st = move_wp(sess, data, cur, ld, fr15)
                me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
                d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
                print(
                    f"  {cur}->{ld} {st}->{newc} ship={me['c']} d14={d14}({d14-d0:+d}) "
                    f"bud={step_budget(data['frame'])}",
                    flush=True,
                )
                if st == "dead":
                    print("DEAD", flush=True)
                    return data
                if st == "moved":
                    dump(data, f"HIT-r{rnd}")
                    if d14 < d0:
                        print("IMPROVED", flush=True)
                    hit = True
                    break
                noops += 1
                fr15 = lock_other_ship(data["frame"], 14)
                free = count_free14(data["frame"], fr15)
                if noops >= 6:
                    break
            if hit or noops >= 6:
                break
        if not hit:
            print(f"r{rnd} no hit (noops={noops})", flush=True)
            break
    dump(data, "end")
    return data


def main():
    print("\n===== cont skip3852 =====", flush=True)
    sess, data = boot([(42, 54)])
    scan_deep(sess, data, rounds=4)

    print("\n===== cont stop4250 =====", flush=True)
    sess, data = boot([])
    scan_deep(sess, data, rounds=4)


if __name__ == "__main__":
    main()
