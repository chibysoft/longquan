"""Probe alternate SE paths: soft south, west-south corridor."""
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


def gate():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3ws"]},
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
    return sess, data


def refresh(data):
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 42]
    if len(free14) < 2:
        free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[1], w[0]))
    lag = min(free14, key=lambda w: (w[1], w[0]))
    return freeze15, lead, lag


def main():
    sess, data = gate()
    freeze15, lead, lag = refresh(data)
    print(f"GATE lead={lead} lag={lag} bud={step_budget(data['frame'])}")

    # Soft south ladder instead of +6
    plan = [
        ("lead", (0, 2)),
        ("lag", (2, 2)),
        ("lead", (0, 2)),
        ("lag", (2, 2)),
        ("lead", (-2, 2)),
        ("lag", (2, 1)),
        ("lead", (-2, 2)),
        ("lag", (-2, 2)),
        ("lead", (-2, 2)),
        ("lag", (0, 2)),
        ("lead", (2, 2)),
        ("lag", (2, 2)),
    ]
    for who, (dx, dy) in plan:
        if step_budget(data["frame"]) < 6:
            print("bud low")
            break
        freeze15, lead, lag = refresh(data)
        wp = lead if who == "lead" else lag
        other = lag if who == "lead" else lead
        dest = (wp[0] + dx, wp[1] + dy)
        if max(abs(dest[0] - other[0]), abs(dest[1] - other[1])) < 5:
            print(f"skip {who} {wp}->{dest} cheb")
            continue
        if near_any(dest, list(freeze15), cheb=5):
            print(f"skip {who} {wp}->{dest} near15")
            continue
        data, newc, st = move_wp(sess, data, wp, dest, freeze15)
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"] if "frame" in data else "?"
        print(
            f"  {who} {wp}->{dest} {st}->{newc} ship={me} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD")
            return
    freeze15, lead, lag = refresh(data)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    print(f"END ship={me['c']} lead={lead} lag={lag} bud={step_budget(data['frame'])}")


if __name__ == "__main__":
    main()
