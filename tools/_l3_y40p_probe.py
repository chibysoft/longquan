"""Y40 pose: short priority SE/east scan (fresh boot each)."""
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


def boot_y40():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_y40p"]},
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
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    if st == "dead":
        return sess, data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    if st == "dead":
        return sess, data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, max(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (58, 50), freeze14
    )
    if st == "dead":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    if st != "moved":
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    for gd in ((lag[0] + 2, lead[1]), (lag[0] + 4, lead[1]), (lead[0] - 6, lead[1])):
        if cheb(gd, lead) < 5 or near_any(gd, list(fr15), cheb=5):
            continue
        data, _, st = move_wp(sess, data, lag, gd, fr15)
        if st == "moved":
            dump(data, "Y40")
            return sess, data, True
        if st == "dead":
            return sess, data, False
    return sess, data, False


# Priority: lead SE first (beat frog needs SE progress), then lag frog-alts
CANDS = [
    # lead east / SE from ~(33,40)
    ("L", (38, 40)),
    ("L", (40, 40)),
    ("L", (42, 40)),
    ("L", (36, 42)),
    ("L", (38, 42)),
    ("L", (40, 42)),
    ("L", (42, 42)),
    ("L", (44, 42)),
    ("L", (38, 44)),
    ("L", (40, 44)),
    ("L", (42, 44)),
    ("L", (44, 44)),
    ("L", (46, 44)),
    ("L", (48, 42)),
    ("L", (48, 44)),
    ("L", (40, 46)),
    ("L", (44, 46)),
    ("L", (48, 46)),
    ("L", (36, 44)),
    ("L", (34, 44)),
    # lag south / SE from ~(24,40) — frog-like without Ny
    ("G", (26, 44)),
    ("G", (28, 44)),
    ("G", (30, 44)),
    ("G", (32, 44)),
    ("G", (28, 42)),
    ("G", (30, 42)),
    ("G", (26, 46)),
    ("G", (30, 46)),
    ("G", (34, 44)),
    ("G", (36, 44)),
]


def main():
    hits = []
    for who, tgt in CANDS:
        print(f"\n===== {who} ->{tgt} =====", flush=True)
        sess, data, ok = boot_y40()
        if not ok or data.get("state") == "GAME_OVER":
            print("boot fail", flush=True)
            continue
        d0, free, fr15 = dump(data, "base")
        if len(free) != 2:
            continue
        lead = max(free, key=lambda w: w[0])
        lag = min(free, key=lambda w: w[0])
        cur = lead if who == "L" else lag
        other = lag if who == "L" else lead
        if cheb(tgt, other) < 5:
            print("merge", flush=True)
            continue
        if near_any(tgt, list(fr15), cheb=5):
            print("near15", flush=True)
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
        print(f"{tag} d14 {d0}->{d1} bud={step_budget(data['frame'])}", flush=True)
        if d1 < d0:
            hits.append((who, cur, newc, d0, d1, step_budget(data["frame"]), free1))
            # chain: try Ny-style north park then SE like frog, OR more SE
            lead2 = max(free1, key=lambda w: (w[1], w[0]))
            north = min(free1, key=lambda w: (w[1], w[0]))
            south = max(free1, key=lambda w: (w[1], w[0]))
            follow = []
            if who == "G":
                # after frog-ish, try Ny36 then S4842 / Ne (known) vs alts
                follow = [
                    (north, (40, 36)),
                    (north, (38, 36)),
                    (north, (42, 38)),
                    (south, (40, 44)),
                    (south, (48, 42)),
                ]
            else:
                follow = [
                    (lead2, (lead2[0] + 4, lead2[1])),
                    (lead2, (lead2[0] + 4, lead2[1] + 2)),
                    (lead2, (48, 42)),
                    (lead2, (44, 46)),
                    (min(free1, key=lambda w: w[0]), (min(free1)[0] + 4, min(free1)[1] + 4)),
                ]
            for src, t2 in follow:
                oth = [w for w in free1 if w != src]
                if any(cheb(t2, o) < 5 for o in oth):
                    continue
                if near_any(t2, list(fr151), cheb=5):
                    continue
                data, nc2, st2 = move_wp(sess, data, src, t2, fr151)
                print(f"  hop2 {src}->{t2} {st2}->{nc2}", flush=True)
                if st2 == "dead" or data.get("state") == "GAME_OVER":
                    break
                if st2 != "moved":
                    continue
                d2, free2, fr152 = dump(data, "hop2")
                if len(free2) == 2 and d2 < d1:
                    print(
                        f"HOP2 IMPROVED d14 {d1}->{d2} bud={step_budget(data['frame'])}",
                        flush=True,
                    )
                    hits.append(("H2", src, nc2, d1, d2, step_budget(data["frame"]), free2))
                    d1 = d2
                    free1 = free2
                    fr151 = fr152
                elif len(free2) != 2:
                    print("FLOCK hop2", flush=True)
                    break

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    if not hits:
        print("none", flush=True)


if __name__ == "__main__":
    main()
