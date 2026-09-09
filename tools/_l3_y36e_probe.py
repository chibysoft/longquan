"""Post mid-east: stay y36 stagger-east (avoid south frog)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, haul15_toward, lock_other_ship, near_any
from tools.r11l_seated_clear import clear_l1, reset


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(
        f"{label} ship={me['c']} d14={d14} free={sorted(free)} n={len(free)} "
        f"bud={step_budget(data['frame'])}"
    )
    return fr15, free, me


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3y36e"]},
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
    fr15, free, me = dump(data, "GATE")
    # soft 15 only
    data, _ = haul15_toward(sess, data, (34, 57), max_step=4, label="15soft")
    fr15, free, me = dump(data, "AFTER15")
    if len(free) != 2:
        print("not 2wp")
        return

    known_dead = {(37, 40), (40, 44), (34, 46), (31, 44), (34, 44), (36, 48)}

    for rnd in range(12):
        if step_budget(data["frame"]) < 6:
            print("bud low")
            break
        fr15, free, me = dump(data, f"r{rnd}")
        if len(free) != 2:
            print("broke", free)
            break
        lead = max(free, key=lambda w: (w[0], -w[1]))
        lag = min(free, key=lambda w: (w[0], -w[1]))
        # Prefer: lag south-stagger first OR lead small east while lag stays back
        plans = [
            # lag drop south 2-4 then lead east (stagger without full align)
            ("lag", lag, (lag[0], lag[1] + 2)),
            ("lag", lag, (lag[0], lag[1] + 4)),
            ("lag", lag, (lag[0] + 2, lag[1] + 4)),
            ("lag", lag, (lag[0] - 2, lag[1] + 2)),
            # lead east small on same row
            ("lead", lead, (lead[0] + 2, lead[1])),
            ("lead", lead, (lead[0] + 3, lead[1])),
            ("lead", lead, (lead[0] + 4, lead[1])),
            ("lead", lead, (lead[0] + 5, lead[1])),
            # lead SE mild
            ("lead", lead, (lead[0] + 2, lead[1] + 2)),
            ("lead", lead, (lead[0] + 4, lead[1] + 2)),
            # lag east stay south of lead
            ("lag", lag, (lag[0] + 4, lag[1])),
            ("lag", lag, (lag[0] + 5, lag[1])),
            ("lag", lag, (lag[0] + 3, lag[1])),
        ]
        moved = False
        for who, cur, ld in plans:
            other = lead if who == "lag" else lag
            if ld in known_dead:
                continue
            if cheb(ld, other) < 5:
                continue
            if near_any(ld, list(fr15), cheb=5):
                continue
            # avoid y<=32 east GO
            if ld[1] <= 32 and ld[0] > cur[0]:
                continue
            data, newc, st = move_wp(sess, data, cur, ld, fr15)
            print(f"  {who} {cur}->{ld} {st}->{newc} cheb={cheb(ld, other)}")
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD", ld)
                return
            if st == "moved":
                n = len(count_free14(data["frame"], lock_other_ship(data["frame"], 14)))
                dump(data, "HIT")
                if n != 2:
                    print("FLOCK n=", n)
                    return
                moved = True
                break
        if not moved:
            print("stalled")
            break
    dump(data, "END")


if __name__ == "__main__":
    main()
