"""One-boot: from N438 deep-vacate 15 south, then retry 14 N/S exits."""
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
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me['c']} d14={d14} free={sorted(free)} "
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return fr15, free


def boot_to_n438(sess):
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    lv0 = data.get("levels_completed") or 0
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    freeze14 = lock_other_ship(data["frame"], 15)
    west15 = min(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
    data, _, st = move_wp(sess, data, west15, (48, 42), freeze14)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, _ = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, n, (40, 36), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    data, _, _ = move_wp(sess, data, s, (40, 44), fr15)
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (43, 38), fr15)
    return data, st == "moved"


def try14(sess, data, label):
    """Try promising 14 exits; return (data, hit)."""
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) != 2:
        return data, False
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    cands = [
        (n, (45, 40)),
        (n, (46, 38)),
        (n, (46, 40)),
        (n, (44, 38)),
        (n, (45, 38)),
        (n, (48, 40)),
        (n, (47, 40)),
        (n, (44, 40)),
        (s, (38, 44)),
        (s, (36, 44)),
        (s, (40, 48)),
        (s, (38, 48)),
        (s, (36, 48)),
        (n, (43, 42)),  # known noop under shallow — retest after vacate
        (n, (43, 40)),
        (s, (42, 48)),
        (s, (44, 48)),
    ]
    ban = {(42, 40), (42, 42), (42, 45), (42, 46), (41, 44), (42, 44), (43, 44)}
    for cur, ld in cands:
        if step_budget(data["frame"]) < 4:
            break
        if ld in ban or ld == cur:
            continue
        if not (0 <= ld[0] < 64 and 0 <= ld[1] < 64):
            continue
        other = s if cur == n else n
        if cheb(ld, other) < 5:
            continue
        if near_any(ld, list(fr15), cheb=5):
            continue
        if ld[1] <= 36 and ld[0] >= 45:
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(
            f"  14 {label} {cur}->{ld} {st}->{newc} ship={me['c']} d14={d14} "
            f"bud={step_budget(data['frame'])}",
            flush=True,
        )
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", flush=True)
            return data, False
        if st == "moved":
            dump(data, "HIT14")
            return data, True
    return data, False


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3vs"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"

    data, ok = boot_to_n438(sess)
    if not ok:
        print("bootfail", flush=True)
        return
    fr15, free = dump(data, "N438")

    # Phase A: push west15 (and maybe east15) further south toward goal
    tgts = [
        (48, 48),
        (48, 50),
        (46, 48),
        (45, 50),
        (42, 50),
        (40, 52),
        (38, 54),
        (36, 52),
        (34, 54),
        (48, 46),
        (50, 48),
        (52, 48),
        (45, 46),
        (42, 48),
        (40, 48),
        (58, 48),
        (58, 50),
        (56, 52),
    ]
    for tgt in tgts:
        if step_budget(data["frame"]) < 6:
            print("bud low stop vacate", flush=True)
            break
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        west = min(flock, key=lambda w: w[0])
        east = max(flock, key=lambda w: w[0])
        # prefer west if tgt is westish, else east
        wp = west if tgt[0] <= 50 else east
        other = east if wp == west else west
        if cheb(tgt, other) < 5:
            print(f"skip merge {wp}->{tgt}", flush=True)
            continue
        if near_any(tgt, list(freeze14), cheb=5):
            print(f"skip near14 {wp}->{tgt}", flush=True)
            continue
        if cheb(tgt, wp) == 0:
            continue
        data, newc, st = move_wp(sess, data, wp, tgt, freeze14)
        print(f"15vac {wp}->{tgt} {st}->{newc} bud={step_budget(data['frame'])}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("15DEAD", flush=True)
            return
        if st != "moved":
            continue
        dump(data, f"after15-{newc}")
        data, hit = try14(sess, data, f"post{newc}")
        if hit:
            print("SUCCESS", flush=True)
            return
        if data.get("state") == "GAME_OVER" or "frame" not in data:
            return

    dump(data, "final")
    print("done no hit", flush=True)


if __name__ == "__main__":
    main()
