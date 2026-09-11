"""After S6044 (d14=30 bud≈9): vacE then S-south / N — keep n=2."""
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


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    wps = [w["c"] for w in r11l.waypoints(data["frame"])]
    print(
        f"{label} ship14={me['c']} d14={d14} free={sorted(free)} n={len(free)} "
        f"ship15={me15['c']} fr15={sorted(fr15)} all={sorted(wps)} "
        f"bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, free, fr15


def boot_to_s6044():
    """Mid-east + deep15 + lagSE + Ny + N4832 + S6044 (no N6038)."""
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_vacE2"]},
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
    if st != "moved":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    src = (26, 44) if (26, 44) in free else max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, src, (36, 44), fr15)
    if st != "moved":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (46, 36), fr15)
    if st != "moved":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (48, 32), fr15)
    if st != "moved":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, (60, 44), fr15)
    if st != "moved":
        return sess, data, False
    dump(data, "S6044")
    return sess, data, True


def main():
    plans = [
        ("vacE-S6248-N6038", [(58, 54)], [("S", (62, 48)), ("S", (60, 48)), ("S", (62, 46))], [("N", (60, 38))]),
        ("vacE-S6048-N6038", [(58, 54)], [("S", (60, 48)), ("S", (62, 48))], [("N", (60, 38))]),
        ("vacE-S5648", [(58, 54)], [("S", (56, 48)), ("S", (58, 48)), ("S", (54, 48))], [("N", (56, 38))]),
        ("vacE62-S6248", [(62, 52), (58, 54)], [("S", (62, 48)), ("S", (60, 48))], [("N", (60, 38))]),
        ("N6038-then-vacE-S", None, None, None),  # special
    ]
    for name, etgts, stgts, ntgts in plans:
        print(f"\n===== {name} =====", flush=True)
        sess, data, ok = boot_to_s6044()
        if not ok:
            print("boot fail", flush=True)
            continue
        d0, free, fr15 = dump(data, "base")

        if name == "N6038-then-vacE-S":
            north = min(free, key=lambda w: (w[1], w[0]))
            south = max(free, key=lambda w: (w[1], w[0]))
            data, _, st = move_wp(sess, data, north, (60, 38), fr15)
            print(f"  N6038 {st} bud={step_budget(data['frame'])}", flush=True)
            if st != "moved":
                continue
            dump(data, "afterN")
            # vac with remaining bud
            freeze14 = lock_other_ship(data["frame"], 15)
            flock = list(lock_other_ship(data["frame"], 14))
            east = max(flock, key=lambda w: w[0])
            data, _, st = move_wp(sess, data, east, (58, 54), freeze14)
            print(f"  vacE {st} bud={step_budget(data['frame'])}", flush=True)
            dump(data, "FINAL")
            continue

        # vacE first
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        east = max(flock, key=lambda w: w[0])
        west = min(flock, key=lambda w: w[0])
        vac_ok = False
        for et in etgts:
            if max(abs(et[0] - west[0]), abs(et[1] - west[1])) < 5:
                continue
            data, newc, st = move_wp(sess, data, east, et, freeze14)
            print(f"  vacE {east}->{et} {st}->{newc} bud={step_budget(data['frame'])}", flush=True)
            if st == "moved":
                vac_ok = True
                dump(data, "after-vac")
                break
            if st == "dead":
                break
        if not vac_ok:
            print("vac fail", flush=True)
            continue

        # S then N
        for who, tgt in (stgts or []) + (ntgts or []):
            if step_budget(data["frame"]) < 3:
                print("budout", flush=True)
                break
            fr15 = lock_other_ship(data["frame"], 14)
            free = count_free14(data["frame"], fr15)
            # raw pair: two pads closest to ship14 among non-deep15
            me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
            wps = [w["c"] for w in r11l.waypoints(data["frame"])]
            cand = [
                c
                for c in wps
                if c not in ((42, 50), (58, 54), (58, 50), (62, 52))
                and manh(c, me14["c"]) <= 35
            ]
            if len(cand) < 2:
                cand = [c for c in wps if manh(c, me14["c"]) <= manh(c, me15["c"]) + 8]
            if len(cand) < 2:
                print(f"bad cand {cand} all={wps}", flush=True)
                break
            north = min(cand, key=lambda w: (w[1], w[0]))
            south = max(cand, key=lambda w: (w[1], w[0]))
            cur = north if who == "N" else south
            other = south if who == "N" else north
            if cheb(tgt, other) < 5:
                print(f"  {who}->{tgt} merge", flush=True)
                continue
            if near_any(tgt, list(fr15), cheb=5):
                print(f"  {who}->{tgt} near15", flush=True)
                continue
            # freeze true 15 only
            freeze15 = [c for c in fr15 if c != cur]
            for p in ((42, 50), (58, 54), (58, 50)):
                if p in wps and p not in freeze15:
                    freeze15.append(p)
            freeze15 = [p for p in freeze15 if p != cur]
            data, newc, st = move_wp(sess, data, cur, tgt, freeze15)
            print(
                f"  {who} {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}",
                flush=True,
            )
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD", flush=True)
                break
            if st != "moved":
                continue
            d1, free1, _ = dump(data, f"after-{tgt}")
            if len(free1) != 2:
                # check raw
                wps = [w["c"] for w in r11l.waypoints(data["frame"])]
                print(f"  lock-n={len(free1)} all={sorted(wps)}", flush=True)
            if d1 < d0:
                print(f"IMPROVED {d0}->{d1}", flush=True)
                d0 = d1
        dump(data, "FINAL")


if __name__ == "__main__":
    main()
