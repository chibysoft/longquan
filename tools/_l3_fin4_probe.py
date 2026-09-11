"""Soft-scan finish from skip-e54 pose (d14=25 d15=4 bud≈3|6)."""
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
from tools._l3_savebud_probe import deep15, se_to_n6038, do_s6048, do_fin15, dump

GOAL14, GOAL15 = (55, 53), (34, 57)


def boot(skip_e54=True, do_s60=True):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_fin4"]},
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
    data, ok = deep15(sess, data, do_east15b=not skip_e54, early_tgt=(40, 56))
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
    dump(data, "base")
    return sess, data, True


# (label, chrome15|14, who/pad-selector, tgt)
# 15L = min x, 15R = max x, 15F = farthest from goal
CANDS = [
    ("15F-3457", "15F", (34, 57)),
    ("15F-3757", "15F", (37, 57)),
    ("15F-3456", "15F", (34, 56)),
    ("15F-3657", "15F", (36, 57)),
    ("15R-3457", "15R", (34, 57)),
    ("15R-3757", "15R", (37, 57)),
    ("15R-3455", "15R", (34, 55)),
    ("15L-3457", "15L", (34, 57)),
    ("15L-3455", "15L", (34, 55)),
    ("15L-3257", "15L", (32, 57)),
    ("15R-4157", "15R", (41, 57)),
    ("15R-3856", "15R", (38, 56)),
    ("14S-6050", "14S", (60, 50)),
    ("14S-6052", "14S", (60, 52)),
    ("14S-5553", "14S", (55, 53)),
    ("14N-5538", "14N", (55, 38)),
]


def pick15(flock, mode):
    if mode == "15L":
        return min(flock, key=lambda w: w[0])
    if mode == "15R":
        return max(flock, key=lambda w: w[0])
    return max(flock, key=lambda w: abs(w[0] - GOAL15[0]) + abs(w[1] - GOAL15[1]))


def main():
    hits = []
    soft = []
    # Prefer skip-both for more bud if we want; start with skip-e54 (d14=25)
    for mode_name, skip_e54, do_s60 in (
        ("skip-e54", True, True),
        ("skip-both", True, False),
    ):
        print(f"\n##### MODE {mode_name} #####", flush=True)
        sess, data, ok = boot(skip_e54=skip_e54, do_s60=do_s60)
        if not ok:
            print("boot fail", flush=True)
            continue
        d14_0, d15_0, _, _ = dump(data, "scan-base")
        for label, mode, tgt in CANDS:
            if "frame" not in data or step_budget(data["frame"]) < 2:
                print("budout reboot", flush=True)
                sess, data, ok = boot(skip_e54=skip_e54, do_s60=do_s60)
                if not ok:
                    break
                d14_0, d15_0, _, _ = dump(data, "rebase")
            fr15 = list(lock_other_ship(data["frame"], 14))
            free = count_free14(data["frame"], fr15)
            freeze14 = lock_other_ship(data["frame"], 15)
            if mode.startswith("14"):
                if len(free) < 2:
                    continue
                cur = (
                    max(free, key=lambda w: (w[1], w[0]))
                    if "S" in mode
                    else min(free, key=lambda w: (w[1], w[0]))
                )
                other = next(w for w in free if w != cur)
                if max(abs(tgt[0] - other[0]), abs(tgt[1] - other[1])) < 5:
                    soft.append((mode_name, label, "merge"))
                    continue
                if near_any(tgt, fr15, cheb=5):
                    soft.append((mode_name, label, "near15"))
                    continue
                data, newc, st = move_wp(sess, data, cur, tgt, fr15)
            else:
                if not fr15:
                    continue
                cur = pick15(fr15, mode)
                other = next((w for w in fr15 if w != cur), cur)
                if max(abs(tgt[0] - other[0]), abs(tgt[1] - other[1])) < 5:
                    soft.append((mode_name, label, "merge"))
                    continue
                if near_any(tgt, list(freeze14), cheb=5):
                    soft.append((mode_name, label, "near15"))
                    continue
                if max(abs(tgt[0] - cur[0]), abs(tgt[1] - cur[1])) <= 1:
                    continue
                data, newc, st = move_wp(sess, data, cur, tgt, freeze14)
            print(
                f"  {label} {cur}->{tgt} {st}->{newc} "
                f"bud={step_budget(data['frame']) if 'frame' in data else '?'}",
                flush=True,
            )
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                print("DEAD reboot", flush=True)
                soft.append((mode_name, label, "dead"))
                sess, data, ok = boot(skip_e54=skip_e54, do_s60=do_s60)
                if not ok:
                    break
                continue
            if st != "moved":
                soft.append((mode_name, label, st))
                continue
            me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
            d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
            d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
            tags = []
            if d15 < d15_0:
                tags.append(f"BEAT15:{d15}")
            if d14 < d14_0:
                tags.append(f"BEAT14:{d14}")
            if d15 == 0:
                tags.append("D15CLEAR")
            if d14 == 0:
                tags.append("D14CLEAR")
            if (data.get("levels_completed") or 0) >= 3:
                tags.append("PASS")
            print(
                f"RESULT {' '.join(tags) or 'LIVE'} {mode_name}/{label} "
                f"d14={d14} d15={d15} bud={step_budget(data['frame'])}",
                flush=True,
            )
            hits.append((mode_name, label, tags, d14, d15, step_budget(data["frame"])))
            sess, data, ok = boot(skip_e54=skip_e54, do_s60=do_s60)
            if not ok:
                break
            d14_0, d15_0, _, _ = dump(data, "rebase")

    print("\n===== SOFT dead =====", flush=True)
    for s in soft:
        if s[2] == "dead":
            print(s, flush=True)
    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)


if __name__ == "__main__":
    main()
