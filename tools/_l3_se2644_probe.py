"""From non-frog SE pose free~(34,36)+(36,44) d14=39 bud≈17: catch + east."""
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


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(
        f"{label} ship={me['c']} d14={d14} free={sorted(free)} n={len(free)} "
        f"fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, free, fr15


def boot_se2644():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_se2644"]},
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
    data, _, _ = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, _ = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, _ = move_wp(
        sess, data, max(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (58, 50), freeze14
    )
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lag, (26, 44), fr15)
    if st != "moved":
        print(f"lag {st}", flush=True)
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    # after lag, free may be n=2 or n=3; take easternmost as lead base
    if len(free) < 2:
        return sess, data, False
    # Prefer moving the northern/western remnant — but proven path moved lead from (26,44)
    # In live: lag(23,36)->(26,44) then lead(26,44)->(36,44). So after lag, lead was at 26,44?
    # Actually: lag moved TO 26,44, then the NEW lead is max x — if free=(26,44)+(33,36), lead=(33,36)
    # Log said: lag (23,36)->(26,44); lead (26,44)->(36,44)
    # So they moved the pad that landed at 26,44 further to 36,44!
    lead_pad = (26, 44)
    if lead_pad not in free:
        # fallback: max by y then x among southish
        lead_pad = max(free, key=lambda w: (w[1], w[0]))
    others = [w for w in free if w != lead_pad]
    data, _, st = move_wp(sess, data, lead_pad, (36, 44), fr15)
    print(f"lead {lead_pad}->(36,44) {st}", flush=True)
    if st != "moved":
        return sess, data, False
    dump(data, "SE2644")
    return sess, data, True


def main():
    # Catch north down to y44, or Ny east, or SE south further
    catch_tgts = [
        ("N", (30, 44)),
        ("N", (28, 44)),
        ("N", (32, 44)),
        ("N", (26, 44)),
        ("N", (34, 44)),
        ("N", (30, 42)),
        ("N", (32, 42)),
        ("N", (40, 36)),
        ("N", (42, 36)),
        ("N", (44, 36)),
        ("N", (38, 40)),
        ("N", (40, 40)),
        ("S", (40, 44)),
        ("S", (42, 44)),
        ("S", (44, 44)),
        ("S", (48, 44)),
        ("S", (40, 46)),
        ("S", (44, 46)),
        ("S", (48, 42)),
        ("S", (42, 48)),
    ]
    hits = []
    for who, tgt in catch_tgts:
        print(f"\n===== {who}->{tgt} =====", flush=True)
        sess, data, ok = boot_se2644()
        if not ok:
            print("boot fail", flush=True)
            continue
        d0, free, fr15 = dump(data, "base")
        if len(free) != 2:
            continue
        north = min(free, key=lambda w: (w[1], w[0]))
        south = max(free, key=lambda w: (w[1], w[0]))
        cur = north if who == "N" else south
        other = south if who == "N" else north
        if cheb(tgt, other) < 5 or near_any(tgt, list(fr15), cheb=5):
            print("skip", flush=True)
            continue
        data, newc, st = move_wp(sess, data, cur, tgt, fr15)
        print(f"  {cur}->{tgt} {st}->{newc}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", flush=True)
            continue
        if st != "moved":
            continue
        d1, free1, fr151 = dump(data, "after")
        if len(free1) != 2:
            print(f"FLOCK n={len(free1)}", flush=True)
            continue
        tag = "IMPROVED" if d1 < d0 else ("FLAT" if d1 == d0 else "WORSE")
        print(f"{tag} {d0}->{d1} bud={step_budget(data['frame'])}", flush=True)
        if d1 < d0:
            hits.append((who, tgt, d0, d1, step_budget(data["frame"]), free1))
            # if same-row y44, try dual east
            if len(free1) == 2 and free1[0][1] == free1[1][1]:
                lead = max(free1, key=lambda w: w[0])
                lag = min(free1, key=lambda w: w[0])
                for dx in (2, 4, 6):
                    ld = (lead[0] + dx, lead[1])
                    if cheb(ld, lag) < 5 or near_any(ld, list(fr151), cheb=5):
                        continue
                    data, _, st = move_wp(sess, data, lead, ld, fr151)
                    print(f"  dualL {lead}->{ld} {st}", flush=True)
                    if st != "moved":
                        continue
                    fr151 = lock_other_ship(data["frame"], 14)
                    free2 = count_free14(data["frame"], fr151)
                    if len(free2) != 2:
                        print(f"FLOCK dual n={len(free2)}", flush=True)
                        break
                    lag = min(free2, key=lambda w: w[0])
                    lead2 = max(free2, key=lambda w: w[0])
                    gd = (lead2[0] - 6, lag[1])
                    if cheb(gd, lead2) < 5:
                        gd = (lag[0] + dx, lag[1])
                    data, _, st = move_wp(sess, data, lag, gd, fr151)
                    print(f"  dualG {lag}->{gd} {st}", flush=True)
                    if st == "moved":
                        d2, free3, _ = dump(data, "dual")
                        if len(free3) == 2 and d2 < d1:
                            print(f"HOP2 {d1}->{d2}", flush=True)
                            hits.append(("dual", ld, d1, d2, step_budget(data["frame"]), free3))
                    break

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    if not hits:
        print("none", flush=True)


if __name__ == "__main__":
    main()
