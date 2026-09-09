"""Skip Nwest: frog→S+3→S40→Ny36→N+3; more bud for east."""
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


def mv(sess, data, cur, ld, other, fr15, label):
    if ld in DEAD:
        print(f"  skip dead {ld}")
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
        json={"tags": ["r11l_l3nonw"]},
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
    dump(data, "FROG")

    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    data, ok = mv(sess, data, s, (s[0] + 3, s[1]), n, fr15, "S+3")
    if not ok:
        return

    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    data, ok = mv(sess, data, s, (40, 44), n, fr15, "S40")
    if not ok:
        return

    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    data, ok = mv(sess, data, n, (40, 36), s, fr15, "Ny36")
    if not ok:
        # try from whatever north is
        print("Ny36 fail")
        return
    dump(data, "STACK")

    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    data, ok = mv(sess, data, n, (43, 36), s, fr15, "N43")
    dump(data, "N43")

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
            (n, (n[0] + 2, n[1]), "Ne2"),
            (n, (n[0] + 3, n[1]), "Ne3"),
            (n, (44, 36), "N44"),
            (s, (s[0] + 2, s[1]), "Se2"),
            (s, (s[0] + 3, s[1]), "Se3"),
            (s, (42, 44), "S42"),
            (s, (43, 44), "S43"),
            (s, (s[0], s[1] + 4), "Ss"),
            (n, (n[0] + 2, n[1] + 2), "Nse"),
            (s, (s[0] + 2, s[1] + 2), "Sse"),
        ]:
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
