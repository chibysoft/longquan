"""Push chrome15 to goal first after deep15, then SE 14 — or micro-walk from S6048."""
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
    clear15_corridor,
    count_free14,
    goals_by_chrome,
    haul15_toward,
    lock_other_ship,
    near_any,
)
from tools.r11l_seated_clear import clear_l1, reset
from tools._l3_s6048_probe import deep15


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


GOAL14, GOAL15 = (55, 53), (34, 57)


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
    d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
    print(
        f"{label} ship14={me14['c']} d14={d14} free={sorted(free)} "
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} "
        f"bud={step_budget(data['frame'])} lv={data.get('levels_completed')}",
        flush=True,
    )
    return d14, d15, free, fr15


def to_gate(_sess=None):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_15first"]},
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
    data, ok = deep15(sess, data)
    print(f"  deep15 ok={ok} bud={step_budget(data['frame'])}", flush=True)
    return sess, data, ok


def move14(sess, data, who, tgt):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return data, "nfree"
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    cur = south if who == "S" else north
    other = north if who == "S" else south
    if cheb(tgt, other) < 5:
        return data, "merge"
    if near_any(tgt, list(fr15), cheb=5):
        return data, "near15"
    data, newc, st = move_wp(sess, data, cur, tgt, fr15)
    print(f"  {who} {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}", flush=True)
    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, "dead"
    return data, st


def seny_to_s6048(sess, data):
    for who, tgt in [
        ("L", (36, 44)),
        ("N", (48, 32)),
        ("S", (60, 44)),
        ("N", (60, 38)),
        ("S", (60, 48)),
    ]:
        # L = lag = min x
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) < 2:
            return data, False
        if who == "L":
            cur = min(free, key=lambda w: w[0])
            other = max(free, key=lambda w: w[0])
            if cheb(tgt, other) < 5 or near_any(tgt, list(fr15), cheb=5):
                return data, False
            data, newc, st = move_wp(sess, data, cur, tgt, fr15)
            print(f"  L {cur}->{tgt} {st} bud={step_budget(data['frame'])}", flush=True)
            if st != "moved":
                return data, False
        else:
            data, st = move14(sess, data, who, tgt)
            if st != "moved":
                return data, False
    return data, True


def main():
    hits = []

    # A: haul15 hard after deep, then classic SE + micro
    print("\n===== 15FIRST-then-SE =====", flush=True)
    sess, data, ok = to_gate(None)
    if not ok:
        print("boot fail", flush=True)
    else:
        gmap = {14: GOAL14, 15: GOAL15}
        dump(data, "deep")
        for i in range(4):
            if step_budget(data["frame"]) < 8:
                break
            data, ok15 = haul15_toward(sess, data, gmap[15], max_step=6, label=f"15h{i}")
            dump(data, f"haul{i}")
            if data.get("state") == "GAME_OVER" or "frame" not in data:
                print("GO", flush=True)
                break
            me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
            d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
            if d15 <= 6:
                break
        if "frame" in data and data.get("state") != "GAME_OVER":
            d0, _, _, _ = dump(data, "pre-se")
            data, ok = seny_to_s6048(sess, data)
            if ok:
                d1, d15, free, _ = dump(data, "S6048")
                # micro continues
                for who, tgt in [
                    ("S", (60, 50)),
                    ("S", (58, 52)),
                    ("S", (56, 52)),
                    ("S", (55, 53)),
                    ("N", (56, 42)),
                    ("N", (55, 44)),
                ]:
                    if step_budget(data["frame"]) < 3:
                        break
                    data, st = move14(sess, data, who, tgt)
                    if st == "dead":
                        print("DEAD", flush=True)
                        break
                    if st != "moved":
                        print(f"SOFT {st}", flush=True)
                        continue
                    dump(data, f"after-{tgt}")
                if "frame" in data:
                    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
                    d2 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
                    tag = "IMPROVED" if d2 < d1 else ("FLAT" if d2 == d1 else "WORSE")
                    beat = " BEAT25" if d2 < 25 else ""
                    print(f"RESULT {tag}{beat} 15first d14 {d1}->{d2} bud={step_budget(data['frame'])}", flush=True)
                    hits.append((tag, "15first", d1, d2, step_budget(data["frame"])))
            else:
                print("seny fail", flush=True)

    # B: classic S6048 then micro without vacE (near15 filter will skip)
    print("\n===== MICRO-from-S6048 =====", flush=True)
    sess, data, ok = to_gate(None)
    if ok:
        data, ok = seny_to_s6048(sess, data)
        if ok:
            d0, _, _, fr15 = dump(data, "S6048")
            # vacE then micro
            free = count_free14(data["frame"], fr15)
            north = min(free, key=lambda w: (w[1], w[0]))
            south = max(free, key=lambda w: (w[1], w[0]))
            east = next((c for c in fr15 if c in ((58, 54), (58, 50))), max(fr15, key=lambda w: w[1]))
            data, newc, st = move_wp(sess, data, east, (48, 58), [north, south])
            print(f"  vacE48 {east}->(48,58) {st} bud={step_budget(data['frame'])}", flush=True)
            if st == "moved":
                dump(data, "vacE")
                for who, tgt in [
                    ("S", (60, 50)),
                    ("S", (60, 52)),
                    ("S", (58, 52)),
                    ("S", (56, 52)),
                    ("S", (55, 53)),
                    ("S", (52, 52)),
                    ("S", (50, 52)),
                    ("N", (58, 40)),
                    ("N", (56, 42)),
                    ("N", (55, 44)),
                    ("N", (52, 44)),
                ]:
                    if step_budget(data["frame"]) < 3:
                        print("budout", flush=True)
                        break
                    data, st = move14(sess, data, who, tgt)
                    if st == "dead":
                        print("DEAD", flush=True)
                        break
                    if st != "moved":
                        print(f"skip {who}{tgt} {st}", flush=True)
                        continue
                    d1, _, _, _ = dump(data, f"hit-{tgt}")
                    if d1 < d0:
                        print(f"IMPROVED {d0}->{d1}", flush=True)
                        hits.append(("IMPROVED", f"micro{tgt}", d0, d1, step_budget(data["frame"])))
                        d0 = d1

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
