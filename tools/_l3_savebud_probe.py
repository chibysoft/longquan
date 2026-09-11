"""Save-bud variants: skip east15b and/or S6048 so fin15 leaves bud>=3 for d15→0."""
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

GOAL14, GOAL15 = (55, 53), (34, 57)


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


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


def boot_mideast():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_savebud"]},
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
    return sess, data


def move15(sess, data, cur, tgt):
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    other = next((w for w in flock if w != cur), cur)
    if cheb(tgt, other) < 5 or near_any(tgt, list(freeze14), cheb=5):
        return data, "blocked"
    data, newc, st = move_wp(sess, data, cur, tgt, freeze14)
    print(f"  15 {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}", flush=True)
    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, "dead"
    return data, st


def move14(sess, data, who, tgt):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return data, "nfree"
    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    cur = {"R": lead, "L": lag, "N": north, "S": south}[who]
    other = next(w for w in free if w != cur)
    if cheb(tgt, other) < 5 or near_any(tgt, list(fr15), cheb=5):
        return data, "blocked"
    data, newc, st = move_wp(sess, data, cur, tgt, fr15)
    print(f"  14{who} {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}", flush=True)
    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, "dead"
    return data, st


def deep15(sess, data, *, do_east15b=True, early_tgt=(40, 56)):
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    east = max(flock, key=lambda w: w[0])
    if east[0] < 56:
        for tgt in ((58, 42), (56, 44)):
            if cheb(tgt, west) < 5:
                continue
            data, st = move15(sess, data, east, tgt)
            if st == "dead":
                return data, False
            if st == "moved":
                freeze14 = lock_other_ship(data["frame"], 15)
                flock = list(lock_other_ship(data["frame"], 14))
                west = min(flock, key=lambda w: w[0])
                east = max(flock, key=lambda w: w[0])
                break
    moved_w = False
    for tgt in ((42, 50), (48, 42)):
        if cheb(tgt, east) < 5:
            continue
        data, st = move15(sess, data, west, tgt)
        if st == "dead":
            return data, False
        if st == "moved":
            moved_w = True
            freeze14 = lock_other_ship(data["frame"], 15)
            flock = list(lock_other_ship(data["frame"], 14))
            west = min(flock, key=lambda w: w[0])
            east = max(flock, key=lambda w: w[0])
            break
    if not moved_w:
        return data, False
    if do_east15b and east[1] < 52:
        for tgt in ((58, 54), (58, 50)):
            if cheb(tgt, west) < 5:
                continue
            data, st = move15(sess, data, east, tgt)
            if st == "dead":
                return data, False
            if st == "moved":
                freeze14 = lock_other_ship(data["frame"], 15)
                flock = list(lock_other_ship(data["frame"], 14))
                west = min(flock, key=lambda w: w[0])
                east = max(flock, key=lambda w: w[0])
                break
    if early_tgt:
        east = max(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
        west = min(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
        data, st = move15(sess, data, east, early_tgt)
        if st == "dead":
            return data, False
        if st != "moved":
            # try alts
            for alt in ((44, 56), (48, 56), (36, 56)):
                data, st = move15(sess, data, east, alt)
                if st == "moved":
                    break
            if st != "moved":
                return data, False
    dump(data, "after-deep")
    return data, True


def se_to_n6038(sess, data):
    for who, tgt in (("L", (36, 44)), ("N", (48, 32)), ("S", (60, 44)), ("N", (60, 38))):
        data, st = move14(sess, data, who, tgt)
        if st != "moved":
            return data, False
    dump(data, "N6038")
    return data, True


def do_s6048(sess, data):
    data, st = move14(sess, data, "S", (60, 48))
    if st != "moved":
        data, st = move14(sess, data, "S", (62, 48))
    if st != "moved":
        return data, False
    dump(data, "S6048")
    return data, True


def do_fin15(sess, data):
    flock = list(lock_other_ship(data["frame"], 14))
    if not flock:
        return data, False
    rem = sorted(flock, key=lambda w: (abs(w[0] - 42) + abs(w[1] - 50), -w[0]))[0]
    if rem[0] < 38:
        # already both near goal — try haul further
        rem = max(flock, key=lambda w: abs(w[0] - 34) + abs(w[1] - 57))
    for vt in ((34, 56), (34, 57), (32, 56), (36, 57), (34, 55)):
        data, st = move15(sess, data, rem, vt)
        if st == "moved":
            dump(data, "fin15")
            return data, True
        if st == "dead":
            return data, False
        rem = sorted(lock_other_ship(data["frame"], 14), key=lambda w: (abs(w[0] - 42) + abs(w[1] - 50), -w[0]))[0]
    return data, False


# After fin15-like pose, try finish d15 / push d14
FINISH = [
    ("15goal", "15", (34, 57)),
    ("15a", "15", (34, 56)),
    ("15b", "15", (36, 57)),
    ("15c", "15", (32, 57)),
    ("15d", "15", (37, 57)),
    ("14S5553", "14S", (55, 53)),
    ("14S5550", "14S", (55, 50)),
    ("14S60452", "14S", (60, 52)),
]


def try_finish(sess, data, d14_0, d15_0):
    hits = []
    flock = list(lock_other_ship(data["frame"], 14))
    free = count_free14(data["frame"], flock)
    for name, kind, tgt in FINISH:
        if "frame" not in data or step_budget(data["frame"]) < 2:
            print("  budout finish", flush=True)
            break
        if kind == "15":
            if not flock:
                continue
            # move pad farthest from goal
            cur = max(flock, key=lambda w: abs(w[0] - GOAL15[0]) + abs(w[1] - GOAL15[1]))
            data, st = move15(sess, data, cur, tgt)
        else:
            data, st = move14(sess, data, "S", tgt)
        if st == "dead":
            print("  DEAD finish", flush=True)
            return hits, True  # need reboot
        if st != "moved":
            continue
        d14, d15, _, _ = dump(data, f"fin-{name}")
        tag = []
        if d15 < d15_0:
            tag.append(f"BEAT15:{d15}")
        if d14 < d14_0:
            tag.append(f"BEAT14:{d14}")
        if d15 == 0:
            tag.append("D15CLEAR")
        if d14 == 0:
            tag.append("D14CLEAR")
        if (data.get("levels_completed") or 0) >= 3:
            tag.append("PASS")
        print(f"RESULT {' '.join(tag) or 'LIVE'} {name}", flush=True)
        hits.append((tag, name, d14, d15, step_budget(data["frame"])))
        flock = list(lock_other_ship(data["frame"], 14))
        # one success path — keep going on same pose for chained finish
        d14_0, d15_0 = d14, d15
        if d15 == 0 and d14 == 0:
            break
    return hits, False


VARIANTS = [
    # name, do_east15b, do_s6048, early_tgt
    ("base-v64", True, True, (40, 56)),
    ("skip-e54", False, True, (40, 56)),
    ("skip-s6048", True, False, (40, 56)),
    ("skip-both", False, False, (40, 56)),
    ("skip-e54-early44", False, True, (44, 56)),
    ("e54-no-early-fin-only", True, True, None),  # classic then fin only if remnant
]


def main():
    all_hits = []
    for name, do_e54, do_s60, early in VARIANTS:
        print(f"\n===== {name} e54={do_e54} s60={do_s60} early={early} =====", flush=True)
        sess, data = boot_mideast()
        data, ok = deep15(sess, data, do_east15b=do_e54, early_tgt=early)
        if not ok:
            print("SOFT deep", flush=True)
            continue
        data, ok = se_to_n6038(sess, data)
        if not ok:
            print("SOFT SE", flush=True)
            continue
        if do_s60:
            data, ok = do_s6048(sess, data)
            if not ok:
                print("SOFT S6048", flush=True)
                continue
        # fin15 if remnant exists
        data, _ = do_fin15(sess, data)
        d14, d15, _, _ = dump(data, "pose")
        beat = ""
        if d15 < 4:
            beat = " BEAT15<4"
        if d14 < 25:
            beat += " BEAT14<25"
        print(
            f"POSE {name} d14={d14} d15={d15} bud={step_budget(data['frame'])}{beat}",
            flush=True,
        )
        hits, dead = try_finish(sess, data, d14, d15)
        for h in hits:
            all_hits.append((name,) + h)
        if (data.get("levels_completed") or 0) >= 3:
            print("PASS L3!", flush=True)
            break

    print("\n===== ALL HITS =====", flush=True)
    for h in all_hits:
        print(h, flush=True)
    best = sorted(
        [h for h in all_hits if h[1]],
        key=lambda x: (
            0 if "PASS" in x[1] else 1,
            x[3] if isinstance(x[3], int) else 99,  # d15
            x[2] if isinstance(x[2], int) else 99,  # d14
            -x[4],
        ),
    )
    print("BEST", best[:12] or "none", flush=True)


if __name__ == "__main__":
    main()
