"""After N4832: try S landings nearer goal (55,53) with east15 at (58,54).

Hypothesis: S6044 overshoots east; (58,50) seals y48 band; (58,54) may unlock
S→(52/54/56,48/50) for lower d14 and leftover bud.
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
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, lock_other_ship, near_any
from tools.r11l_seated_clear import clear_l1, reset
from longquan.interactive import r11l


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    allw = sorted(w["c"] for w in r11l.waypoints(data["frame"]))
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me['c']} d14={d14} free={sorted(free)} n={len(free)} "
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} all={allw} "
        f"bud={step_budget(data['frame'])} lv={data.get('levels_completed')}",
        flush=True,
    )
    return d14, free, fr15


def boot_to_n4832(east_b=(58, 54)):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_sgoal"]},
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

    # deep15 with east15b = (58,54) (or fallback)
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    print(f"  east15a {st}", flush=True)
    if st == "dead":
        return sess, data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    print(f"  west15 {st}", flush=True)
    if st == "dead":
        return sess, data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    east = max(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
    for et in (east_b, (58, 54), (62, 52), (58, 50)):
        if cheb(et, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0])) < 5:
            continue
        data, newc, st = move_wp(sess, data, east, et, freeze14)
        print(f"  east15b {east}->{et} {st}->{newc}", flush=True)
        if st == "moved":
            break
        if st == "dead":
            return sess, data, False
        freeze14 = lock_other_ship(data["frame"], 15)
        east = max(lock_other_ship(data["frame"], 14), key=lambda w: w[0])

    # se-ny through N4832
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lag = min(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lag, (26, 44), fr15)
    print(f"  lagSE {st}", flush=True)
    if st != "moved":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    src = (26, 44) if (26, 44) in free else max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, src, (36, 44), fr15)
    print(f"  extE {st}", flush=True)
    if st != "moved":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (46, 36), fr15)
    print(f"  Ny46 {st}", flush=True)
    if st != "moved":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (48, 32), fr15)
    print(f"  N4832 {st}", flush=True)
    if st != "moved":
        return sess, data, False
    dump(data, "N4832")
    return sess, data, True


# Prefer goal-side S; include baseline S6044 last for comparison
S_CANDS = [
    (52, 50),
    (54, 50),
    (52, 48),
    (54, 48),
    (56, 48),
    (56, 50),
    (50, 50),
    (50, 48),
    (58, 48),
    (60, 48),
    (54, 46),
    (52, 46),
    (56, 46),
    (60, 44),  # baseline
    (62, 46),
    (58, 46),
]

N_FOLLOW = [
    (56, 38),
    (52, 38),
    (60, 38),
    (54, 40),
    (50, 40),
    (56, 42),
    (52, 42),
    (48, 38),
]


def main():
    hits = []
    sess, data, ok = boot_to_n4832()
    if not ok:
        print("boot fail", flush=True)
        return
    d0, free, fr15 = dump(data, "base")
    if len(free) < 2:
        print("bad free", flush=True)
        return
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    print(f"N={north} S={south}", flush=True)

    for stgt in S_CANDS:
        if step_budget(data["frame"]) < 4:
            print("budout — reboot", flush=True)
            sess, data, ok = boot_to_n4832()
            if not ok:
                break
            d0, free, fr15 = dump(data, "rebase")
            if len(free) < 2:
                break
            north = min(free, key=lambda w: (w[1], w[0]))
            south = max(free, key=lambda w: (w[1], w[0]))

        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) < 2:
            sess, data, ok = boot_to_n4832()
            if not ok:
                break
            d0, free, fr15 = dump(data, "refree")
            continue
        north = min(free, key=lambda w: (w[1], w[0]))
        south = max(free, key=lambda w: (w[1], w[0]))
        if cheb(stgt, north) < 5 or near_any(stgt, list(fr15), cheb=5):
            print(f"  S->{stgt} skip merge/near15", flush=True)
            continue
        if cheb(stgt, south) <= 1:
            continue
        data, newc, st = move_wp(sess, data, south, stgt, fr15)
        bud = step_budget(data["frame"]) if "frame" in data else -1
        print(f"  S {south}->{stgt} {st}->{newc} bud={bud}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", flush=True)
            sess, data, ok = boot_to_n4832()
            if not ok:
                break
            d0, free, fr15 = dump(data, "redead")
            continue
        if st != "moved":
            continue
        d1, free1, fr1 = dump(data, "afterS")
        tag = "IMPROVED" if d1 < d0 else ("FLAT" if d1 == d0 else "WORSE")
        print(f"  {tag} {d0}->{d1}", flush=True)
        if d1 < d0:
            hits.append(("S", stgt, d0, d1, bud, sorted(free1)))
            # try one N follow if bud allows
            if bud >= 4 and len(free1) >= 2:
                n0 = min(free1, key=lambda w: (w[1], w[0]))
                s0 = max(free1, key=lambda w: (w[1], w[0]))
                for nt in N_FOLLOW:
                    if cheb(nt, s0) < 5 or near_any(nt, list(fr1), cheb=5):
                        continue
                    if cheb(nt, n0) <= 1:
                        continue
                    data, newc, st = move_wp(sess, data, n0, nt, fr1)
                    bud2 = step_budget(data["frame"]) if "frame" in data else -1
                    print(f"    N {n0}->{nt} {st}->{newc} bud={bud2}", flush=True)
                    if st == "moved":
                        d2, free2, _ = dump(data, "afterN")
                        if d2 < d1:
                            print(f"    N-IMPROVED {d1}->{d2}", flush=True)
                            hits.append(("N", nt, d1, d2, bud2, sorted(free2)))
                        break
                    if st == "dead" or data.get("state") == "GAME_OVER":
                        break
                    fr1 = lock_other_ship(data["frame"], 14)
                    free1 = count_free14(data["frame"], fr1)
                    if len(free1) < 2:
                        break
                    n0 = min(free1, key=lambda w: (w[1], w[0]))
                    s0 = max(free1, key=lambda w: (w[1], w[0]))
            # reboot for next S cand (pose changed)
            sess, data, ok = boot_to_n4832()
            if not ok:
                break
            d0, free, fr15 = dump(data, "rehit")
            continue
        # non-improve: reboot to keep scan clean
        sess, data, ok = boot_to_n4832()
        if not ok:
            break
        d0, free, fr15 = dump(data, "reflat")

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    if not hits:
        print("none", flush=True)


if __name__ == "__main__":
    main()
