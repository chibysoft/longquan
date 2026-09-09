"""Deep 15 (east+west) → frog without N43 → S-west then N-south."""
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
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(
        f"{label} ship14={me['c']} d14={d14} free14={sorted(free)} n={len(free)} "
        f"ship15={me15['c']} fr15={sorted(fr15)} bud={step_budget(data['frame'])}"
    )
    return fr15, free, me


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def mv(sess, data, cur, ld, other, fr15, label):
    if cheb(ld, other) < 5:
        print(f"  skip merge {label} {ld}")
        return data, False
    if near_any(ld, list(fr15), cheb=5):
        print(f"  skip near15 {label} {ld}")
        return data, False
    if ld[1] <= 36 and ld[0] >= 45:
        print(f"  skip y36ban {ld}")
        return data, False
    data, newc, st = move_wp(sess, data, cur, ld, fr15)
    print(f"  {label} {cur}->{ld} {st}->{newc}")
    if st == "dead" or data.get("state") == "GAME_OVER":
        print("DEAD", ld)
        return data, False
    if st == "moved":
        dump(data, "HIT")
        return data, True
    return data, False


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3gap14"]},
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

    # deep 15
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    west15 = min(fr15, key=lambda w: w[0])
    east15 = max(fr15, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, east15, (58, 42), freeze14)
    print("east15", st)
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    west15 = min(fr15, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, west15, (48, 42), freeze14)
    print("west15", st)
    dump(data, "15deep")

    # frog without N43
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
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (40, 36), fr15)
    print("Ny36", st)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, s, (40, 44), fr15)
    print("S40", st)
    fr15, free, me = dump(data, "STACK")  # (40,36)+(40,44) bud hopefully ~10+

    # Open gap: move south WEST or SE small, then north south
    for rnd in range(8):
        if step_budget(data["frame"]) < 4:
            print("bud low")
            break
        fr15, free, me = dump(data, f"r{rnd}")
        if len(free) != 2:
            break
        s = max(free, key=lambda w: (w[1], w[0]))
        n = min(free, key=lambda w: (w[1], w[0]))
        trials = [
            (s, (s[0] - 4, s[1]), "Sw"),
            (s, (s[0] - 5, s[1]), "Sw"),
            (s, (s[0] - 6, s[1]), "Sw"),
            (s, (36, 44), "S36"),
            (s, (35, 44), "S35"),
            (s, (38, 44), "S38"),
            (s, (s[0] - 4, s[1] + 2), "Ssw"),
            (n, (43, 42), "N42"),
            (n, (42, 42), "N42"),
            (n, (44, 40), "N40"),
            (n, (43, 40), "N40"),
            (n, (n[0] + 3, n[1]), "Ne"),
            (n, (43, 36), "N43"),
            (s, (42, 44), "Se"),
            (s, (s[0] + 2, s[1]), "Se"),
            (s, (42, 46), "Sse"),
            (n, (n[0], n[1] + 4), "Ns"),
        ]
        moved = False
        for cur, ld, lab in trials:
            data, ok = mv(sess, data, cur, ld, s if cur == n else n, fr15, lab)
            if data.get("state") == "GAME_OVER":
                return
            if ok:
                moved = True
                break
        if not moved:
            print("stalled")
            break
    dump(data, "END")


if __name__ == "__main__":
    main()
