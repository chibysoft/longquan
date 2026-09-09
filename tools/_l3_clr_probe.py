"""Offline+live: clearance_path from mid-east to 14 goal; try those hops."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_core import clearance_path, ship_footprint_ok, _plane
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import (
    clear15_corridor,
    count_free14,
    haul15_toward,
    lock_other_ship,
    near_any,
)
from tools.r11l_seated_clear import clear_l1, reset


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3clr"]},
        timeout=60,
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

    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    g14 = (55, 53)
    path = clearance_path(data["frame"], me14["c"], g14, step=1)
    print(f"ship={me14['c']} path_len={len(path) if path else 0}")
    if path:
        # print coarse samples
        samples = path[:: max(1, len(path) // 12)]
        print("samples", samples[:14], "...", path[-1])
        g = _plane(data["frame"])
        print("goal_fp", ship_footprint_ok(g, *g14), "start_fp", ship_footprint_ok(g, *me14["c"]))

    # Push 15 east twice so freeze bubble leaves mid SE
    for i in range(2):
        data, ok = haul15_toward(sess, data, (34, 57), max_step=8, label=f"15e{i}")
        print("15", ok, ships(data["frame"]), step_budget(data["frame"]))
        if data.get("state") == "GAME_OVER":
            return

    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    path2 = clearance_path(data["frame"], me14["c"], g14, step=1)
    print(f"after15 path_len={len(path2) if path2 else 0}")
    if path2:
        print("samples2", path2[:: max(1, len(path2) // 10)][:12])

    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[0], w[1]))
    lag = min(free14, key=lambda w: (w[0], w[1]))
    print(f"lead={lead} lag={lag} freeze15={freeze15} bud={step_budget(data['frame'])}")

    # Candidate lead hops: along clearance path ahead of ship, cheb-sep from lag
    cands = []
    if path2 and len(path2) > 5:
        for hop in path2[4 : min(40, len(path2)) : 3]:
            # Aim lead near hop + offset east of lag
            cands.append((hop[0] + 2, hop[1]))
            cands.append((hop[0] + 4, hop[1]))
            cands.append((hop[0], hop[1] + 2))
            cands.append(hop)
    # Also explicit SE toward goal
    for dx, dy in (
        (2, 6), (4, 6), (4, 4), (6, 4), (6, 6), (8, 4), (8, 6),
        (2, 4), (4, 2), (6, 2), (0, 6), (8, 0),
        (-2, 6), (4, 8), (6, 8),
    ):
        cands.append((lead[0] + dx, lead[1] + dy))
    # Dedup
    seen = set()
    ordered = []
    for c in cands:
        if c not in seen:
            seen.add(c)
            ordered.append(c)

    hits = []
    for ld in ordered:
        if step_budget(data["frame"]) < 6:
            print("bud low", hits)
            break
        if not (0 <= ld[0] < 64 and 0 <= ld[1] < 64):
            continue
        if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
            continue
        if near_any(ld, list(freeze15), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, lead, ld, freeze15)
        print(f"  L {lead}->{ld} {st}->{newc} bud={step_budget(data['frame'])}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", ld)
            return
        if st == "moved":
            hits.append(ld)
            me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
            print(f"HIT ship={me['c']} d14={d14} free={count_free14(data['frame'], lock_other_ship(data['frame'], 14))}")
            freeze15 = lock_other_ship(data["frame"], 14)
            free14 = count_free14(data["frame"], freeze15)
            lead = max(free14, key=lambda w: (w[1], w[0]))
            lag = min(free14, key=lambda w: (w[1], w[0]))
            if len(hits) >= 3:
                break
    print("hits", hits)


if __name__ == "__main__":
    main()
