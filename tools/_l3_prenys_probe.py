"""After Ny46 BEFORE S4842: try better S SE / N4832 order (more cheb room)."""
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
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(
        f"{label} ship={me['c']} d14={d14} free={sorted(free)} "
        f"fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, free, fr15


def boot_to_ny46():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_prenys"]},
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
    dump(data, "NY46")
    return sess, data, True


# Plans: ordered move lists from Ny46 pose (north y36, south y44)
PLANS = [
    ("N4832-S4842", [("N", (48, 32)), ("S", (48, 42))]),
    ("N4832-S5246", [("N", (48, 32)), ("S", (52, 46))]),
    ("N4832-S5048", [("N", (48, 32)), ("S", (50, 48))]),
    ("N4832-S5448", [("N", (48, 32)), ("S", (54, 48))]),
    ("S5246-N4832", [("S", (52, 46)), ("N", (48, 32))]),
    ("S5046-N5032", [("S", (50, 46)), ("N", (50, 32))]),
    ("S4842-N4832", [("S", (48, 42)), ("N", (48, 32))]),  # baseline order
    ("S4046-N5036", [("S", (40, 46)), ("N", (50, 36))]),
    ("S4046-N5436", [("S", (40, 46)), ("N", (54, 36))]),
    ("direct-S5446", [("S", (54, 46))]),
    ("direct-S5248", [("S", (52, 48))]),
    ("N5032-S5246", [("N", (50, 32)), ("S", (52, 46))]),
]


def main():
    best = None
    for name, steps in PLANS:
        print(f"\n===== {name} =====", flush=True)
        sess, data, ok = boot_to_ny46()
        if not ok:
            print("boot fail", flush=True)
            continue
        d0, free, fr15 = dump(data, "start")
        failed = False
        for who, tgt in steps:
            fr15 = lock_other_ship(data["frame"], 14)
            free = count_free14(data["frame"], fr15)
            if len(free) != 2:
                print(f"flock n={len(free)}", flush=True)
                failed = True
                break
            north = min(free, key=lambda w: (w[1], w[0]))
            south = max(free, key=lambda w: (w[1], w[0]))
            cur = north if who == "N" else south
            other = south if who == "N" else north
            if cheb(tgt, other) < 5:
                print(f"  {who}->{tgt} merge{cheb(tgt, other)}", flush=True)
                failed = True
                break
            if near_any(tgt, list(fr15), cheb=5):
                print(f"  {who}->{tgt} near15", flush=True)
                failed = True
                break
            data, newc, st = move_wp(sess, data, cur, tgt, fr15)
            print(
                f"  {who} {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}",
                flush=True,
            )
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD", flush=True)
                failed = True
                break
            if st != "moved":
                failed = True
                break
        if failed:
            continue
        d1, free1, _ = dump(data, "end")
        if len(free1) != 2:
            print(f"FLOCK end n={len(free1)}", flush=True)
            continue
        delta = d1 - d0
        bud = step_budget(data["frame"])
        print(f"RESULT d14 {d0}->{d1} ({delta:+d}) bud={bud} free={sorted(free1)}", flush=True)
        if best is None or d1 < best[1] or (d1 == best[1] and bud > best[2]):
            best = (name, d1, bud, sorted(free1))

    print("\n===== BEST =====", flush=True)
    print(best, flush=True)


if __name__ == "__main__":
    main()
