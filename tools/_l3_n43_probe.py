"""From N43 (43,36)+(40,44) bud~13: micro moves + 15 unlock."""
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

DEAD = {(45, 36), (46, 36), (27, 40), (28, 40), (38, 44), (52, 44), (42, 48), (41, 48)}


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


def to_n43(sess, data):
    data, _ = haul15_toward(sess, data, (34, 57), max_step=4, label="15soft")
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
    # after Ny36 may be n=3 briefly; pick southmost and north-east
    s = max(free, key=lambda w: (w[1], w[0]))
    n = max([w for w in free if w[1] <= 38], key=lambda w: w[0], default=min(free, key=lambda w: w[1]))
    data, _, st = move_wp(sess, data, s, (40, 44), fr15)
    print("S40", st)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (43, 36), fr15)
    print("N43", st)
    return data


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3n43"]},
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
    data = to_n43(sess, data)
    dump(data, "N43")

    # One-shot scan
    fr15, free, me = dump(data, "scan")
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    cands = []
    for dx in range(1, 6):
        cands += [("N", n, (n[0] + dx, n[1])), ("S", s, (s[0] + dx, s[1]))]
    for dy in (2, 3, 4, 6):
        cands += [("S", s, (s[0], s[1] + dy)), ("N", n, (n[0], n[1] + dy))]
    for t in (
        (44, 36),
        (44, 38),
        (42, 36),
        (40, 46),
        (40, 48),
        (40, 50),
        (42, 46),
        (44, 44),
        (48, 40),
        (43, 40),
        (43, 44),
    ):
        cur = n if abs(t[1] - n[1]) <= abs(t[1] - s[1]) else s
        cands.append(("X", cur, t))

    # Also try 15 unlock candidates interleaved first
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15b = list(fr15)
    west15 = min(fr15b, key=lambda w: w[0])
    east15 = max(fr15b, key=lambda w: w[0])
    for tgt in (
        (west15[0] + 2, west15[1] + 2),
        (west15[0] + 3, west15[1] + 1),
        (west15[0] + 4, west15[1] + 2),
        (west15[0], west15[1] + 3),
        (48, 46),
        (50, 44),
        (47, 44),
    ):
        oth = east15
        if cheb(tgt, oth) < 5 or near_any(tgt, list(freeze14), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, west15, tgt, freeze14)
        print(f"  15 {west15}->{tgt} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("15DEAD", tgt)
            return
        if st == "moved":
            dump(data, "15OK")
            fr15, free, me = dump(data, "after15")
            s = max(free, key=lambda w: (w[1], w[0]))
            n = min(free, key=lambda w: (w[1], w[0]))
            break

    fr15, free, me = dump(data, "try14")
    if len(free) != 2:
        return
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    seen = set()
    for who, cur, ld in cands:
        if ld in seen or ld in DEAD:
            continue
        seen.add(ld)
        other = s if cur == n else n
        if cheb(ld, other) < 5:
            continue
        if near_any(ld, list(fr15), cheb=5):
            print(f"  near15 {ld}")
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        print(f"  {who} {cur}->{ld} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", ld)
            return
        if st == "moved":
            dump(data, "HIT")
            for rnd in range(5):
                if step_budget(data["frame"]) < 4:
                    break
                fr15, free, me = dump(data, f"r{rnd}")
                if len(free) != 2:
                    break
                s = max(free, key=lambda w: (w[1], w[0]))
                n = min(free, key=lambda w: (w[1], w[0]))
                progressed = False
                for cur2, ld2, lab in [
                    (n, (n[0] + 2, n[1]), "Ne"),
                    (n, (n[0] + 3, n[1]), "Ne"),
                    (s, (s[0] + 2, s[1]), "Se"),
                    (s, (s[0] + 3, s[1]), "Se"),
                    (s, (s[0], s[1] + 4), "Ss"),
                    (n, (44, 36), "N44"),
                    (s, (44, 44), "S44"),
                    (s, (48, 44), "S48"),
                ]:
                    if ld2 in DEAD:
                        continue
                    o2 = s if cur2 == n else n
                    if cheb(ld2, o2) < 5 or near_any(ld2, list(fr15), cheb=5):
                        continue
                    data, newc, st = move_wp(sess, data, cur2, ld2, fr15)
                    print(f"    {lab} {cur2}->{ld2} {st}")
                    if st == "dead" or data.get("state") == "GAME_OVER":
                        print("DEAD", ld2)
                        return
                    if st == "moved":
                        dump(data, "HIT2")
                        progressed = True
                        break
                if not progressed:
                    print("stall")
                    break
            dump(data, "END")
            return
    print("none")
    dump(data, "END")


if __name__ == "__main__":
    main()
