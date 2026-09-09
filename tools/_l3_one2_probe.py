"""Single-candidate boots from N438 — find any east/south HIT."""
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

BAD = {(42, 40), (42, 42), (42, 45), (42, 46), (44, 36), (45, 36), (48, 36), (43, 40), (43, 42)}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def boot_n438():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3one2"]},
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
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    if st == "dead":
        return sess, data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    west15 = min(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
    data, _, st = move_wp(sess, data, west15, (48, 42), freeze14)
    if st != "moved":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (40, 36), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, s, (40, 44), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (43, 38), fr15)
    return sess, data, st == "moved"


def main():
    cands = [
        ("S", 42, 44),
        ("S", 41, 44),
        ("S", 43, 44),
        ("S", 40, 45),
        ("S", 41, 45),
        ("S", 40, 46),
        ("S", 41, 46),
        ("S", 43, 46),
        ("S", 44, 46),
        ("S", 38, 44),
        ("S", 36, 44),
        ("N", 45, 40),
        ("N", 46, 38),
        ("N", 46, 40),
        ("N", 44, 39),
        ("N", 45, 39),
        ("N", 44, 38),
        ("N", 45, 38),
        ("N", 41, 38),
        ("N", 42, 38),
        ("N", 44, 40),
        ("S", 44, 44),
        ("S", 46, 44),
        ("S", 48, 44),
    ]
    for who, x, y in cands:
        ld = (x, y)
        if ld in BAD:
            continue
        print(f"=== {who} {ld} ===", flush=True)
        sess, data, ok = boot_n438()
        if not ok:
            print("bootfail", flush=True)
            continue
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        s = max(free, key=lambda w: (w[1], w[0]))
        n = min(free, key=lambda w: (w[1], w[0]))
        cur = n if who == "N" else s
        other = s if who == "N" else n
        if cheb(ld, other) < 5:
            print("merge", flush=True)
            continue
        if near_any(ld, list(fr15), cheb=5):
            print("near15", flush=True)
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(f"  {st}->{newc} ship={me['c']} d14={d14} bud={step_budget(data['frame'])}", flush=True)
        if st == "dead":
            BAD.add(ld)
            print("DEAD", flush=True)
            continue
        if st == "moved":
            free2 = sorted(count_free14(data["frame"], lock_other_ship(data["frame"], 14)))
            print(f"HIT free={free2}", flush=True)
            if d14 <= 36 and (ld[0] > 40 or ld[1] > 38):
                print("KEEP", flush=True)
                # continue a bit
                for i in range(4):
                    fr15 = lock_other_ship(data["frame"], 14)
                    free = count_free14(data["frame"], fr15)
                    if len(free) != 2 or step_budget(data["frame"]) < 4:
                        break
                    s = max(free, key=lambda w: (w[1], w[0]))
                    n = min(free, key=lambda w: (w[1], w[0]))
                    progressed = False
                    for cur2, ld2 in [
                        (s, (s[0] + 4, s[1])),
                        (s, (s[0] + 2, s[1])),
                        (n, (n[0] + 2, n[1])),
                        (n, (n[0], n[1] + 2)),
                        (s, (48, 44)),
                        (n, (46, 40)),
                    ]:
                        if ld2 in BAD:
                            continue
                        o2 = s if cur2 == n else n
                        if cheb(ld2, o2) < 5 or near_any(ld2, list(fr15), cheb=5):
                            continue
                        if ld2[1] <= 36 and ld2[0] >= 45:
                            continue
                        data, newc, st = move_wp(sess, data, cur2, ld2, fr15)
                        print(f"  cont {cur2}->{ld2} {st}", flush=True)
                        if st == "dead":
                            print("cont DEAD", flush=True)
                            return
                        if st == "moved":
                            me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
                            d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
                            print(f"  CONT ship={me['c']} d14={d14}", flush=True)
                            progressed = True
                            break
                    if not progressed:
                        break
                return
    print("done BAD", BAD, flush=True)


if __name__ == "__main__":
    main()
