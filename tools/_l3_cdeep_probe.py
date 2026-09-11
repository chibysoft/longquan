"""Compact deep15: fewer moves and/or park 15 closer to goal (34,57).

Baseline 3-move: E(58,42) W(42,50) E(58,50) → ship15~(50,50) d15=23 bud≈22.
Try 2-move and goal-side west/east targets; then run se-ny to N6038 and report.
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
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} "
        f"bud={step_budget(data['frame'])} lv={data.get('levels_completed')}",
        flush=True,
    )
    return d14, d15, free, fr15, step_budget(data["frame"])


def open_sess():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_cdeep"]},
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
    return sess, data


def apply_deep(sess, data, steps):
    """steps: list of ('E'|'W', tgt) relative to current flock15."""
    for who, tgt in steps:
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        if len(flock) < 2:
            print(f"  flock15 n={len(flock)}", flush=True)
            return data, False
        west = min(flock, key=lambda w: w[0])
        east = max(flock, key=lambda w: w[0])
        cur = east if who == "E" else west
        other = west if who == "E" else east
        if cheb(tgt, other) < 5:
            print(f"  {who}->{tgt} merge", flush=True)
            return data, False
        if near_any(tgt, count_free14(data["frame"], freeze14) if False else [], cheb=5):
            pass
        # don't land on 14's free
        fr15 = lock_other_ship(data["frame"], 14)
        free14 = count_free14(data["frame"], fr15)
        if near_any(tgt, free14, cheb=5):
            print(f"  {who}->{tgt} near14", flush=True)
            return data, False
        data, newc, st = move_wp(sess, data, cur, tgt, freeze14)
        print(f"  {who} {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame'])}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            return data, False
        if st != "moved":
            return data, False
    return data, True


def se_ny_to_n6038(sess, data):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) != 2:
        print(f"  free14 n={len(free)} {free}", flush=True)
        return data, False
    lag = min(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lag, (26, 44), fr15)
    print(f"  lagSE {st}", flush=True)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    src = (26, 44) if (26, 44) in free else max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, src, (36, 44), fr15)
    print(f"  extE {st}", flush=True)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (46, 36), fr15)
    print(f"  Ny {st}", flush=True)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (48, 32), fr15)
    print(f"  N4832 {st}", flush=True)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, (60, 44), fr15)
    print(f"  S6044 {st}", flush=True)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    for nt in ((60, 38), (56, 38), (52, 38)):
        if cheb(nt, south) < 5 or near_any(nt, list(fr15), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, north, nt, fr15)
        print(f"  N {north}->{nt} {st}->{newc}", flush=True)
        if st == "moved":
            return data, True
        if st == "dead" or data.get("state") == "GAME_OVER":
            return data, False
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) < 2:
            return data, False
        north = min(free, key=lambda w: (w[1], w[0]))
        south = max(free, key=lambda w: (w[1], w[0]))
    return data, False


PLANS = [
    ("base3", [("E", (58, 42)), ("W", (42, 50)), ("E", (58, 50))]),
    ("e5850_w4250", [("E", (58, 50)), ("W", (42, 50))]),
    ("e5850_w3852", [("E", (58, 50)), ("W", (38, 52))]),
    ("e5850_w3654", [("E", (58, 50)), ("W", (36, 54))]),
    ("e5850_w3456", [("E", (58, 50)), ("W", (34, 56))]),
    ("w4250_e5850", [("W", (42, 50)), ("E", (58, 50))]),
    ("e5842_w3852_e5850", [("E", (58, 42)), ("W", (38, 52)), ("E", (58, 50))]),
    ("e5842_w3654_e5850", [("E", (58, 42)), ("W", (36, 54)), ("E", (58, 50))]),
    ("e5842_w4250_e5854", [("E", (58, 42)), ("W", (42, 50)), ("E", (58, 54))]),
]


def main():
    summary = []
    for name, steps in PLANS:
        print(f"\n===== {name} =====", flush=True)
        sess, data = open_sess()
        dump(data, "gate")
        data, ok = apply_deep(sess, data, steps)
        if not ok:
            print("deep fail", flush=True)
            summary.append((name, "deep-fail", None, None, None))
            continue
        dump(data, "deep")
        data, ok = se_ny_to_n6038(sess, data)
        if not ok:
            dump(data, "seny-fail")
            summary.append((name, "seny-fail", None, None, step_budget(data["frame"]) if "frame" in data else -1))
            continue
        d14, d15, free, fr15, bud = dump(data, "END")
        summary.append((name, "ok", d14, d15, bud))

    print("\n===== SUMMARY =====", flush=True)
    for row in summary:
        print(row, flush=True)


if __name__ == "__main__":
    main()
