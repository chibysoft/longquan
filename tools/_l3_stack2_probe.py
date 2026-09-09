"""STACK with soft15 required; from (40,36)+(40,44) east-only (no suicidal 15)."""
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

DEAD = {
    (27, 40),
    (28, 40),
    (38, 44),
    (45, 47),
    (52, 44),
    (35, 44),
    (37, 40),
    (38, 40),
    (42, 48),
    (41, 48),
}


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me['c']} d14={d14} free14={sorted(free)} n={len(free)} "
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}"
    )
    return fr15, free, me


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def to_stack(sess, data):
    data, _ = haul15_toward(sess, data, (34, 57), max_step=4, label="15soft")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print("leadS", st)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    print("frog", st)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, s, (s[0] + 3, s[1]), fr15)
    print("S+3", st)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (23, 40), fr15)
    print("Nwest", st)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, s, (40, 44), fr15)
    print("S40", st)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (40, 36), fr15)
    print("Ny36", st)
    return data, st == "moved"


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3stack2"]},
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
    dump(data, "STACK")
    if not ok:
        print("stack fail")
        return

    for rnd in range(10):
        if step_budget(data["frame"]) < 4:
            print("bud low")
            break
        fr15, free, me = dump(data, f"r{rnd}")
        if len(free) != 2:
            break
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
        trials = [
            (north, (north[0] + 4, north[1]), "Ne"),
            (north, (north[0] + 5, north[1]), "Ne"),
            (north, (north[0] + 8, north[1]), "Ne"),
            (north, (48, 36), "N48"),
            (north, (52, 36), "N52"),
            (north, (44, 36), "N44"),
            (south, (south[0] + 4, south[1]), "Se"),
            (south, (south[0] + 5, south[1]), "Se"),
            (south, (48, 44), "S48"),
            (south, (south[0], min(56, south[1] + 4)), "Ss"),
            (south, (south[0] + 4, south[1] + 4), "Sse"),
            (north, (55, 36), "Ng"),
            (south, (55, 44), "Sg"),
            (south, (55, 48), "Sg"),
            (north, (north[0] + 2, north[1] + 4), "Ns"),
        ]
        moved = False
        for cur, ld, lab in trials:
            if ld in DEAD:
                continue
            other = north if cur == south else south
            if cheb(ld, other) < 5:
                continue
            if near_any(ld, list(fr15), cheb=5):
                print(f"  near15 {ld}")
                continue
            if cur == north and ld[0] < north[0]:
                continue
            data, newc, st = move_wp(sess, data, cur, ld, fr15)
            print(f"  {lab} {cur}->{ld} {st}->{newc}")
            if st == "dead" or data.get("state") == "GAME_OVER":
                print("DEAD", ld)
                return
            if st == "moved":
                dump(data, "HIT")
                if len(count_free14(data["frame"], lock_other_ship(data["frame"], 14))) != 2:
                    print("FLOCK")
                    return
                moved = True
                break
        if not moved:
            # last resort: move west15 further east if merge-free
            freeze14 = lock_other_ship(data["frame"], 15)
            fr15b = list(lock_other_ship(data["frame"], 14))
            west15 = min(fr15b, key=lambda w: w[0])
            east15 = max(fr15b, key=lambda w: w[0])
            for tgt in ((west15[0] + 4, west15[1] + 2), (west15[0] + 2, west15[1] + 3), (48, 48), (50, 46)):
                if cheb(tgt, east15) < 5 or near_any(tgt, list(freeze14), cheb=5):
                    continue
                data, newc, st = move_wp(sess, data, west15, tgt, freeze14)
                print(f"  15rescue {west15}->{tgt} {st}")
                if st == "dead" or data.get("state") == "GAME_OVER":
                    print("15DEAD")
                    return
                if st == "moved":
                    dump(data, "15OK")
                    moved = True
                    break
            if not moved:
                print("stalled")
                break
    dump(data, "END")


if __name__ == "__main__":
    main()
