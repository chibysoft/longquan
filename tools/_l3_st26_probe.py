"""From N6038+S6044 pose d14=26 bud≈5: scan same-col exits."""
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
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(
        f"{label} ship={me['c']} d14={d14} free={sorted(free)} "
        f"fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, free, fr15


def boot():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_st26"]},
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
    data, ok = advance_14_frog_ny_stack(sess, data, (34, 57))
    if not ok:
        return sess, data, False
    dump(data, "END")
    return sess, data, True


# Prefer SE for ship goal (55,53); then N south/east; avoid known west noop (58,38)
CANDS = [
    ("S", (62, 48)),
    ("S", (58, 48)),
    ("S", (56, 48)),
    ("S", (62, 46)),
    ("S", (64, 46)),
    ("S", (58, 46)),
    ("S", (62, 44)),
    ("S", (56, 46)),
    ("S", (54, 48)),
    ("N", (60, 32)),
    ("N", (58, 34)),
    ("N", (62, 36)),
    ("N", (56, 36)),
    ("N", (62, 34)),
    ("N", (58, 32)),
    ("N", (60, 34)),
    ("N", (56, 34)),
    ("N", (54, 36)),
    ("N", (62, 38)),
    ("N", (58, 40)),
]


def main():
    hits = []
    soft = []
    dead = []
    sess, data, ok = boot()
    if not ok:
        print("boot fail", flush=True)
        return
    d0, free, fr15 = dump(data, "base")
    if len(free) != 2:
        print(f"bad free {free}", flush=True)
        return
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    live = []
    for who, tgt in CANDS:
        cur = north if who == "N" else south
        other = south if who == "N" else north
        if not (0 <= tgt[0] < 64 and 0 <= tgt[1] < 64):
            continue
        if cheb(tgt, other) < 5 or near_any(tgt, list(fr15), cheb=5):
            continue
        if cheb(tgt, cur) <= 1:
            continue
        live.append((who, tgt))
    print(f"N={north} S={south} live={live}", flush=True)

    i = 0
    while i < len(live):
        if step_budget(data["frame"]) < 3:
            print("budout — reboot", flush=True)
            sess, data, ok = boot()
            if not ok:
                break
            d0, free, fr15 = dump(data, "rebase")
            if len(free) != 2:
                break
            north = min(free, key=lambda w: (w[1], w[0]))
            south = max(free, key=lambda w: (w[1], w[0]))

        who, tgt = live[i]
        i += 1
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) != 2:
            sess, data, ok = boot()
            if not ok:
                break
            d0, free, fr15 = dump(data, "refree")
            continue
        north = min(free, key=lambda w: (w[1], w[0]))
        south = max(free, key=lambda w: (w[1], w[0]))
        cur = north if who == "N" else south
        other = south if who == "N" else north
        if cheb(tgt, other) < 5 or near_any(tgt, list(fr15), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, cur, tgt, fr15)
        bud = step_budget(data["frame"]) if "frame" in data else -1
        print(f"  {who} {cur}->{tgt} {st}->{newc} bud={bud}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", flush=True)
            dead.append((who, tgt))
            sess, data, ok = boot()
            if not ok:
                break
            d0, free, fr15 = dump(data, "redead")
            continue
        if st != "moved":
            soft.append((who, tgt, st))
            continue
        d1, free1, _ = dump(data, "after")
        if len(free1) != 2:
            print(f"FLOCK n={len(free1)}", flush=True)
            dead.append((who, tgt))
            sess, data, ok = boot()
            if not ok:
                break
            d0, free, fr15 = dump(data, "reflock")
            continue
        if d1 < d0:
            print(f"IMPROVED {d0}->{d1}", flush=True)
            hits.append((who, tgt, d0, d1, bud, sorted(free1)))
            d0 = d1
            north = min(free1, key=lambda w: (w[1], w[0]))
            south = max(free1, key=lambda w: (w[1], w[0]))
        elif d1 == d0:
            print("FLAT", flush=True)
            soft.append((who, tgt, "flat"))
            north = min(free1, key=lambda w: (w[1], w[0]))
            south = max(free1, key=lambda w: (w[1], w[0]))
        else:
            print("WORSE", flush=True)
            soft.append((who, tgt, "worse"))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    if not hits:
        print("none", flush=True)
    print("soft", soft, flush=True)
    print("dead", dead, flush=True)


if __name__ == "__main__":
    main()
