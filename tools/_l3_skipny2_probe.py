"""skip-Ny (save ~2) → S6044 → N6038 → S6248 → more south; report d14/d15/bud."""
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
        f"d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])} "
        f"lv={data.get('levels_completed')}",
        flush=True,
    )
    return d14, d15, free, fr15, step_budget(data["frame"])


def boot(skip_ny: bool):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_skipny2"]},
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
    if st != "moved":
        return sess, data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    if st != "moved":
        return sess, data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, max(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (58, 54), freeze14
    )
    if st != "moved":
        return sess, data, False

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

    if not skip_ny:
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        north = min(free, key=lambda w: (w[1], w[0]))
        data, _, st = move_wp(sess, data, north, (46, 36), fr15)
        if st != "moved":
            return sess, data, False

    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    n_ok = False
    for nt in ((48, 32), (50, 32), (46, 32)):
        if cheb(nt, south) < 5 or near_any(nt, list(fr15), cheb=5):
            continue
        data, _, st = move_wp(sess, data, north, nt, fr15)
        print(f"  N4832 {north}->{nt} {st} bud={step_budget(data['frame'])}", flush=True)
        if st == "moved":
            n_ok = True
            break
        if st == "dead" or data.get("state") == "GAME_OVER":
            return sess, data, False
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) < 2:
            return sess, data, False
        north = min(free, key=lambda w: (w[1], w[0]))
        south = max(free, key=lambda w: (w[1], w[0]))
    if not n_ok:
        return sess, data, False
    dump(data, "N4832")
    return sess, data, True


def step(sess, data, who, tgt):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return data, "flock"
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    # After S6248, free list can steal 15 pads — prefer true SE pads for S
    if who == "S":
        cands = [w for w in free if w[0] >= 56 and w[1] >= 42]
        if cands:
            south = max(cands, key=lambda w: (w[1], w[0]))
            north = min((w for w in free if w != south), key=lambda w: (w[1], w[0]), default=north)
    cur = north if who == "N" else south
    other = south if who == "N" else north
    if cheb(tgt, other) < 5 or near_any(tgt, list(fr15), cheb=5) or cheb(tgt, cur) <= 1:
        print(f"  {who}->{tgt} skip", flush=True)
        return data, "skip"
    data, newc, st = move_wp(sess, data, cur, tgt, fr15)
    print(
        f"  {who} {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}",
        flush=True,
    )
    if st == "dead" or data.get("state") == "GAME_OVER":
        return data, "dead"
    return data, st


CHAIN = [
    ("S", (60, 44)),
    ("N", (60, 38)),
    ("S", (62, 48)),
    # continue south/west toward goal
    ("S", (60, 50)),
    ("S", (58, 50)),
    ("S", (56, 50)),
    ("S", (58, 52)),
    ("S", (54, 50)),
    ("N", (56, 42)),
    ("N", (54, 44)),
    ("N", (56, 44)),
    ("N", (52, 44)),
]


def run(label, skip_ny):
    print(f"\n===== {label} skip_ny={skip_ny} =====", flush=True)
    sess, data, ok = boot(skip_ny)
    if not ok:
        print("boot fail", flush=True)
        return None
    best = dump(data, "start")
    for who, tgt in CHAIN:
        if step_budget(data["frame"]) < 3:
            print("budout", flush=True)
            break
        data, st = step(sess, data, who, tgt)
        if st == "dead":
            print("DEAD", flush=True)
            break
        if st != "moved":
            continue
        cur = dump(data, f"after-{tgt}")
        if cur[0] < best[0] or (cur[0] == best[0] and cur[1] < best[1]):
            best = cur
        if (data.get("levels_completed") or 0) >= 3:
            print("PASS L3", flush=True)
            return cur
    print(f"BEST {label} d14={best[0]} d15={best[1]} bud={best[4]} ship free detail above", flush=True)
    return best


def main():
    a = run("with-Ny", skip_ny=False)
    b = run("skip-Ny", skip_ny=True)
    print("\n===== COMPARE =====", flush=True)
    print("with-Ny", a[:2] + (a[4],) if a else None, flush=True)
    print("skip-Ny", b[:2] + (b[4],) if b else None, flush=True)


if __name__ == "__main__":
    main()
