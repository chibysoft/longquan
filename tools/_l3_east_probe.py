"""Post-gate: dual-east along y=36 clearance (keep n=2)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_core import clearance_path
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


def refresh(data):
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    # Prefer y=36 band
    band = [w for w in free14 if 34 <= w[1] <= 38]
    if len(band) >= 2:
        free14 = band
    lead = max(free14, key=lambda w: (w[0], w[1]))
    lag = min(free14, key=lambda w: (w[0], w[1]))
    return freeze15, lead, lag, free14


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3east"]},
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

    # Clear 15 seal bubble off y36 east corridor
    data, _ = haul15_toward(sess, data, (34, 57), max_step=8, label="15e")
    print("after15", ships(data["frame"]), step_budget(data["frame"]))

    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    path = clearance_path(data["frame"], me["c"], (55, 53), step=1)
    print("path", path[::4][:10] if path else None)

    # Dual-east rounds: lead +4/+5, then lag catch same-row
    for rnd in range(6):
        if step_budget(data["frame"]) < 8:
            print("bud low")
            break
        freeze15, lead, lag, free14 = refresh(data)
        n = len(free14)
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(f"--- rnd{rnd} ship={me['c']} d14={d14} lead={lead} lag={lag} n={n} bud={step_budget(data['frame'])}")
        if n != 2:
            print("flock broke")
            break
        if me["c"][0] >= 48:
            print("east enough")
            break

        # lead east dx=4 or 5 (gate-proven)
        moved = False
        for dx in (5, 4, 3, 6):
            ld = (lead[0] + dx, lead[1])
            if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
                continue
            if near_any(ld, list(freeze15), cheb=5):
                print(f"  lead skip near15 {ld}")
                continue
            data, newc, st = move_wp(sess, data, lead, ld, freeze15)
            print(f"  lead {lead}->{ld} {st}->{newc}")
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD lead")
                return
            if st == "moved":
                moved = True
                break
        if not moved:
            print("lead stuck")
            break

        freeze15, lead, lag, free14 = refresh(data)
        if len(free14) != 2:
            print("n!=2 after lead", free14)
            break

        # lag east toward under-lead, same row; don't pass ship badly
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        for dx in (5, 4, 6, 3, 7, 8):
            gd = (lag[0] + dx, lag[1])
            # stay west of lead by cheb>=5
            if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
                continue
            if gd[0] >= lead[0]:
                continue
            if near_any(gd, list(freeze15), cheb=5):
                continue
            data, newc, st = move_wp(sess, data, lag, gd, freeze15)
            print(f"  lag {lag}->{gd} {st}->{newc} ship={ships(data['frame'])}")
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD lag")
                return
            if st == "moved":
                freeze15, lead, lag, free14 = refresh(data)
                print(f"  after lag n={len(free14)} free={free14}")
                break
        else:
            print("lag stuck")

    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    freeze15, lead, lag, free14 = refresh(data)
    print(f"END ship={me['c']} d14={abs(me['c'][0]-55)+abs(me['c'][1]-53)} free={free14} bud={step_budget(data['frame'])}")

    # If east enough, try south along x~55
    if me["c"][0] >= 40 and len(free14) == 2:
        print("--- south ---")
        for ld in (
            (lead[0], lead[1] + 4),
            (lead[0], lead[1] + 6),
            (lead[0] + 2, lead[1] + 4),
            (min(55, lead[0] + 4), lead[1] + 4),
            (55, 42),
            (55, 46),
            (55, 50),
        ):
            if step_budget(data["frame"]) < 6:
                break
            freeze15, lead, lag, free14 = refresh(data)
            if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
                continue
            if near_any(ld, list(freeze15), cheb=5):
                continue
            data, newc, st = move_wp(sess, data, lead, ld, freeze15)
            print(f"  S {lead}->{ld} {st}->{newc}")
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD S")
                return
            if st == "moved":
                print("HIT S", ships(data["frame"]))
                break


if __name__ == "__main__":
    main()
