"""Stop at N6038 after vacW (d14≈26 d15≈14 bud≈6): scan goal last-mile before S6048."""
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
from tools._l3_d15gw_probe import deep15

GOAL14, GOAL15 = (55, 53), (34, 57)


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
    d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
    print(
        f"{label} ship14={me14['c']} d14={d14} free={sorted(free)} "
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, d15, free, fr15


def boot_to_n6038():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_n60g"]},
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
    data, ok = deep15(sess, data)
    if not ok:
        return sess, data, False
    # vacW
    freeze14 = lock_other_ship(data["frame"], 15)
    west = min(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
    data, _, st = move_wp(sess, data, west, (34, 56), freeze14)
    print(f"  vacW {st} bud={step_budget(data['frame'])}", flush=True)
    if st != "moved":
        return sess, data, False
    # L N S6044 N6038
    chain = [
        ("L", (36, 44)),
        ("N", (48, 32)),
        ("S", (60, 44)),
        ("N", (60, 38)),
    ]
    for who, tgt in chain:
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) < 2:
            return sess, data, False
        lead = max(free, key=lambda w: w[0])
        lag = min(free, key=lambda w: w[0])
        north = min(free, key=lambda w: (w[1], w[0]))
        south = max(free, key=lambda w: (w[1], w[0]))
        cur = {"R": lead, "L": lag, "N": north, "S": south}[who]
        data, newc, st = move_wp(sess, data, cur, tgt, fr15)
        print(f"  {who} {cur}->{tgt} {st}->{newc}", flush=True)
        if st != "moved":
            return sess, data, False
    dump(data, "N6038")
    return sess, data, True


CANDS = [
    ("14S", (60, 48)),  # baseline S6048 compare
    ("14S", (60, 50)),
    ("14S", (55, 48)),
    ("14S", (55, 44)),
    ("14S", (58, 48)),
    ("14S", (62, 48)),
    ("14S", (55, 53)),
    ("14S", (52, 48)),
    ("14N", (55, 38)),
    ("14N", (52, 38)),
    ("15E", (52, 56)),
    ("15E", (48, 56)),
    ("15E", (44, 56)),
    ("15E", (40, 56)),
    ("15E", (36, 57)),
    ("15W", (34, 57)),
    ("15W", (32, 57)),
    ("15W", (30, 56)),
]


def main():
    hits = []
    soft = []
    sess, data, ok = boot_to_n6038()
    if not ok:
        print("boot fail", flush=True)
        return
    d14_0, d15_0, free, fr15 = dump(data, "base")
    for label, tgt in CANDS:
        if "frame" not in data or step_budget(data["frame"]) < 3:
            print("budout — reboot", flush=True)
            sess, data, ok = boot_to_n6038()
            if not ok:
                break
            d14_0, d15_0, free, fr15 = dump(data, "rebase")
        fr15 = list(lock_other_ship(data["frame"], 14))
        free = count_free14(data["frame"], fr15)
        freeze14 = lock_other_ship(data["frame"], 15)
        if label.startswith("14"):
            if len(free) < 2:
                continue
            cur = (
                max(free, key=lambda w: (w[1], w[0]))
                if "S" in label
                else min(free, key=lambda w: (w[1], w[0]))
            )
            other = next(w for w in free if w != cur)
            if max(abs(tgt[0] - other[0]), abs(tgt[1] - other[1])) < 5:
                soft.append((label, tgt, "merge"))
                continue
            if near_any(tgt, fr15, cheb=5):
                soft.append((label, tgt, "near15"))
                continue
            data, newc, st = move_wp(sess, data, cur, tgt, fr15)
        else:
            if not fr15:
                continue
            cur = max(fr15, key=lambda w: w[0]) if "E" in label else min(fr15, key=lambda w: w[0])
            other = next((w for w in fr15 if w != cur), cur)
            if max(abs(tgt[0] - other[0]), abs(tgt[1] - other[1])) < 5:
                soft.append((label, tgt, "merge"))
                continue
            if near_any(tgt, list(freeze14), cheb=5):
                soft.append((label, tgt, "near15"))
                continue
            data, newc, st = move_wp(sess, data, cur, tgt, freeze14)
        print(
            f"  {label} {cur}->{tgt} {st}->{newc} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}",
            flush=True,
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            print("DEAD — reboot", flush=True)
            soft.append((label, tgt, "dead"))
            sess, data, ok = boot_to_n6038()
            if not ok:
                break
            continue
        if st != "moved":
            soft.append((label, tgt, st))
            continue
        d14, d15, _, _ = dump(data, f"hit-{label}{tgt}")
        tags = []
        if d14 < 25:
            tags.append("BEAT25")
        elif d14 < d14_0:
            tags.append(f"BEAT14:{d14}")
        if d15 < d15_0:
            tags.append(f"BEAT15:{d15}")
        if (data.get("levels_completed") or 0) >= 3:
            tags.append("PASS")
        print(f"RESULT {' '.join(tags) or 'FLAT/IMPROVED'} {label}{tgt} d14={d14} d15={d15}", flush=True)
        hits.append((tags, label, tgt, d14, d15, step_budget(data["frame"])))
        sess, data, ok = boot_to_n6038()
        if not ok:
            break

    print("\n===== SOFT =====", flush=True)
    for s in soft:
        print(s, flush=True)
    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)


if __name__ == "__main__":
    main()
