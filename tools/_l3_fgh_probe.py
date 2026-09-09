"""Non-frog / budget-rich alts:
  F: skip mid-east +5 translate — frog from collapse bud≈37
  G: Y40 → frog(26,44) → alt N (not Ny36) then SE
  H: Y40 micro dual (lead tiny + lag catch)
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
    dump(data, "DEEP15")
    return data, st != "dead"


def frog_chain(sess, data, n_tgts, s_tgts, ne_tgts=None):
    """leadS+4 → frog → N → S → optional Ne. Returns best (d14,bud,free,ship)."""
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) != 2:
        return data, None
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print(f"  leadS {st}", flush=True)
    if st != "moved":
        return data, None
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    frog = (lag[0] + 2, lead[1] + 4)
    data, _, st = move_wp(sess, data, lag, frog, fr15)
    print(f"  frog {lag}->{frog} {st}", flush=True)
    if st != "moved":
        return data, None
    dump(data, "FROG")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    moved_n = False
    for nt in n_tgts:
        if near_any(nt, list(fr15), cheb=5):
            continue
        if cheb(nt, south) < 5:
            continue
        data, _, st = move_wp(sess, data, north, nt, fr15)
        print(f"  N {north}->{nt} {st}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            return data, None
        if st == "moved":
            moved_n = True
            break
    if not moved_n:
        return data, None
    dump(data, "N")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) != 2:
        return data, None
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    for stgt in s_tgts:
        if near_any(stgt, list(fr15), cheb=5):
            continue
        if cheb(stgt, north) < 5:
            continue
        data, _, st = move_wp(sess, data, south, stgt, fr15)
        print(f"  S {south}->{stgt} {st}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            return data, None
        if st == "moved":
            break
    d14, free, fr15, bud = dump(data, "S")
    if ne_tgts and bud >= 4 and len(free) == 2:
        north = min(free, key=lambda w: (w[1], w[0]))
        south = max(free, key=lambda w: (w[0], w[1]))
        for nt in ne_tgts:
            if near_any(nt, list(fr15), cheb=5):
                continue
            if cheb(nt, south) < 5:
                continue
            data, _, st = move_wp(sess, data, north, nt, fr15)
            print(f"  Ne {north}->{nt} {st}", flush=True)
            if st == "dead" or data.get("state") == "GAME_OVER":
                break
            if st == "moved":
                d14, free, fr15, bud = dump(data, "Ne")
                break
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    return data, (d14, bud, free, me["c"])


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


def run_F():
    print("\n===== F collapse-only frog (skip +5) =====", flush=True)
    sess, data, lv0 = open_sess("F")
    _install_reshape_cap3()
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    freeze15 = lock_other_ship(data["frame"], 14)
    data, _ = west_to_neck(sess, data, freeze15, lv0)
    freeze15 = lock_other_ship(data["frame"], 14)
    data, _ = ensure_y34(sess, data, freeze15)
    freeze15 = lock_other_ship(data["frame"], 14)
    data, _ = collapse_to_2(sess, data, freeze15)
    dump(data, "COLLAPSE")
    data, ok = deep15(sess, data)
    if not ok:
        print("deep fail", flush=True)
        return
    # Same frog chain as C but with extra ~5 bud
    data, res = frog_chain(
        sess,
        data,
        n_tgts=((40, 36), (38, 36), (42, 36)),
        s_tgts=((48, 42), (40, 44), (40, 46)),
        ne_tgts=((45, 36), (44, 36)),
    )
    if res:
        d14, bud, free, ship = res
        beat = d14 < 34 or (d14 <= 34 and bud >= 8)
        print(
            f"=== {'BEAT' if beat else 'best'} F: d14={d14} bud={bud} ship={ship} free={free} ===",
            flush=True,
        )
    else:
        print("=== FAIL F ===", flush=True)


def run_G():
    print("\n===== G Y40 frog then alt N =====", flush=True)
    # variants of N target
    for n_tgts, label in (
        (((42, 36), (40, 36)), "N42"),
        (((38, 36), (40, 36)), "N38"),
        (((40, 38), (42, 38), (40, 36)), "N4038"),
        (((36, 36), (38, 36), (40, 36)), "N36"),
        (((44, 36), (42, 36), (40, 36)), "N44"),
    ):
        print(f"\n--- G {label} ---", flush=True)
        sess, data, lv0 = open_sess(f"G{label}")
        freeze14 = lock_other_ship(data["frame"], 15)
        data, _ = clear15_corridor(sess, data, freeze14)
        data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
        data, ok = deep15(sess, data)
        if not ok:
            continue
        data, res = frog_chain(
            sess,
            data,
            n_tgts=n_tgts,
            s_tgts=((48, 42), (44, 42), (40, 44)),
            ne_tgts=((45, 36), (46, 36), (44, 36), (48, 38)),
        )
        if res:
            d14, bud, free, ship = res
            beat = d14 < 34 or (d14 <= 34 and bud >= 8)
            print(
                f"=== {'BEAT' if beat else 'best'} G-{label}: d14={d14} bud={bud} "
                f"ship={ship} free={free} ===",
                flush=True,
            )


def run_H():
    print("\n===== H Y40 micro dual =====", flush=True)
    pairs = [
        # (lead_tgt, lag_tgt_or_None for auto catch)
        ((34, 42), None),
        ((36, 40), None),
        ((37, 40), None),
        ((34, 44), None),
        ((36, 42), None),
        ((33, 44), None),  # lead south first
        ((34, 40), (28, 40)),
        ((36, 40), (28, 40)),
        ((38, 40), (30, 40)),
        ((36, 42), (28, 42)),
        ((38, 42), (30, 42)),
        ((34, 44), (26, 44)),  # classic frog-ish
        ((33, 44), (26, 44)),
    ]
    for lead_t, lag_t in pairs:
        print(f"\n--- H lead->{lead_t} lag->{lag_t} ---", flush=True)
        sess, data, lv0 = open_sess("H")
        freeze14 = lock_other_ship(data["frame"], 15)
        data, _ = clear15_corridor(sess, data, freeze14)
        data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
        data, ok = deep15(sess, data)
        if not ok:
            continue
        # to Y40
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        lead = max(free, key=lambda w: w[0])
        data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
        if st != "moved":
            print(f"leadS {st}", flush=True)
            continue
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        lead = max(free, key=lambda w: (w[1], w[0]))
        lag = min(free, key=lambda w: (w[1], w[0]))
        for gd in ((lag[0] + 2, lead[1]), (lag[0] + 4, lead[1])):
            if cheb(gd, lead) < 5:
                continue
            data, _, st = move_wp(sess, data, lag, gd, fr15)
            if st == "moved":
                break
        d0, free, fr15, bud = dump(data, "Y40")
        if len(free) != 2:
            continue
        lead = max(free, key=lambda w: w[0])
        lag = min(free, key=lambda w: w[0])
        if near_any(lead_t, list(fr15), cheb=5) or cheb(lead_t, lag) < 5:
            print("skip lead", flush=True)
            continue
        data, _, st = move_wp(sess, data, lead, lead_t, fr15)
        print(f"  lead {lead}->{lead_t} {st}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", flush=True)
            continue
        if st != "moved":
            continue
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        print(f"  post-lead free={sorted(free)} n={len(free)}", flush=True)
        if len(free) < 1:
            continue
        # catch lag
        if len(free) == 1:
            # only lead survived — try plant lag from ship? can't. fail
            print("FLOCK solo", flush=True)
            continue
        lag = min(free, key=lambda w: w[0])
        lead = max(free, key=lambda w: w[0])
        if lag_t is None:
            # auto: same row as lead, ~6 west
            lag_t2 = (lead[0] - 6, lead[1])
            if cheb(lag_t2, lead) < 5:
                lag_t2 = (lag[0] + 4, lead[1])
        else:
            lag_t2 = lag_t
        if near_any(lag_t2, list(fr15), cheb=5) or cheb(lag_t2, lead) < 5:
            print(f"skip lag {lag_t2}", flush=True)
            d1, free, _, bud = dump(data, "noshift")
        else:
            data, _, st = move_wp(sess, data, lag, lag_t2, fr15)
            print(f"  lag {lag}->{lag_t2} {st}", flush=True)
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD lag", flush=True)
                continue
            d1, free, _, bud = dump(data, "dual")
        if len(free) == 2 and d1 < d0:
            print(f"IMPROVED d14 {d0}->{d1} bud={bud}", flush=True)
            beat = d1 < 34 or (d1 <= 34 and bud >= 8)
            print(
                f"=== {'BEAT' if beat else 'best'} H: d14={d1} bud={bud} free={free} ===",
                flush=True,
            )


def main():
    run_F()
    run_G()
    run_H()


if __name__ == "__main__":
    main()
