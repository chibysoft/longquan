"""After mid-east: park15 deeper south BEFORE frog-ny."""
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
    advance_14_frog_ny_stack,
    clear15_corridor,
    count_free14,
    haul15_toward,
    lock_other_ship,
    near_any,
)
from tools.r11l_seated_clear import clear_l1, reset


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me['c']} d14={d14} free14={sorted(free)} "
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}"
    )


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l315park"]},
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
    dump(data, "GATE")

    # Aggressive 15 park toward (34,57) / clear seal from y36-44
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    west15 = min(fr15, key=lambda w: w[0])
    east15 = max(fr15, key=lambda w: w[0])
    for tgt in (
        (48, 50),
        (45, 52),
        (50, 48),
        (42, 50),
        (48, 46),
        (50, 44),
        (west15[0] + 4, min(56, west15[1] + 8)),
        (west15[0] + 6, min(56, west15[1] + 6)),
        (34, 52),
        (36, 54),
    ):
        if near_any(tgt, list(freeze14), cheb=5):
            print(f"  skip near14 {tgt}")
            continue
        if max(abs(tgt[0] - east15[0]), abs(tgt[1] - east15[1])) < 5:
            print(f"  skip merge15 {tgt}")
            continue
        data, newc, st = move_wp(sess, data, west15, tgt, freeze14)
        print(f"  15park {west15}->{tgt} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("15 DEAD")
            return
        if st == "moved":
            dump(data, "15OK")
            break
    else:
        for _ in range(3):
            data, ok = haul15_toward(sess, data, (34, 57), max_step=8, label="15agg")
            dump(data, "15agg")
            if not ok:
                break

    data, ok = advance_14_frog_ny_stack(sess, data, (34, 57))
    dump(data, "AFTER")
    print("stack_ok", ok)
    # Can we place S at (44,44) or N at (48,36)?
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) == 2:
        s = max(free, key=lambda w: (w[1], w[0]))
        n = min(free, key=lambda w: (w[1], w[0]))
        for cur, ld in ((s, (44, 44)), (s, (48, 44)), (n, (48, 36)), (n, (44, 36)), (n, (43, 42))):
            other = s if cur == n else n
            cheb = max(abs(ld[0] - other[0]), abs(ld[1] - other[1]))
            near = near_any(ld, list(fr15), cheb=5)
            print(f"  test {ld} cheb={cheb} near15={near}")
            if cheb < 5 or near or ld[1] <= 36 and ld[0] >= 45:
                continue
            data, newc, st = move_wp(sess, data, cur, ld, fr15)
            print(f"  {cur}->{ld} {st}")
            if st == "dead":
                print("DEAD")
                return
            if st == "moved":
                dump(data, "HIT")
                return


if __name__ == "__main__":
    main()
