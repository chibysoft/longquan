"""Skip east15b@(58,54): deep only E5842+W4250, then SE chain; more bud, east@58,42."""
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


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me14["c"][0] - 55) + abs(me14["c"][1] - 53)
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me14['c']} d14={d14} free={sorted(free)} "
        f"d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14


def deep15_short(sess, data):
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    print(f"  E5842 {st}", flush=True)
    if st != "moved":
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    print(f"  W4250 {st} bud={step_budget(data['frame'])}", flush=True)
    return data, st == "moved"


def se_chain(sess, data, *, s_tgt=(60, 48)):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lag = min(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lag, (36, 44), fr15)
    print(f"  lagDirect {st}", flush=True)
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
    data, _, st = move_wp(sess, data, south, (60, 44), fr15)
    print(f"  S6044 {st}", flush=True)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (60, 38), fr15)
    print(f"  N6038 {st}", flush=True)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    if near_any(s_tgt, list(fr15), cheb=5):
        print(f"  S{s_tgt} near15", flush=True)
        return data, False
    if max(abs(s_tgt[0] - north[0]), abs(s_tgt[1] - north[1])) < 5:
        print(f"  S{s_tgt} merge", flush=True)
        return data, False
    data, _, st = move_wp(sess, data, south, s_tgt, fr15)
    print(f"  S {s_tgt} {st} bud={step_budget(data['frame'])}", flush=True)
    return data, st == "moved"


def boot_and(label, s_tgt, extra=None):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_noe54"]},
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
    data, ok = deep15_short(sess, data)
    if not ok:
        print("deep fail", flush=True)
        return
    data, ok = se_chain(sess, data, s_tgt=s_tgt)
    dump(data, f"after-{label}")
    if not ok or extra is None:
        return
    # one extra move
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    who, tgt = extra
    cur = south if who == "S" else north
    other = north if who == "S" else south
    if near_any(tgt, list(fr15), cheb=5) or max(abs(tgt[0] - other[0]), abs(tgt[1] - other[1])) < 5:
        print(f"  extra skip near/merge", flush=True)
        return
    d0 = dump(data, "pre-extra")
    data, newc, st = move_wp(sess, data, cur, tgt, fr15)
    print(f"  extra {who}->{tgt} {st}->{newc}", flush=True)
    if st == "moved" and "frame" in data:
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        d1 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(f"RESULT d14 {d0}->{d1} bud={step_budget(data['frame'])}", flush=True)


def main():
    plans = [
        ("S6048", (60, 48), None),
        ("S6248", (62, 48), None),
        ("S6048-S5553", (60, 48), ("S", (55, 53))),
        ("S6048-S5652", (60, 48), ("S", (56, 52))),
        ("S6048-S5252", (60, 48), ("S", (52, 52))),
        ("S6048-S5052", (60, 48), ("S", (50, 52))),
    ]
    for label, stgt, extra in plans:
        print(f"\n===== {label} =====", flush=True)
        boot_and(label, stgt, extra)
    print("\n===== DONE =====", flush=True)


if __name__ == "__main__":
    main()
