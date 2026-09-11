"""From se-ny endpose (46,36)+(48,42) d14=34 bud≈11: find IMPROVED hops.
Also try bigger extE before Ny; and collapse-only (skip +5) for more bud.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import (
    advance_14_mid_east,
    collapse_to_2,
    ensure_y34,
    west_to_neck,
    _install_reshape_cap3,
)
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
    return d14, free, fr15, step_budget(data["frame"])


def open_sess(tag):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": [f"r11l_{tag}"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    return sess, data, data.get("levels_completed") or 0


def deep15(sess, data):
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    if st == "dead":
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    if st == "dead":
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, max(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (58, 50), freeze14
    )
    return data, st != "dead"


def se_ny(sess, data, ext=(36, 44), nyt=(46, 36)):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) != 2:
        return data, False
    lag = min(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lag, (26, 44), fr15)
    if st != "moved":
        print(f"  lagSE {st}", flush=True)
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    src = (26, 44) if (26, 44) in free else max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, src, ext, fr15)
    print(f"  extE {src}->{ext} {st}", flush=True)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return data, False
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    if near_any(nyt, list(fr15), cheb=5) or cheb(nyt, south) < 5:
        print(f"  Ny skip {nyt}", flush=True)
        return data, False
    data, _, st = move_wp(sess, data, north, nyt, fr15)
    print(f"  Ny {north}->{nyt} {st}", flush=True)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, (48, 42), fr15)
    print(f"  S {south}->(48,42) {st}", flush=True)
    if st != "moved":
        return data, False
    dump(data, "END")
    return data, True


def boot_end(mid_east=True):
    sess, data, lv0 = open_sess("cont")
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    if mid_east:
        data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
    else:
        _install_reshape_cap3()
        freeze15 = lock_other_ship(data["frame"], 14)
        data, _ = west_to_neck(sess, data, freeze15, lv0)
        freeze15 = lock_other_ship(data["frame"], 14)
        data, _ = ensure_y34(sess, data, freeze15)
        freeze15 = lock_other_ship(data["frame"], 14)
        data, _ = collapse_to_2(sess, data, freeze15)
        dump(data, "COLLAPSE")
    data, ok = deep15(sess, data)
    if not ok:
        return sess, data, False
    data, ok = se_ny(sess, data)
    return sess, data, ok


# Known dead/noop under Ny46 pose
KNOWN_BAD = {
    (50, 36),
    (52, 36),
    (48, 36),
    (50, 42),
    (52, 42),
    (52, 44),
    (54, 44),
    (50, 44),
    (50, 46),
    (52, 46),
    (48, 46),
    (48, 48),
    (52, 48),
    (50, 48),
}


def run_cont_scan():
    print("\n===== CONT from se-ny end =====", flush=True)
    cands = []
    # north from (46,36) — need cheb>=5 from (48,42)
    for t in (
        (50, 38),
        (52, 38),
        (54, 38),
        (50, 40),
        (52, 40),
        (48, 40),
        (47, 40),
        (49, 40),
        (51, 38),
        (53, 40),
        (46, 40),
        (44, 40),
        (46, 42),
        (44, 42),
        (42, 40),
        (52, 36),  # known noop — confirm
    ):
        cands.append(("N", t))
    # south from (48,42)
    for t in (
        (54, 46),
        (56, 44),
        (56, 46),
        (54, 48),
        (52, 50),
        (50, 50),
        (48, 50),
        (46, 48),
        (44, 48),
        (54, 42),
        (56, 42),
        (55, 45),
        (53, 47),
        (51, 49),
    ):
        cands.append(("S", t))

    hits = []
    for who, tgt in cands:
        if tgt in KNOWN_BAD:
            continue
        print(f"\n===== {who}->{tgt} =====", flush=True)
        sess, data, ok = boot_end(True)
        if not ok:
            print("boot fail", flush=True)
            continue
        d0, free, fr15, bud = dump(data, "base")
        if len(free) != 2 or bud < 4:
            continue
        north = min(free, key=lambda w: (w[1], w[0]))
        south = max(free, key=lambda w: (w[1], w[0]))
        cur = north if who == "N" else south
        other = south if who == "N" else north
        if cheb(tgt, other) < 5 or near_any(tgt, list(fr15), cheb=5):
            print("skip", flush=True)
            continue
        if cheb(tgt, cur) <= 1:
            print("tiny", flush=True)
            continue
        data, newc, st = move_wp(sess, data, cur, tgt, fr15)
        print(f"  {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", flush=True)
            continue
        if st != "moved":
            continue
        d1, free1, _, bud1 = dump(data, "after")
        if len(free1) != 2:
            print(f"FLOCK n={len(free1)}", flush=True)
            continue
        if d1 < d0:
            print(f"IMPROVED {d0}->{d1} bud={bud1}", flush=True)
            hits.append((who, tgt, d0, d1, bud1, free1))
        elif d1 == d0:
            print(f"FLAT bud={bud1} — maybe reposition", flush=True)
            hits.append(("FLAT", tgt, d0, d1, bud1, free1))
        else:
            print("WORSE", flush=True)
    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    if not hits:
        print("none", flush=True)
    return hits


def run_bigger_ext():
    print("\n===== bigger extE before Ny =====", flush=True)
    for ext in ((38, 44), (40, 44), (42, 44), (40, 46), (38, 46), (42, 46)):
        print(f"\n--- ext={ext} ---", flush=True)
        sess, data, lv0 = open_sess(f"ext{ext[0]}")
        freeze14 = lock_other_ship(data["frame"], 15)
        data, _ = clear15_corridor(sess, data, freeze14)
        data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
        data, ok = deep15(sess, data)
        if not ok:
            continue
        data, ok = se_ny(sess, data, ext=ext, nyt=(46, 36))
        if not ok:
            # try Ny44 if 46 merge
            sess, data, lv0 = open_sess(f"extb{ext[0]}")
            freeze14 = lock_other_ship(data["frame"], 15)
            data, _ = clear15_corridor(sess, data, freeze14)
            data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
            data, ok = deep15(sess, data)
            if ok:
                data, ok = se_ny(sess, data, ext=ext, nyt=(44, 36))
        if ok and "frame" in data:
            d14, free, _, bud = dump(data, f"EXTdone")
            beat = d14 < 34 or (d14 <= 34 and bud >= 12)
            print(
                f"=== {'BEAT' if beat else 'best'} ext{ext}: d14={d14} bud={bud} free={sorted(free)} ===",
                flush=True,
            )


def run_collapse_only():
    print("\n===== collapse-only se-ny (more bud) =====", flush=True)
    sess, data, ok = boot_end(mid_east=False)
    if ok:
        d14, free, _, bud = dump(data, "COLend")
        beat = d14 < 34 or (d14 <= 34 and bud >= 12)
        print(
            f"=== {'BEAT' if beat else 'best'} collapse: d14={d14} bud={bud} free={sorted(free)} ===",
            flush=True,
        )


def main():
    run_bigger_ext()
    run_collapse_only()
    run_cont_scan()


if __name__ == "__main__":
    main()
