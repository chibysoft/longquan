"""Continue west-south from first SE (32,42)+(25,42)."""
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


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3ws2"]},
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
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    lead = max(free14, key=lambda w: (w[0], w[1]))
    lag = min(free14, key=lambda w: (w[0], w[1]))
    data, _, st = move_wp(sess, data, lead, (32, 42), freeze15)
    print("SE1", st, ships(data["frame"]))
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    print("free after SE1", free14)
    # pick deepest as lead, shallowest as lag among band
    band = [w for w in free14 if w[1] >= 36]
    lead = max(band or free14, key=lambda w: (w[1], w[0]))
    lag = min(band or free14, key=lambda w: (w[1], w[0]))
    # if lag still on y36, pull south
    if lag[1] < 42:
        for gd in ((lag[0] + 2, 42), (25, 42), (lag[0] + 4, 42)):
            if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
                continue
            data, _, st = move_wp(sess, data, lag, gd, freeze15)
            print("lagS", lag, "->", gd, st)
            if st == "moved":
                break
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD lag")
                return
    freeze15 = lock_other_ship(data["frame"], 14)
    free14 = count_free14(data["frame"], freeze15)
    band = sorted([w for w in free14 if w[0] <= 40], key=lambda w: (w[1], w[0]))
    print(f"READY free={free14} band={band} ship={ships(data['frame'])} bud={step_budget(data['frame'])}")
    lead = max(band, key=lambda w: (w[1], w[0]))
    lag = min(band, key=lambda w: (w[1], w[0]))

    for ld in (
        (30, 44), (28, 44), (26, 44), (32, 44), (24, 44),
        (30, 46), (28, 46), (26, 46), (24, 46), (22, 46),
        (28, 48), (26, 48), (24, 48), (22, 48), (20, 48),
        (30, 48), (32, 48), (18, 46), (20, 44),
        (28, 42), (26, 42), (24, 42),  # west same row
    ):
        if step_budget(data["frame"]) < 5:
            break
        freeze15 = lock_other_ship(data["frame"], 14)
        free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 40]
        if len(free14) < 2:
            free14 = count_free14(data["frame"], freeze15)
        lead = max(free14, key=lambda w: (w[1], w[0]))
        lag = min(free14, key=lambda w: (w[1], w[0]))
        if ld == lead:
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
            print("HIT", ships(data["frame"]), count_free14(data["frame"], lock_other_ship(data["frame"], 14)))
            # catch lag
            freeze15 = lock_other_ship(data["frame"], 14)
            free14 = [w for w in count_free14(data["frame"], freeze15) if w[0] <= 40]
            lead = max(free14, key=lambda w: (w[1], w[0]))
            lag = min(free14, key=lambda w: (w[1], w[0]))
            for gd in (
                (lag[0] + 2, lead[1]),
                (lag[0] + 4, lag[1]),
                (lag[0], lead[1]),
                (lead[0] - 5, lead[1]),
                (lag[0] - 2, lead[1]),
            ):
                if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
                    continue
                if near_any(gd, [lead] + list(freeze15), cheb=5):
                    continue
                data, newc, st = move_wp(sess, data, lag, gd, freeze15)
                print(f"  G {lag}->{gd} {st}->{newc}")
                if st == "moved":
                    print("LAG HIT", ships(data["frame"]))
                    break
                if st == "dead" or data.get("state") == "GAME_OVER":
                    print("DEAD lag")
                    return
            # continue searching deeper from new lead — don't return


if __name__ == "__main__":
    main()
