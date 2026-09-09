"""Skip gate +5 translate: from collapse 2wp, unseal, multi +2 dual-east."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_core import clearance_path
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import (
    advance_14_mid_east,
    collapse_to_2,
    ensure_y34,
    translate2_nudge,
    west_to_neck,
    _install_reshape_cap3,
)
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, lock_other_ship, near_any
from tools.r11l_seated_clear import clear_l1, reset


def dump(data, label):
    wps = [w["c"] for w in r11l.waypoints(data["frame"])]
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(
        f"{label} ship={me['c']} d14={d14} wps={wps} free={free} "
        f"freeze15={fr15} bud={step_budget(data['frame'])}"
    )
    return fr15, free, me


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3multi"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    lv0 = data.get("levels_completed") or 0
    _install_reshape_cap3()
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    freeze15 = lock_other_ship(data["frame"], 14)
    data, _ = west_to_neck(sess, data, freeze15, lv0)
    freeze15 = lock_other_ship(data["frame"], 14)
    data, _ = collapse_to_2(sess, data, freeze15)
    fr15, free, me = dump(data, "COLLAPSE")  # expect (19,36)/(29,36) ship~(24,36)

    # Unseal (41,40) — try SE destinations that worked before for clear15
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = lock_other_ship(data["frame"], 14)
    seal = min(fr15, key=lambda w: w[0]) if fr15 else None
    if seal:
        for dest in ((45, 40), (44, 40), (42, 41), (46, 42), (48, 38), (50, 42)):
            if near_any(dest, freeze14, cheb=5):
                continue
            data, newc, st = move_wp(sess, data, seal, dest, freeze14)
            print(f"  seal {seal}->{dest} {st}->{newc}")
            if st == "moved":
                break
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD seal")
                return

    fr15, free, me = dump(data, "UNSEAL")

    # Multiple tiny dual-east from pre-gate formation
    for rnd in range(8):
        if step_budget(data["frame"]) < 10:
            print("bud low")
            break
        fr15, free, me = dump(data, f"rnd{rnd}")
        if len(free) != 2:
            print("flock break")
            break
        if me["c"][0] >= 48:
            print("far enough")
            break
        # Prefer dx=2 always to keep gap small
        data, ok = translate2_nudge(sess, data, fr15, lead_dx=2)
        if data.get("state") == "GAME_OVER":
            print("GO")
            return
        if not ok:
            print("nudge fail — try dx=1 lead only then lag")
            fr15, free, me = dump(data, "failstate")
            if len(free) != 2:
                break
            lead = max(free, key=lambda w: w[0])
            lag = min(free, key=lambda w: w[0])
            ld = (lead[0] + 2, lead[1])
            if near_any(ld, list(fr15), cheb=5):
                print("blocked by 15", ld, fr15)
                # need more 15 clear
                freeze14 = lock_other_ship(data["frame"], 15)
                fr15b = lock_other_ship(data["frame"], 14)
                if fr15b:
                    wp = min(fr15b, key=lambda w: w[0])
                    data, _, st = move_wp(sess, data, wp, (wp[0] + 6, wp[1]), freeze14)
                    print(f"  re-clear {wp} {st}")
                continue
            data, newc, st = move_wp(sess, data, lead, ld, fr15)
            print(f"  manual lead {lead}->{ld} {st}")
            if st != "moved":
                break
            fr15, free, me = dump(data, "after-manual-lead")
            if len(free) != 2:
                print("manual broke flock")
                break
            lag = min(free, key=lambda w: w[0])
            lead = max(free, key=lambda w: w[0])
            gd = (min(lead[0] - 5, lag[0] + 3), lag[1])
            data, newc, st = move_wp(sess, data, lag, gd, fr15)
            print(f"  manual lag {lag}->{gd} {st}")
            fr15, free, me = dump(data, "after-manual-lag")
            if not st == "moved":
                break

    fr15, free, me = dump(data, "END")
    path = clearance_path(data["frame"], me["c"], (55, 53), step=1)
    print("path_len", len(path) if path else 0, "tail", path[-5:] if path else None)


if __name__ == "__main__":
    main()
