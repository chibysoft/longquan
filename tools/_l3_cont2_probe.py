"""Tight cont from se-ny: only cheb-legal targets; prefer S-first then N."""
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
        f"{label} ship={me['c']} d14={d14} free={sorted(free)} n={len(free)} "
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
        json={"tags": ["r11l_cont2"]},
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
    dump(data, "END")
    return sess, data, True


# Only targets with cheb>=5 from the OTHER pad
CANDS = [
    # south first — open space for north later
    ("S", (54, 46)),
    ("S", (56, 44)),
    ("S", (56, 46)),
    ("S", (54, 48)),
    ("S", (52, 50)),
    ("S", (50, 50)),
    ("S", (48, 50)),
    ("S", (46, 48)),
    ("S", (44, 48)),
    ("S", (56, 42)),
    ("S", (54, 42)),
    ("S", (55, 47)),
    ("S", (53, 49)),
    ("S", (51, 51)),
    ("S", (49, 52)),
    # north — far enough from (48,42)
    ("N", (54, 38)),
    ("N", (56, 36)),
    ("N", (56, 38)),
    ("N", (55, 36)),
    ("N", (54, 36)),
    ("N", (58, 36)),
    ("N", (54, 40)),
    ("N", (56, 40)),
    ("N", (52, 34)),
    ("N", (50, 34)),
    ("N", (48, 32)),
    ("N", (46, 32)),
    ("N", (44, 34)),
    ("N", (42, 34)),
    ("N", (42, 38)),
]


def main():
    hits = []
    for who, tgt in CANDS:
        print(f"\n===== {who}->{tgt} =====", flush=True)
        sess, data, ok = boot()
        if not ok:
            print("boot fail", flush=True)
            continue
        d0, free, fr15 = dump(data, "base")
        if len(free) != 2:
            continue
        north = min(free, key=lambda w: (w[1], w[0]))
        south = max(free, key=lambda w: (w[1], w[0]))
        cur = north if who == "N" else south
        other = south if who == "N" else north
        if cheb(tgt, other) < 5:
            print(f"skip merge cheb={cheb(tgt, other)}", flush=True)
            continue
        if near_any(tgt, list(fr15), cheb=5):
            print("skip near15", flush=True)
            continue
        data, newc, st = move_wp(sess, data, cur, tgt, fr15)
        print(f"  {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", flush=True)
            continue
        if st != "moved":
            continue
        d1, free1, fr151 = dump(data, "after")
        if len(free1) != 2:
            print(f"FLOCK n={len(free1)}", flush=True)
            continue
        if d1 < d0:
            print(f"IMPROVED {d0}->{d1} bud={step_budget(data['frame'])}", flush=True)
            hits.append((who, tgt, d0, d1, step_budget(data["frame"]), free1))
            # try follow-up from other pad
            n2 = min(free1, key=lambda w: (w[1], w[0]))
            s2 = max(free1, key=lambda w: (w[1], w[0]))
            follow = [(n2, (n2[0] + 4, n2[1])), (n2, (n2[0] + 6, n2[1] + 2)), (s2, (s2[0] + 4, s2[1] + 2))]
            for src, t2 in follow:
                oth = s2 if src == n2 else n2
                if cheb(t2, oth) < 5 or near_any(t2, list(fr151), cheb=5):
                    continue
                if step_budget(data["frame"]) < 4:
                    break
                data, _, st2 = move_wp(sess, data, src, t2, fr151)
                print(f"  hop2 {src}->{t2} {st2}", flush=True)
                if st2 == "moved" and "frame" in data:
                    d2, free2, _ = dump(data, "hop2")
                    if len(free2) == 2 and d2 < d1:
                        print(f"HOP2 {d1}->{d2}", flush=True)
                        hits.append(("H2", t2, d1, d2, step_budget(data["frame"]), free2))
                    break
                if st2 == "dead":
                    break
        elif d1 == d0:
            print(f"FLAT bud={step_budget(data['frame'])}", flush=True)
        else:
            print("WORSE", flush=True)

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    if not hits:
        print("none", flush=True)


if __name__ == "__main__":
    main()
