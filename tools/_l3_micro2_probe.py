"""Deep15+STACK: exhaustive micro from (40,36)+(40,44) — reboot per dest."""
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

BAD = {(42, 42), (44, 36), (45, 36), (46, 36), (48, 36), (40, 50)}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def to_stack(sess, data):
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    east15 = max(fr15, key=lambda w: w[0])
    west15 = min(fr15, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, east15, (58, 42), freeze14)
    if st == "dead":
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    west15 = min(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
    data, _, st = move_wp(sess, data, west15, (48, 42), freeze14)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (40, 36), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, s, (40, 44), fr15)
    return data, st == "moved"


def boot():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3micro2"]},
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
    data, ok = to_stack(sess, data)
    return sess, data, ok


def main():
    ordered = [
        ("N", 43, 36),
        ("N", 42, 36),
        ("N", 41, 36),
        ("N", 43, 38),
        ("N", 42, 38),
        ("N", 41, 38),
        ("N", 43, 40),
        ("N", 42, 40),
        ("N", 41, 40),
        ("S", 42, 44),
        ("S", 43, 44),
        ("S", 41, 44),
        ("S", 42, 46),
        ("S", 44, 46),
        ("S", 40, 46),
        ("S", 43, 46),
        ("N", 44, 38),
        ("N", 44, 40),
        ("S", 45, 44),
        ("S", 38, 44),
        ("S", 36, 44),
        ("N", 38, 36),
        ("N", 45, 40),
        ("S", 40, 48),
        ("N", 40, 40),
        ("N", 40, 42),
    ]

    hits = []
    for who, x, y in ordered:
        ld = (x, y)
        if ld in BAD:
            continue
        if who == "N" and y <= 36 and x >= 45:
            continue
        print(f"=== {who} {ld} ===")
        sess, data, ok = boot()
        if not ok:
            print("boot fail")
            continue
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        s = max(free, key=lambda w: (w[1], w[0]))
        n = min(free, key=lambda w: (w[1], w[0]))
        cur = n if who == "N" else s
        other = s if who == "N" else n
        if ld == cur:
            print("same")
            continue
        if cheb(ld, other) < 5:
            print("merge")
            continue
        if near_any(ld, list(fr15), cheb=5):
            print("near15")
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(f"  {cur}->{ld} {st}->{newc} ship={me['c']} d14={d14} bud={step_budget(data['frame'])}")
        if st == "dead":
            BAD.add(ld)
            print("DEAD")
            continue
        if st == "moved":
            free2 = count_free14(data["frame"], lock_other_ship(data["frame"], 14))
            print(f"HIT free={sorted(free2)}")
            hits.append((who, ld, me["c"], d14, sorted(free2)))
            # only return on d14 improvement or clear east progress
            if d14 < 36 or (who == "S" and ld[0] > 40) or (who == "N" and ld[1] > 36 and ld[0] >= 42):
                print("GOOD hit — stop")
                return
            # keep searching for better
    print("hits so far", hits)
    print("BAD", BAD)


if __name__ == "__main__":
    main()
