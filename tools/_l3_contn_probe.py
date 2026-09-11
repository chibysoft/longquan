"""From se-ny endpose: only N targets with cheb>=5 vs S(48,42). Soft-fail keeps pose."""
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


def boot_to_seny():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_contn"]},
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
    # deep15
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
    # lagSE + extE + Ny46 + S4842
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
    dump(data, "END")
    return sess, data, True


# cheb>=5 vs (48,42); prefer reducing d14 (east/south of ship goal 55,53)
# north pad starts (46,36)
CANDS = [
    (54, 36),
    (56, 36),
    (58, 36),
    (52, 36),
    (54, 38),
    (56, 38),
    (58, 38),
    (54, 34),
    (56, 34),
    (52, 34),
    (50, 34),
    (48, 32),
    (46, 32),
    (44, 34),
    (42, 34),
    (42, 38),
    (44, 32),
    (50, 32),
    (52, 32),
    (40, 36),
    (40, 32),
    (58, 40),
    (56, 40),  # cheb to S=max(8,2)=8
    (54, 40),  # cheb=max(6,2)=6
    (52, 40),  # cheb=max(4,2)=4 ILLEGAL — keep for filter check
]


def main():
    hits = []
    dead = []
    soft = []
    skip = []
    sess, data, ok = boot_to_seny()
    if not ok:
        print("boot fail", flush=True)
        return
    d0, free0, fr150 = dump(data, "base")
    south0 = max(free0, key=lambda w: (w[1], w[0]))
    north0 = min(free0, key=lambda w: (w[1], w[0]))
    print(f"N={north0} S={south0} filter vs S+15", flush=True)

    # offline filter
    live = []
    for tgt in CANDS:
        if cheb(tgt, south0) < 5:
            skip.append((tgt, f"merge{cheb(tgt, south0)}"))
            continue
        if near_any(tgt, list(fr150), cheb=5):
            skip.append((tgt, "near15"))
            continue
        if cheb(tgt, north0) <= 1:
            skip.append((tgt, "tiny"))
            continue
        live.append(tgt)
    print(f"live={live}", flush=True)
    print(f"skip={skip}", flush=True)

    i = 0
    while i < len(live):
        if step_budget(data["frame"]) < 4:
            print("budout — reboot", flush=True)
            sess, data, ok = boot_to_seny()
            if not ok:
                print("reboot fail", flush=True)
                break
            d0, free0, fr150 = dump(data, "rebase")
            south0 = max(free0, key=lambda w: (w[1], w[0]))
            north0 = min(free0, key=lambda w: (w[1], w[0]))

        tgt = live[i]
        i += 1
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if north0 not in free:
            # pose drifted — find current north
            north0 = min(free, key=lambda w: (w[1], w[0]))
            south0 = max(free, key=lambda w: (w[1], w[0]))
        if cheb(tgt, south0) < 5 or near_any(tgt, list(fr15), cheb=5):
            print(f"  skip-late {tgt}", flush=True)
            continue

        data, newc, st = move_wp(sess, data, north0, tgt, fr15)
        bud = step_budget(data["frame"]) if "frame" in data else -1
        print(f"  N {north0}->{tgt} {st}->{newc} bud={bud}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", flush=True)
            dead.append(tgt)
            sess, data, ok = boot_to_seny()
            if not ok:
                break
            d0, free0, fr150 = dump(data, "redead")
            south0 = max(free0, key=lambda w: (w[1], w[0]))
            north0 = min(free0, key=lambda w: (w[1], w[0]))
            continue
        if st != "moved":
            soft.append((tgt, st))
            # pose unchanged; north still north0
            continue

        d1, free1, _ = dump(data, "after")
        if len(free1) != 2:
            print(f"FLOCK n={len(free1)}", flush=True)
            dead.append(tgt)
            sess, data, ok = boot_to_seny()
            if not ok:
                break
            d0, free0, fr150 = dump(data, "reflock")
            south0 = max(free0, key=lambda w: (w[1], w[0]))
            north0 = min(free0, key=lambda w: (w[1], w[0]))
            continue
        if d1 < d0:
            print(f"IMPROVED {d0}->{d1}", flush=True)
            hits.append((tgt, d0, d1, bud, sorted(free1)))
            # keep going from new pose with remaining live that still legal
            north0 = min(free1, key=lambda w: (w[1], w[0]))
            south0 = max(free1, key=lambda w: (w[1], w[0]))
            d0 = d1
        elif d1 == d0:
            print("FLAT", flush=True)
            soft.append((tgt, "flat"))
            north0 = min(free1, key=lambda w: (w[1], w[0]))
            south0 = max(free1, key=lambda w: (w[1], w[0]))
        else:
            print("WORSE", flush=True)
            soft.append((tgt, "worse"))
            north0 = min(free1, key=lambda w: (w[1], w[0]))
            south0 = max(free1, key=lambda w: (w[1], w[0]))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    if not hits:
        print("none", flush=True)
    print("soft", soft, flush=True)
    print("dead", dead, flush=True)


if __name__ == "__main__":
    main()
