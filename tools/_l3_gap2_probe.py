"""A: N-west≥10 from S+3. B: clear15 seal then y36 +3 east."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east, translate2_nudge
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, haul15_toward, lock_other_ship, near_any
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


def boot(tag):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": [tag]},
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
    return sess, data, lv0


def to_s3(sess, data):
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
    south = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, (south[0] + 3, south[1]), fr15)
    print("S+3", st)
    return data


def main():
    print("=== A N-west / S+10 ===")
    sess, data, lv0 = boot("r11l_l3gap2a")
    data = to_s3(sess, data)
    fr15, free, me = dump(data, "BASE")
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    for who, cur, ld in [
        ("N", north, (23, 40)),
        ("N", north, (22, 40)),
        ("N", north, (20, 40)),
        ("N", north, (18, 40)),
        ("N", north, (24, 40)),
        ("S", south, (38, 44)),
        ("S", south, (42, 44)),
        ("S", south, (36, 44)),
        ("S", south, (40, 44)),
        ("S", south, (28, 48)),
        ("S", south, (32, 48)),
        ("S", south, (24, 48)),
    ]:
        other = south if who == "N" else north
        if cheb(ld, other) < 5:
            print(f"  skip merge {ld}")
            continue
        if near_any(ld, list(fr15), cheb=5):
            print(f"  skip near15 {ld}")
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        n = len(count_free14(data["frame"], lock_other_ship(data["frame"], 14))) if "frame" in data else 0
        print(f"  {who} {cur}->{ld} {st}->{newc} n={n}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD — stop A")
            break
        if st == "moved" and n == 2:
            dump(data, "AHIT")
            # continue a few east
            for i in range(5):
                fr15, free, me = dump(data, f"A{i}")
                if len(free) != 2:
                    break
                s = max(free, key=lambda w: (w[1], w[0]))
                nwp = min(free, key=lambda w: (w[1], w[0]))
                progressed = False
                for w, c, t in [
                    ("S", s, (s[0] + 4, s[1])),
                    ("S", s, (s[0] + 5, s[1])),
                    ("S", s, (s[0] + 8, s[1])),
                    ("S", s, (s[0] + 3, s[1])),
                    ("N", nwp, (nwp[0] + 4, nwp[1])),
                    ("N", nwp, (nwp[0] + 5, nwp[1])),
                    ("S", s, (s[0] + 4, s[1] + 2)),
                    ("N", nwp, (nwp[0] + 2, 36)),
                    ("N", nwp, (37, 36)),
                ]:
                    o = nwp if w == "S" else s
                    if cheb(t, o) < 5 or near_any(t, list(fr15), cheb=5):
                        continue
                    data, newc, st = move_wp(sess, data, c, t, fr15)
                    print(f"    {w} {c}->{t} {st}")
                    if st == "dead" or data.get("state") == "GAME_OVER":
                        print("DEAD cont")
                        dump(data, "AEND")
                        break
                    if st == "moved":
                        dump(data, "Aadv")
                        progressed = True
                        break
                else:
                    pass
                if not progressed or data.get("state") == "GAME_OVER":
                    if data.get("state") == "GAME_OVER":
                        break
                    print("A stall round")
                    break
            dump(data, "AEND")
            break

    print("=== B clear15 seal then +3 east ===")
    sess, data, lv0 = boot("r11l_l3gap2b")
    dump(data, "GATE")
    # Move western 15 wp south to unlock (37,36)
    fr15 = lock_other_ship(data["frame"], 14)
    west15 = min(fr15, key=lambda w: w[0])
    freeze14 = lock_other_ship(data["frame"], 15)
    for tgt in (
        (west15[0], west15[1] + 6),
        (west15[0], west15[1] + 8),
        (west15[0] + 2, west15[1] + 6),
        (west15[0] - 2, west15[1] + 6),
        (west15[0] + 4, west15[1] + 4),
        (west15[0], min(56, west15[1] + 10)),
    ):
        if near_any(tgt, list(freeze14), cheb=5):
            continue
        data, newc, st = move_wp(sess, data, west15, tgt, freeze14)
        print(f"  15south {west15}->{tgt} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("15 DEAD")
            return
        if st == "moved":
            dump(data, "15moved")
            break
    else:
        print("15 south fail, try haul")
        data, _ = haul15_toward(sess, data, (34, 57), max_step=10, label="15haul")
        dump(data, "15haul")

    freeze15 = lock_other_ship(data["frame"], 14)
    data, ok = translate2_nudge(sess, data, freeze15, lead_dx=3)
    dump(data, "after+3")
    print("+3 ok", ok)
    if ok and len(count_free14(data["frame"], lock_other_ship(data["frame"], 14))) == 2:
        for i in range(3):
            freeze15 = lock_other_ship(data["frame"], 14)
            data, ok = translate2_nudge(sess, data, freeze15, lead_dx=3)
            dump(data, f"plus{i}")
            if not ok:
                break
    dump(data, "BEND")


if __name__ == "__main__":
    main()
