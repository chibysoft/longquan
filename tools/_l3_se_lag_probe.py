"""After mid-east + SE to y42/44, brute-try lag destinations (budget-aware)."""
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
    lock_other_ship,
    near_any,
)
from tools.r11l_seated_clear import clear_l1, reset
from longquan.interactive import r11l


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3lag"]},
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
    data, ok = advance_14_mid_east(sess, data, lv0, do_clear15=False)
    print("gate", ok, ships(data["frame"]), "bud", step_budget(data["frame"]))

    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[0], w[1]))
    lag = min(free14, key=lambda w: (w[0], w[1]))

    data, _, st = move_wp(sess, data, lead, (lead[0] + 2, lead[1] + 6), freeze15)
    print("SE-lead", st, step_budget(data["frame"]))
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lag[1] + 6), freeze15)
    print("SE-lag", st, step_budget(data["frame"]))
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lead, (lead[0] - 3, lead[1] + 2), freeze15)
    print("SE2", st, ships(data["frame"]), step_budget(data["frame"]))

    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 42]
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    print(
        f"PROBE ship={me['c']} lead={lead} lag={lag} freeze15={freeze15} "
        f"wps={[w['c'] for w in r11l.waypoints(data['frame'])]} bud={step_budget(data['frame'])}"
    )

    # Prioritized lag targets: east-first same-row, then SE, then south, then under-lead.
    cands = []
    for dx, dy in (
        (4, 0), (5, 0), (6, 0), (3, 0), (2, 0), (8, 0),
        (4, 1), (5, 1), (3, 1), (4, 2), (5, 2), (2, 2), (6, 2),
        (0, 1), (0, 2), (1, 2), (-2, 2), (-4, 2),
        (3, 2), (2, 1), (-2, 0), (-4, 0),
        (lead[0] - lag[0] - 6, lead[1] - lag[1]),
        (lead[0] - lag[0] - 5, lead[1] - lag[1]),
        (lead[0] - lag[0] - 7, lead[1] - lag[1]),
    ):
        cands.append((lag[0] + dx, lag[1] + dy))
    cands = list(dict.fromkeys(cands))

    hits = []
    for gd in cands:
        if step_budget(data["frame"]) < 6:
            print("bud low")
            break
        if not (0 <= gd[0] < 64 and 0 <= gd[1] < 64):
            continue
        if gd == lag:
            continue
        cheb_lead = max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1]))
        if cheb_lead < 5:
            continue
        if near_any(gd, list(freeze15), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, lag, gd, freeze15)
        print(
            f"  try {lag}->{gd} chebL={cheb_lead} {st}->{newc} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD at", gd)
            return
        if st == "moved":
            hits.append(gd)
            freeze15 = lock_other_ship(data["frame"], 14)
            free14 = count_free14(data["frame"], freeze15)
            me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            print(f"  HIT ship={me['c']} free={free14}")
            band = [w for w in free14 if w[0] <= 42]
            if len(band) >= 2:
                lag = min(band, key=lambda w: (w[1], w[0]))
                lead = max(band, key=lambda w: (w[1], w[0]))
            if len(hits) >= 4:
                break
    print("hits", hits)


if __name__ == "__main__":
    main()
