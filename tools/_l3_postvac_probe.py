"""After S6248 + vacE(52,58): scan S/N targets that improve d14 without GO."""
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
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me14["c"][0] - 55) + abs(me14["c"][1] - 53)
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me14['c']} d14={d14} free={sorted(free)} "
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} "
        f"bud={step_budget(data['frame'])} lv={data.get('levels_completed')}",
        flush=True,
    )
    return d14, d15, free, fr15


def boot():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_postvac"]},
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
    gmap = {s["chrome"]: None for s in ships(data["frame"])}
    # goal15 unused in frog path deep; pass dummy
    from tools.r11l_l3_sync_probe import goals_by_chrome

    gmap = goals_by_chrome(data["frame"])
    data, ok = advance_14_frog_ny_stack(sess, data, gmap.get(15, (34, 57)))
    if not ok:
        print("seny fail", flush=True)
        return sess, data, False
    dump(data, "after-seny")
    # vacE
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    flock = [c for c in fr15 if c not in (north, south)] or list(fr15)
    east15 = next((c for c in flock if c in ((58, 54), (58, 50))), max(flock, key=lambda w: w[1]))
    data, newc, st = move_wp(sess, data, east15, (52, 58), [north, south])
    print(f"  vacE {east15}->(52,58) {st}->{newc} bud={step_budget(data['frame'])}", flush=True)
    if st != "moved":
        return sess, data, False
    dump(data, "after-vacE")
    return sess, data, True


# Targets to try from S=(61,48) / N=(60,38) after vacE.
S_TGTS = [
    (56, 52),
    (54, 52),
    (55, 53),
    (53, 53),
    (54, 54),
    (50, 52),
    (52, 54),
    (48, 52),
    (56, 50),
    (54, 50),
    (58, 52),
    (60, 52),
    (56, 48),
    (54, 48),
    (52, 50),
    (50, 50),
    (48, 50),
]
N_TGTS = [
    (56, 44),
    (54, 44),
    (52, 44),
    (55, 42),
    (54, 42),
    (56, 42),
    (58, 42),
    (52, 40),
    (54, 40),
    (56, 40),
]


def main():
    hits = []
    soft = []
    dead = []
    for who, tgts in (("S", S_TGTS), ("N", N_TGTS)):
        for tgt in tgts:
            print(f"\n===== {who}->{tgt} =====", flush=True)
            sess, data, ok = boot()
            if not ok:
                print("boot fail", flush=True)
                continue
            d0, _, free, fr15 = dump(data, "start")
            if len(free) < 2:
                print("nfree", len(free), flush=True)
                continue
            north = min(free, key=lambda w: (w[1], w[0]))
            south = max(free, key=lambda w: (w[1], w[0]))
            cur = south if who == "S" else north
            other = north if who == "S" else south
            if cheb(tgt, other) < 5:
                print("merge", flush=True)
                soft.append((who, tgt, "merge"))
                continue
            if near_any(tgt, list(fr15), cheb=5):
                print("near15", flush=True)
                soft.append((who, tgt, "near15"))
                continue
            if step_budget(data["frame"]) < 3:
                print("budout", flush=True)
                continue
            data, newc, st = move_wp(sess, data, cur, tgt, fr15)
            print(f"  {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}", flush=True)
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                dead.append((who, tgt))
                print("DEAD", flush=True)
                continue
            if st != "moved":
                soft.append((who, tgt, st))
                continue
            d1, d15, free2, _ = dump(data, "END")
            tag = "IMPROVED" if d1 < d0 else ("FLAT" if d1 == d0 else "WORSE")
            print(f"RESULT {tag} d14 {d0}->{d1} d15={d15} free={sorted(free2)}", flush=True)
            hits.append((who, tgt, tag, d0, d1, d15, step_budget(data["frame"])))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    print("soft", soft, flush=True)
    print("dead", dead, flush=True)


if __name__ == "__main__":
    main()
