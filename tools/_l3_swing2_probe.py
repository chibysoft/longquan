"""From N438: S-west open gap → N south → east. Avoid (42,46)."""
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


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(
        f"{label} ship={me['c']} d14={d14} free={sorted(free)} n={len(free)} "
        f"fr15={sorted(fr15)} bud={step_budget(data['frame'])}"
    )
    return fr15, free, me


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def setup(sess, data):
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    print("east15", st)
    freeze14 = lock_other_ship(data["frame"], 15)
    west15 = min(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
    data, _, st = move_wp(sess, data, west15, (48, 42), freeze14)
    print("west15", st)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print("leadS", st)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    print("frog", st)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (40, 36), fr15)
    print("Ny36", st)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, s, (40, 44), fr15)
    print("S40", st)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (43, 38), fr15)
    print("N438", st)
    return data, st == "moved"


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3swing2"]},
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
    data, ok = setup(sess, data)
    dump(data, "BASE")
    if not ok:
        return

    # One S-west
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    data, newc, st = move_wp(sess, data, s, (36, 44), fr15)
    print(f"Sw {s}->(36,44) {st}->{newc}")
    if st != "moved":
        # try (38,44)
        data, newc, st = move_wp(sess, data, s, (38, 44), fr15)
        print(f"Sw38 {st}")
        if st != "moved":
            return
    dump(data, "SW")

    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    for ld in ((43, 42), (43, 40), (44, 42), (42, 40), (44, 40), (45, 42), (43, 44)):
        if cheb(ld, s) < 5:
            print(f"  merge {ld} cheb={cheb(ld, s)}")
            continue
        if near_any(ld, list(fr15), cheb=5):
            print(f"  near15 {ld}")
            continue
        data, newc, st = move_wp(sess, data, n, ld, fr15)
        print(f"  N {n}->{ld} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", ld)
            return
        if st == "moved":
            dump(data, "Nhit")
            break
    else:
        print("N fail")
        return

    # Recover east: move S back east, N east
    for rnd in range(8):
        if step_budget(data["frame"]) < 4:
            print("bud low")
            break
        fr15, free, me = dump(data, f"r{rnd}")
        if len(free) != 2:
            break
        s = max(free, key=lambda w: (w[1], w[0]))
        n = min(free, key=lambda w: (w[1], w[0]))
        moved = False
        for cur, ld, lab in [
            (s, (s[0] + 4, s[1]), "Se"),
            (s, (s[0] + 5, s[1]), "Se"),
            (s, (40, 44), "S40"),
            (s, (44, 44), "S44"),
            (s, (48, 44), "S48"),
            (n, (n[0] + 4, n[1]), "Ne"),
            (n, (n[0] + 2, n[1]), "Ne"),
            (n, (n[0], n[1] + 2), "Ns"),
            (s, (s[0] + 4, s[1] + 2), "Sse"),
            (n, (48, 42), "Ng"),
            (s, (55, 48), "Sg"),
        ]:
            if cheb(ld, s if cur == n else n) < 5:
                continue
            if near_any(ld, list(fr15), cheb=5):
                continue
            if ld[1] <= 36 and ld[0] >= 45:
                continue
            if ld in {(42, 46)}:
                continue
            data, newc, st = move_wp(sess, data, cur, ld, fr15)
            print(f"  {lab} {cur}->{ld} {st}")
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD", ld)
                return
            if st == "moved":
                dump(data, "adv")
                moved = True
                break
        if not moved:
            print("stall")
            break
    dump(data, "END")


if __name__ == "__main__":
    main()
