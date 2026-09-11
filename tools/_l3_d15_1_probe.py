"""From d15=1 pose (after fin15w): clear last step to goal15 / improve d14."""
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
from tools._l3_savebud_probe import deep15, se_to_n6038, do_s6048, do_fin15, dump, move15, move14

GOAL14, GOAL15 = (55, 53), (34, 57)


def boot_to_d15_1(*, do_s60: bool):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_d15_1"]},
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
    data, ok = deep15(sess, data, do_east15b=False, early_tgt=(40, 56))
    if not ok:
        return sess, data, False
    data, ok = se_to_n6038(sess, data)
    if not ok:
        return sess, data, False
    if do_s60:
        data, ok = do_s6048(sess, data)
        if not ok:
            return sess, data, False
    data, _ = do_fin15(sess, data)
    # fin15w
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    data, st = move15(sess, data, west, (28, 56))
    if st != "moved":
        data, st = move15(sess, data, west, (30, 56))
    if st != "moved":
        return sess, data, False
    dump(data, "d15_1")
    return sess, data, True


CANDS = [
    # 15 pads: expect ~ (28,56)+(40,56), ship@(34,56)
    ("15R", (34, 57)),
    ("15R", (40, 57)),
    ("15R", (34, 56)),
    ("15R", (36, 57)),
    ("15R", (38, 57)),
    ("15R", (42, 57)),
    ("15L", (34, 57)),
    ("15L", (28, 57)),
    ("15L", (32, 57)),
    ("15L", (34, 56)),
    ("15L", (26, 57)),
    ("14S", (60, 50)),
    ("14S", (60, 52)),
    ("14S", (55, 53)),
    ("14S", (60, 48)),
    ("14N", (55, 38)),
]


def main():
    hits = []
    for do_s60 in (False, True):  # prefer bud=4 path first
        print(f"\n##### s60={do_s60} #####", flush=True)
        for label, tgt in CANDS:
            sess, data, ok = boot_to_d15_1(do_s60=do_s60)
            if not ok:
                print("boot fail", flush=True)
                continue
            d14_0 = abs(next(s["c"][0] for s in ships(data["frame"]) if s["chrome"] == 14) - 55) + abs(
                next(s["c"][1] for s in ships(data["frame"]) if s["chrome"] == 14) - 53
            )
            d15_0 = abs(next(s["c"][0] for s in ships(data["frame"]) if s["chrome"] == 15) - 34) + abs(
                next(s["c"][1] for s in ships(data["frame"]) if s["chrome"] == 15) - 57
            )
            fr15 = list(lock_other_ship(data["frame"], 14))
            free = count_free14(data["frame"], fr15)
            freeze14 = lock_other_ship(data["frame"], 15)
            if label.startswith("14"):
                if len(free) < 2 or step_budget(data["frame"]) < 2:
                    continue
                cur = (
                    max(free, key=lambda w: (w[1], w[0]))
                    if "S" in label
                    else min(free, key=lambda w: (w[1], w[0]))
                )
                other = next(w for w in free if w != cur)
                if max(abs(tgt[0] - other[0]), abs(tgt[1] - other[1])) < 5:
                    print(f"  skip {label}{tgt} merge", flush=True)
                    continue
                if near_any(tgt, fr15, cheb=5):
                    print(f"  skip {label}{tgt} near15", flush=True)
                    continue
                data, newc, st = move_wp(sess, data, cur, tgt, fr15)
            else:
                if not fr15 or step_budget(data["frame"]) < 2:
                    continue
                cur = max(fr15, key=lambda w: w[0]) if "R" in label else min(fr15, key=lambda w: w[0])
                other = next((w for w in fr15 if w != cur), cur)
                if max(abs(tgt[0] - other[0]), abs(tgt[1] - other[1])) < 5:
                    print(f"  skip {label}{tgt} merge other={other}", flush=True)
                    continue
                if near_any(tgt, list(freeze14), cheb=5):
                    print(f"  skip {label}{tgt} near14", flush=True)
                    continue
                data, newc, st = move_wp(sess, data, cur, tgt, freeze14)
            print(
                f"  {label} {cur}->{tgt} {st}->{newc} "
                f"bud={step_budget(data['frame']) if 'frame' in data else '?'}",
                flush=True,
            )
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                print("DEAD", flush=True)
                continue
            if st != "moved":
                continue
            me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
            d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
            d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
            tags = []
            if d15 == 0:
                tags.append("D15CLEAR")
            elif d15 < d15_0:
                tags.append(f"BEAT15:{d15}")
            if d14 < d14_0:
                tags.append(f"BEAT14:{d14}")
            if (data.get("levels_completed") or 0) >= 3:
                tags.append("PASS")
            dump(data, f"hit-{label}{tgt}")
            print(f"RESULT {' '.join(tags) or 'LIVE'} {label}{tgt} d14={d14} d15={d15}", flush=True)
            hits.append((do_s60, label, tgt, tags, d14, d15, step_budget(data["frame"])))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)


if __name__ == "__main__":
    main()
