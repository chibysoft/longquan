"""Fix: after Ny free often n=3 — continue S/Ne. Also try N42 east bias."""
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
    return d14, free, fr15, step_budget(data["frame"])


def boot_frog():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_n3fix"]},
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
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    if st == "dead":
        return sess, data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    if st == "dead":
        return sess, data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, max(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (58, 50), freeze14
    )
    if st == "dead":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    if st != "moved":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    if st != "moved":
        return sess, data, False
    dump(data, "FROG")
    return sess, data, True


def run_variant(name, n_tgt, s_tgts, ne_tgts):
    print(f"\n===== {name} N={n_tgt} =====", flush=True)
    sess, data, ok = boot_frog()
    if not ok:
        print("boot fail", flush=True)
        return None
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    if near_any(n_tgt, list(fr15), cheb=5) or cheb(n_tgt, south) < 5:
        print("N skip", flush=True)
        return None
    data, _, st = move_wp(sess, data, north, n_tgt, fr15)
    print(f"  N {north}->{n_tgt} {st}", flush=True)
    if st != "moved" or data.get("state") == "GAME_OVER":
        return None
    d14, free, fr15, bud = dump(data, "N")
    # Allow n>=2 (live often n=3 after Ny)
    if len(free) < 2:
        print("n<2", flush=True)
        return None
    south = max(free, key=lambda w: (w[1], w[0]))
    others = [w for w in free if w != south]
    for stgt in s_tgts:
        if near_any(stgt, list(fr15), cheb=5):
            print(f"  S{stgt} near15", flush=True)
            continue
        if any(cheb(stgt, o) < 5 for o in others):
            print(f"  S{stgt} merge", flush=True)
            continue
        data, _, st = move_wp(sess, data, south, stgt, fr15)
        print(f"  S {south}->{stgt} {st}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD S", flush=True)
            return None
        if st == "moved":
            break
        # soft fail — try next
    d14, free, fr15, bud = dump(data, "S")
    if len(free) >= 2 and bud >= 4:
        north = min(free, key=lambda w: (w[1], w[0]))
        south = max(free, key=lambda w: (w[0], w[1]))
        others = [w for w in free if w != north]
        for nt in ne_tgts:
            if near_any(nt, list(fr15), cheb=5):
                continue
            if any(cheb(nt, o) < 5 for o in others):
                continue
            data, _, st = move_wp(sess, data, north, nt, fr15)
            print(f"  Ne {north}->{nt} {st}", flush=True)
            if st == "dead" or data.get("state") == "GAME_OVER":
                break
            if st == "moved":
                d14, free, fr15, bud = dump(data, "Ne")
                break
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    beat = len(free) >= 2 and (d14 < 34 or (d14 <= 34 and bud >= 8))
    print(
        f"=== {'BEAT' if beat else 'best'} {name}: d14={d14} bud={bud} "
        f"n={len(free)} ship={me['c']} free={sorted(free)} ===",
        flush=True,
    )
    return d14, bud, free


def main():
    # Baseline: known Ny36 + S4842 + Ne45
    run_variant(
        "base",
        (40, 36),
        ((48, 42), (40, 44)),
        ((45, 36), (44, 36)),
    )
    # East-biased N then bigger S
    run_variant(
        "N42",
        (42, 36),
        ((48, 42), (50, 42), (44, 44), (48, 44)),
        ((45, 36), (46, 36), (48, 38), (44, 36)),
    )
    run_variant(
        "N44",
        (44, 36),
        ((48, 42), (50, 42), (48, 44)),
        ((46, 36), (48, 38), (45, 36)),
    )
    run_variant(
        "N38",
        (38, 36),
        ((48, 42), (44, 42), (40, 44)),
        ((45, 36), (42, 36), (44, 36)),
    )
    # After N42: try S further SE
    run_variant(
        "N42-S50",
        (42, 36),
        ((50, 44), (52, 42), (48, 46), (46, 44), (48, 42)),
        ((46, 38), (48, 38), (45, 36)),
    )


if __name__ == "__main__":
    main()
