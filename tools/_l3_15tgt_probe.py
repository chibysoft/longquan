"""Safe 15 vacate targets from (41,40) at gate — one reboot each."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import clear15_corridor, lock_other_ship, near_any
from tools.r11l_seated_clear import clear_l1, reset

BAD = {(45, 52), (48, 46), (41, 48), (52, 44)}


def boot():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l315t"]},
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
    return sess, data


def main():
    tgts = [
        (48, 42),
        (50, 42),
        (46, 44),
        (48, 44),
        (50, 44),
        (44, 44),
        (46, 42),
        (48, 40),
        (50, 40),
        (42, 44),
        (44, 46),
        (46, 46),
        (50, 46),
        (52, 42),
        (45, 44),
        (45, 46),
    ]
    for tgt in tgts:
        if tgt in BAD:
            continue
        print(f"=== {tgt} ===")
        sess, data = boot()
        freeze14 = lock_other_ship(data["frame"], 15)
        fr15 = list(lock_other_ship(data["frame"], 14))
        west15 = min(fr15, key=lambda w: w[0])
        east15 = max(fr15, key=lambda w: w[0])
        if near_any(tgt, list(freeze14), cheb=5):
            print("near14")
            continue
        if max(abs(tgt[0] - east15[0]), abs(tgt[1] - east15[1])) < 5:
            print("merge")
            continue
        data, newc, st = move_wp(sess, data, west15, tgt, freeze14)
        me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
        print(f"  {west15}->{tgt} {st}->{newc} ship15={me15['c']} bud={step_budget(data['frame'])}")
        if st == "dead":
            BAD.add(tgt)
            print("DEAD")
            continue
        if st == "moved":
            print("HIT — check if (44,44) free for 14")
            fr15 = list(lock_other_ship(data["frame"], 14))
            for cell in ((44, 44), (48, 44), (48, 36), (43, 42)):
                print(f"  near15[{cell}]={near_any(cell, fr15, cheb=5)}")
            return
    print("done", "bad=", BAD)


if __name__ == "__main__":
    main()
