"""After skip_both→S6248 (d14=25 bud≈6): scan south/west exits with raw wps."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
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
    allw = sorted(w["c"] for w in r11l.waypoints(data["frame"]))
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me['c']} d14={d14} free={sorted(free)} "
        f"d15={d15} fr15={sorted(fr15)} all={allw} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, me["c"], allw, fr15


def boot_s6248():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_cont6248"]},
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
        sess, data, max(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (58, 54), freeze14
    )
    # skip_both: lag→(36,44), N4832, S6044, N6038, S6248
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lag = min(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lag, (36, 44), fr15)
    if st != "moved":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (48, 32), fr15)
    if st != "moved":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, (60, 44), fr15)
    if st != "moved":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, north, (60, 38), fr15)
    if st != "moved":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    south = max(free, key=lambda w: (w[1], w[0]))
    # prefer true south pad
    south = max((w for w in free if w[1] >= 40), default=south, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, south, (62, 48), fr15)
    if st != "moved":
        return sess, data, False
    dump(data, "S6248")
    return sess, data, True


# Prefer goal-side; include micro hops from ~(61,48)/(60,38)
CANDS = [
    ((61, 48), (58, 52)),
    ((61, 48), (56, 52)),
    ((61, 48), (54, 52)),
    ((61, 48), (60, 52)),
    ((61, 48), (58, 50)),
    ((61, 48), (56, 50)),
    ((61, 48), (54, 50)),
    ((61, 48), (62, 52)),
    ((61, 48), (55, 53)),
    ((61, 48), (56, 48)),
    ((61, 48), (54, 48)),
    ((60, 38), (56, 44)),
    ((60, 38), (54, 44)),
    ((60, 38), (56, 42)),
    ((60, 38), (52, 44)),
    ((60, 38), (58, 44)),
    ((60, 38), (55, 48)),
]


def main():
    hits = []
    soft = []
    dead = []
    sess, data, ok = boot_s6248()
    if not ok:
        print("boot fail", flush=True)
        return
    d0, ship, allw, fr15 = dump(data, "base")
    # resolve actual south/north from allw near east SE
    se = [c for c in allw if c[0] >= 56]
    print(f"se-pads={se}", flush=True)

    for src_hint, tgt in CANDS:
        if step_budget(data["frame"]) < 3:
            print("budout — reboot", flush=True)
            sess, data, ok = boot_s6248()
            if not ok:
                break
            d0, ship, allw, fr15 = dump(data, "rebase")

        allw = sorted(w["c"] for w in r11l.waypoints(data["frame"]))
        # pick src closest to hint among allw
        if src_hint not in allw:
            near = [c for c in allw if cheb(c, src_hint) <= 2]
            if not near:
                print(f"  no src near {src_hint}", flush=True)
                continue
            src = min(near, key=lambda c: cheb(c, src_hint))
        else:
            src = src_hint
        others = [c for c in allw if c != src]
        # freeze: known 15 deep pads + nearer-to-15
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
        freeze = []
        for c in allw:
            if c == src:
                continue
            if c in ((42, 50), (58, 54), (58, 50)):
                freeze.append(c)
            elif abs(c[0] - me15["c"][0]) + abs(c[1] - me15["c"][1]) + 4 < abs(
                c[0] - me14["c"][0]
            ) + abs(c[1] - me14["c"][1]):
                freeze.append(c)
        if near_any(tgt, freeze, cheb=5):
            print(f"  {src}->{tgt} near15 freeze={freeze}", flush=True)
            continue
        if any(cheb(tgt, o) < 5 for o in others if o not in freeze and o != src):
            # merge with other 14 pad
            o14 = [o for o in others if o not in freeze]
            if any(cheb(tgt, o) < 5 for o in o14):
                print(f"  {src}->{tgt} merge", flush=True)
                continue
        data, newc, st = move_wp(sess, data, src, tgt, freeze)
        bud = step_budget(data["frame"]) if "frame" in data else -1
        print(f"  {src}->{tgt} {st}->{newc} bud={bud}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            dead.append((src, tgt))
            sess, data, ok = boot_s6248()
            if not ok:
                break
            d0, ship, allw, fr15 = dump(data, "redead")
            continue
        if st != "moved":
            soft.append((src, tgt, st))
            continue
        d1, ship1, allw1, _ = dump(data, "after")
        if (data.get("levels_completed") or 0) >= 3:
            print("PASS", flush=True)
            hits.append((src, tgt, d0, d1, bud, "PASS"))
            break
        if d1 < d0:
            print(f"IMPROVED {d0}->{d1}", flush=True)
            hits.append((src, tgt, d0, d1, bud, sorted(allw1)))
            d0 = d1
        else:
            tag = "FLAT" if d1 == d0 else "WORSE"
            print(tag, flush=True)
            soft.append((src, tgt, tag.lower()))
            sess, data, ok = boot_s6248()
            if not ok:
                break
            d0, ship, allw, fr15 = dump(data, "repose")

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    if not hits:
        print("none", flush=True)
    print("soft", soft, flush=True)
    print("dead", dead, flush=True)


if __name__ == "__main__":
    main()
