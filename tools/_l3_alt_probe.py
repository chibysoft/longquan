"""After gate: leadS then alternate lag targets; also test post_mideast +3."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east, advance_14_post_mideast, translate2_nudge
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, haul15_toward, lock_other_ship, near_any
from tools.r11l_seated_clear import clear_l1, reset


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(
        f"{label} ship={me['c']} d14={d14} free={sorted(free)} n={len(free)} "
        f"bud={step_budget(data['frame'])}"
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


def lead_s4(sess, data):
    data, _ = haul15_toward(sess, data, (34, 57), max_step=4, label="15soft")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print("leadS", st)
    dump(data, "afterLeadS")
    return data


def main():
    # --- Path P: post_mideast only (no south) ---
    print("=== PATH P post_mideast ===")
    sess, data, lv0 = boot("r11l_l3altP")
    dump(data, "GATE")
    data, ok = advance_14_post_mideast(sess, data, lv0, rounds=4)
    dump(data, "PEND")
    print("P ok", ok, "state", data.get("state"))

    # --- Path Q: leadS then try lag targets ---
    print("=== PATH Q leadS + lag variants ===")
    sess, data, lv0 = boot("r11l_l3altQ")
    data = lead_s4(sess, data)
    fr15, free, me = dump(data, "Q0")
    if len(free) != 2:
        print("Q flock", free)
        return
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    # Try each lag candidate on FRESH boots — only first attempt on this card
    cands = [
        (lag[0] + 2, lead[1] + 4),  # classic frog
        (lag[0] + 4, lead[1] + 4),
        (lag[0], lead[1] + 2),
        (lag[0] + 2, lead[1] + 2),
        (lag[0] - 2, lead[1] + 4),
        (lag[0] + 5, lead[1]),
        (lag[0] + 2, lead[1]),
        (lag[0] - 4, lead[1]),
        (lag[0], lead[1] + 6),
        (lag[0] + 6, lead[1] + 4),
    ]
    for ld in cands:
        if cheb(ld, lead) < 5:
            print(f"  skip merge {ld}")
            continue
        if near_any(ld, list(fr15), cheb=5):
            print(f"  skip near15 {ld}")
            continue
        data, newc, st = move_wp(sess, data, lag, ld, fr15)
        n = len(count_free14(data["frame"], lock_other_ship(data["frame"], 14))) if "frame" in data else 0
        print(f"  lag {lag}->{ld} {st}->{newc} n={n}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD — reboot next cand")
            sess, data, lv0 = boot(f"r11l_l3altQ_{ld[0]}_{ld[1]}")
            data = lead_s4(sess, data)
            fr15, free, me = dump(data, "Qre")
            if len(free) != 2:
                return
            lead = max(free, key=lambda w: (w[1], w[0]))
            lag = min(free, key=lambda w: (w[1], w[0]))
            continue
        if st == "moved" and n == 2:
            dump(data, "QHIT")
            # continue east from here
            for rnd in range(6):
                fr15, free, me = dump(data, f"Qr{rnd}")
                if len(free) != 2 or step_budget(data["frame"]) < 6:
                    break
                south = max(free, key=lambda w: (w[1], w[0]))
                north = min(free, key=lambda w: (w[1], w[0]))
                advanced = False
                for who, cur, tgt in [
                    ("S", south, (south[0] + 3, south[1])),
                    ("S", south, (south[0] + 5, south[1])),
                    ("S", south, (south[0] + 8, south[1])),
                    ("S", south, (south[0] + 10, south[1])),
                    ("N", north, (north[0] + 5, north[1])),
                    ("N", north, (north[0] + 3, north[1])),
                    ("S", south, (south[0] + 4, south[1] + 2)),
                    ("N", north, (north[0] + 2, north[1] + 4)),
                    ("S", south, (south[0], south[1] + 4)),
                ]:
                    other = north if who == "S" else south
                    if cheb(tgt, other) < 5:
                        continue
                    if near_any(tgt, list(fr15), cheb=5):
                        continue
                    data, newc, st = move_wp(sess, data, cur, tgt, fr15)
                    print(f"    {who} {cur}->{tgt} {st}")
                    if st == "dead" or data.get("state") == "GAME_OVER":
                        print("DEAD cont", tgt)
                        return
                    if st == "moved":
                        nn = len(count_free14(data["frame"], lock_other_ship(data["frame"], 14)))
                        dump(data, "Qadv")
                        if nn != 2:
                            print("flock break")
                            return
                        advanced = True
                        break
                if not advanced:
                    print("Qr stalled")
                    break
            dump(data, "QEND")
            return
        if st == "moved" and n != 2:
            print("seal n=", n, "— reboot")
            sess, data, lv0 = boot(f"r11l_l3altQs_{ld[0]}")
            data = lead_s4(sess, data)
            fr15, free, me = dump(data, "Qre2")
            if len(free) != 2:
                return
            lead = max(free, key=lambda w: (w[1], w[0]))
            lag = min(free, key=lambda w: (w[1], w[0]))
    print("Q no good lag")


if __name__ == "__main__":
    main()
