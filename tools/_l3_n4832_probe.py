"""N→(48,32) FLAT then batch-scan S SE (soft-fail keeps pose)."""
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


def boot_n4832():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_n4832b"]},
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
    south = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, (48, 42), fr15)
    if st != "moved":
        return sess, data, False
    # N→(48,32) FLAT live
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (48, 32), fr15)
    if st != "moved":
        print(f"N4832 {st}", flush=True)
        return sess, data, False
    dump(data, "N4832")
    return sess, data, True


S_CANDS = [
    (54, 44),
    (56, 44),
    (52, 46),
    (50, 48),
    (52, 48),
    (54, 48),
    (48, 50),
    (50, 50),
    (52, 50),
    (54, 42),
    (56, 42),
    (52, 42),
    (50, 46),
    (56, 48),
    (55, 47),
    (53, 49),
    (51, 51),
    (46, 48),
    (44, 46),
    (50, 44),
    (52, 44),
    (54, 46),
    (58, 46),
    (60, 44),
    (56, 50),
]


def main():
    hits = []
    soft = []
    dead = []
    sess, data, ok = boot_n4832()
    if not ok:
        print("boot fail", flush=True)
        return
    d0, free, fr15 = dump(data, "base")
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    live = []
    for tgt in S_CANDS:
        if cheb(tgt, north) < 5:
            continue
        if near_any(tgt, list(fr15), cheb=5):
            continue
        live.append(tgt)
    print(f"live S={live}", flush=True)

    i = 0
    while i < len(live):
        if step_budget(data["frame"]) < 4:
            print("budout — reboot", flush=True)
            sess, data, ok = boot_n4832()
            if not ok:
                break
            d0, free, fr15 = dump(data, "rebase")
            north = min(free, key=lambda w: (w[1], w[0]))
            south = max(free, key=lambda w: (w[1], w[0]))

        tgt = live[i]
        i += 1
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
        if cheb(tgt, north) < 5 or near_any(tgt, list(fr15), cheb=5):
            print(f"  skip {tgt}", flush=True)
            continue
        data, newc, st = move_wp(sess, data, south, tgt, fr15)
        bud = step_budget(data["frame"]) if "frame" in data else -1
        print(f"  S {south}->{tgt} {st}->{newc} bud={bud}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", flush=True)
            dead.append(tgt)
            sess, data, ok = boot_n4832()
            if not ok:
                break
            d0, free, fr15 = dump(data, "redead")
            north = min(free, key=lambda w: (w[1], w[0]))
            south = max(free, key=lambda w: (w[1], w[0]))
            continue
        if st != "moved":
            soft.append((tgt, st))
            continue
        d1, free1, _ = dump(data, "after")
        if len(free1) != 2:
            print(f"FLOCK n={len(free1)}", flush=True)
            dead.append(tgt)
            sess, data, ok = boot_n4832()
            if not ok:
                break
            d0, free, fr15 = dump(data, "reflock")
            continue
        if d1 < d0:
            print(f"IMPROVED {d0}->{d1}", flush=True)
            hits.append((tgt, d0, d1, bud, sorted(free1)))
            d0 = d1
            north = min(free1, key=lambda w: (w[1], w[0]))
            south = max(free1, key=lambda w: (w[1], w[0]))
        elif d1 == d0:
            print("FLAT", flush=True)
            soft.append((tgt, "flat"))
            north = min(free1, key=lambda w: (w[1], w[0]))
            south = max(free1, key=lambda w: (w[1], w[0]))
        else:
            print("WORSE", flush=True)
            soft.append((tgt, "worse"))
            north = min(free1, key=lambda w: (w[1], w[0]))
            south = max(free1, key=lambda w: (w[1], w[0]))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    if not hits:
        print("none", flush=True)
    print("soft", soft, flush=True)
    print("dead", dead, flush=True)


if __name__ == "__main__":
    main()
