"""Continue from (28,44)/(18,44) west-south deeper."""
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


def refresh(data):
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 42]
    if len(free14) < 2:
        free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[0], w[1]))  # eastern of pair as lead
    lag = min(free14, key=lambda w: (w[0], w[1]))
    return freeze15, lead, lag


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3ww3"]},
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
    freeze15, lead, lag = refresh(data)
    data, _, _ = move_wp(sess, data, lead, (36, 42), freeze15)
    freeze15, lead, lag = refresh(data)
    data, _, _ = move_wp(sess, data, lag, (25, 42), freeze15)
    freeze15, lead, lag = refresh(data)
    data, _, _ = move_wp(sess, data, lead, (33, 44), freeze15)
    freeze15, lead, lag = refresh(data)
    for gd in ((22, 43), (18, 44)):
        freeze15, lead, lag = refresh(data)
        data, _, st = move_wp(sess, data, lag, gd, freeze15)
        print("G", lag, gd, st)
    freeze15, lead, lag = refresh(data)
    data, _, st = move_wp(sess, data, lead, (28, 44), freeze15)
    print("L28", st, ships(data["frame"]), "bud", step_budget(data["frame"]))
    freeze15, lead, lag = refresh(data)
    print(f"READY lead={lead} lag={lag} bud={step_budget(data['frame'])}")

    # Dual south / west-south ladder
    steps = [
        ("lead", (28, 46)),
        ("lag", (18, 46)),
        ("lead", (26, 48)),
        ("lag", (18, 48)),
        ("lead", (24, 50)),
        ("lag", (18, 50)),
        ("lead", (28, 48)),
        ("lag", (20, 48)),
        ("lead", (24, 46)),
        ("lag", (16, 46)),
        ("lead", (22, 48)),
        ("lag", (16, 48)),
        ("lead", (20, 50)),
        ("lag", (14, 50)),
        ("lead", (26, 44)),
        ("lag", (16, 44)),
        ("lead", (30, 46)),
        ("lag", (20, 46)),
    ]
    for who, dest in steps:
        if step_budget(data["frame"]) < 5:
            print("bud low")
            break
        freeze15, lead, lag = refresh(data)
        wp = lead if who == "lead" else lag
        other = lag if who == "lead" else lead
        if max(abs(dest[0] - other[0]), abs(dest[1] - other[1])) < 5:
            print("skip", who, dest)
            continue
        if near_any(dest, list(freeze15), cheb=5):
            print("near15", dest)
            continue
        data, newc, st = move_wp(sess, data, wp, dest, freeze15)
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"] if "frame" in data else "?"
        print(f"  {who} {wp}->{dest} {st}->{newc} ship={me} bud={step_budget(data['frame']) if 'frame' in data else '?'}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", dest)
            return
        if st == "moved":
            print("  free", count_free14(data["frame"], lock_other_ship(data["frame"], 14)))


if __name__ == "__main__":
    main()
