"""Compressed frog→S(40,44)→Nwest; save bud for haul15 + continue."""
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
    (25, 44),  # N catch from (23,40) — deadly as dest from north
    (28, 40),
    (35, 44),
    (37, 40),
    (38, 40),
    (42, 48),
    (41, 48),
    (34, 46),
    (31, 44),
    (27, 48),
    (36, 48),
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


def try_move(sess, data, cur, ld, other, fr15, label):
    if ld in DEAD:
        print(f"  skip known dead {ld}")
        return data, False
    if cheb(ld, other) < 5:
        print(f"  skip merge {ld}")
        return data, False
    if near_any(ld, list(fr15), cheb=5):
        print(f"  skip near15 {ld}")
        return data, False
    data, newc, st = move_wp(sess, data, cur, ld, fr15)
    print(f"  {label} {cur}->{ld} {st}->{newc}")
    if st == "dead" or data.get("state") == "GAME_OVER":
        print("DEAD", ld)
        DEAD.add(ld)
        return data, False
    if st == "moved":
        dump(data, "HIT")
        if len(count_free14(data["frame"], lock_other_ship(data["frame"], 14))) != 2:
            print("FLOCK")
            return data, False
        return data, True
    return data, False


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3fast"]},
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

    # soft 15
    data, _ = haul15_toward(sess, data, (34, 57), max_step=4, label="15soft")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print("leadS", st)
    dump(data, "afterS")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    print("frog", st)
    dump(data, "afterFrog")

    # compressed: S big to (40,44) then Nwest
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    for tgt in ((40, 44), (38, 44), (42, 44), (36, 44)):
        data, ok = try_move(sess, data, south, tgt, north, fr15, "Sbig")
        if ok:
            break
        if data.get("state") == "GAME_OVER":
            return
    else:
        print("Sbig fail")
        return

    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    data, ok = try_move(sess, data, north, (23, 40), south, fr15, "Nwest")
    if not ok:
        for t in ((22, 40), (20, 40), (18, 40)):
            data, ok = try_move(sess, data, north, t, south, fr15, "Nwest")
            if ok or data.get("state") == "GAME_OVER":
                break
    dump(data, "COMPRESSED")

    # haul15 while bud allows
    for h in range(5):
        if step_budget(data["frame"]) < 8:
            break
        data, _ = haul15_toward(sess, data, (34, 57), max_step=8, label=f"15h{h}")
        dump(data, f"H{h}")

    for rnd in range(10):
        bud = step_budget(data["frame"])
        if bud < 4:
            print("bud low")
            break
        fr15, free, me = dump(data, f"r{rnd}")
        if len(free) != 2:
            print("broke", free)
            break
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
        moved = False
        # Prefer S east if not near15; N east on y40; N to y36 corridor
        trials = []
        for dx in (4, 5, 6, 8, 10):
            trials.append((south, (south[0] + dx, south[1]), "Se"))
        for dx in (4, 6, 8, 10):
            trials.append((north, (north[0] + dx, north[1]), "Ne"))
        trials.append((north, (40, 36), "Ny36"))
        trials.append((north, (44, 36), "Ny36"))
        trials.append((north, (37, 36), "Ny36"))
        trials.append((north, (48, 36), "Ny36"))
        trials.append((south, (south[0] + 4, south[1] + 2), "Sse"))
        trials.append((south, (48, 44), "S48"))
        trials.append((south, (52, 44), "S52"))
        trials.append((south, (55, 44), "S55"))
        trials.append((north, (south[0] - 10, south[1]), "Ncatch"))
        trials.append((north, (south[0] - 12, south[1]), "Ncatch"))
        for cur, ld, lab in trials:
            other = south if cur == north else north
            data, ok = try_move(sess, data, cur, ld, other, fr15, lab)
            if data.get("state") == "GAME_OVER":
                dump(data, "END")
                return
            if ok:
                moved = True
                break
        if not moved:
            if bud >= 8:
                data, _ = haul15_toward(sess, data, (34, 57), max_step=6, label="15x")
                dump(data, "15x")
            else:
                print("stalled")
                break
    dump(data, "END")


if __name__ == "__main__":
    main()
