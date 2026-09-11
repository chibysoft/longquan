"""Ny46 → N4832 → S(52,42): measure d14/bud vs baseline S4842."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, lock_other_ship, manh
from tools.r11l_seated_clear import clear_l1, reset


def dump(data, label):
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    wps = [w["c"] for w in r11l.waypoints(data["frame"])]
    d14 = abs(me14["c"][0] - 55) + abs(me14["c"][1] - 53)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    # raw free: wps closer to 14 or within 30 of 14
    raw14 = []
    for c in wps:
        if manh(c, me14["c"]) <= 30 and manh(c, me14["c"]) <= manh(c, me15["c"]) + 4:
            raw14.append(c)
    print(
        f"{label} d14={d14} ship14={me14['c']} ship15={me15['c']} "
        f"free_lock={sorted(free)} raw14={sorted(raw14)} all={sorted(wps)} "
        f"bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14


def boot_ny46():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_ns52"]},
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
    data, _, _ = move_wp(sess, data, lag, (26, 44), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    src = (26, 44) if (26, 44) in free else max(free, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, src, (36, 44), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, north, (46, 36), fr15)
    dump(data, "NY46")
    return sess, data


def main():
    plans = [
        ("base-S4842", [("S", (48, 42))]),
        ("N4832-S4842", [("N", (48, 32)), ("S", (48, 42))]),
        ("N4832-S5242", [("N", (48, 32)), ("S", (52, 42))]),
        ("N4832-S5342", [("N", (48, 32)), ("S", (53, 42))]),
        ("S4842-N4832-S5242", [("S", (48, 42)), ("N", (48, 32)), ("S", (52, 42))]),
        ("S5242-only", [("S", (52, 42))]),
        ("N4832-S5242-N5036", [("N", (48, 32)), ("S", (52, 42)), ("N", (50, 36))]),
    ]
    for name, steps in plans:
        print(f"\n===== {name} =====", flush=True)
        sess, data = boot_ny46()
        d0 = dump(data, "start")
        ok = True
        for who, tgt in steps:
            fr15 = lock_other_ship(data["frame"], 14)
            # Prefer raw selection by y
            me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
            wps = [w["c"] for w in r11l.waypoints(data["frame"])]
            cand = [
                c
                for c in wps
                if manh(c, me14["c"]) <= 30 and c not in fr15[:2]  # keep true 15 deep
            ]
            # better: pads not at known 15 homes
            cand = [c for c in wps if c not in ((42, 50), (58, 50), (58, 42))]
            cand = [c for c in cand if manh(c, me14["c"]) <= manh(c, me15["c"]) + 10]
            if len(cand) < 2:
                cand = [c for c in wps if manh(c, me14["c"]) <= 30]
            north = min(cand, key=lambda w: (w[1], w[0]))
            south = max(cand, key=lambda w: (w[1], w[0]))
            cur = north if who == "N" else south
            freeze = [c for c in wps if c != cur and (c in ((42, 50), (58, 50)) or manh(c, me15["c"]) + 8 < manh(c, me14["c"]))]
            # freeze the other of the pair
            other = south if cur == north else north
            freeze = list(set(freeze + [other] if other != cur else freeze))
            # Actually move_wp freeze = other ship's pads; pass lock_other_ship but force-include deep15
            freeze15 = list(lock_other_ship(data["frame"], 14))
            for p in ((42, 50), (58, 50)):
                if p in wps and p not in freeze15:
                    freeze15.append(p)
            # Remove cur from freeze if misclassified
            freeze15 = [p for p in freeze15 if p != cur]
            data, newc, st = move_wp(sess, data, cur, tgt, freeze15)
            print(f"  {who} {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}", flush=True)
            if st != "moved":
                ok = False
                break
            dump(data, f"after-{who}{tgt}")
        if ok:
            d1 = dump(data, "END")
            print(f"RESULT {name} d14 {d0}->{d1} bud={step_budget(data['frame'])}", flush=True)


if __name__ == "__main__":
    main()
