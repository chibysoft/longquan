"""From vacW+S6048 pose (d14=25 d15=14 bud≈3): soft-scan last-mile 14/15 moves."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import (
    advance_14_frog_ny_stack,
    clear15_corridor,
    count_free14,
    lock_other_ship,
    near_any,
)
from tools.r11l_seated_clear import clear_l1, reset

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
    return d14, d15


def boot():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_last3"]},
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
    data, ok = advance_14_frog_ny_stack(sess, data, GOAL15)
    return sess, data, ok


# (chrome, tgt) — chrome 14 moves a free14 pad; 15 moves a fr15 pad
CANDS = [
    ("14S", (60, 52)),
    ("14S", (60, 50)),
    ("14S", (55, 53)),
    ("14S", (55, 48)),
    ("14S", (58, 48)),
    ("14S", (62, 48)),
    ("14N", (55, 38)),
    ("14N", (60, 42)),
    ("15E", (48, 56)),
    ("15E", (40, 56)),
    ("15E", (36, 56)),
    ("15E", (34, 57)),
    ("15E", (42, 56)),
    ("15E", (48, 58)),
    ("15E", (52, 56)),
    ("15W", (34, 57)),
    ("15W", (32, 56)),
    ("15W", (30, 56)),
]


def main():
    hits = []
    sess, data, ok = boot()
    if not ok or "frame" not in data:
        print("boot fail", flush=True)
        return
    d14_0, d15_0 = dump(data, "base")
    for label, tgt in CANDS:
        if step_budget(data["frame"]) < 2:
            print("budout — reboot", flush=True)
            sess, data, ok = boot()
            if not ok:
                break
            dump(data, "rebase")
        fr15 = list(lock_other_ship(data["frame"], 14))
        free = count_free14(data["frame"], fr15)
        freeze14 = lock_other_ship(data["frame"], 15)
        if label.startswith("14"):
            if len(free) < 2:
                print(f"  skip {label}{tgt} nfree", flush=True)
                continue
            cur = (
                max(free, key=lambda w: (w[1], w[0]))
                if "S" in label
                else min(free, key=lambda w: (w[1], w[0]))
            )
            other = next(w for w in free if w != cur)
            if max(abs(tgt[0] - other[0]), abs(tgt[1] - other[1])) < 5:
                continue
            if near_any(tgt, fr15, cheb=5):
                continue
            data, newc, st = move_wp(sess, data, cur, tgt, fr15)
        else:
            if not fr15:
                continue
            cur = (
                max(fr15, key=lambda w: w[0])
                if "E" in label
                else min(fr15, key=lambda w: w[0])
            )
            other = next((w for w in fr15 if w != cur), cur)
            if max(abs(tgt[0] - other[0]), abs(tgt[1] - other[1])) < 5:
                continue
            if near_any(tgt, list(freeze14), cheb=5):
                continue
            data, newc, st = move_wp(sess, data, cur, tgt, freeze14)
        print(f"  {label} {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            print("DEAD — reboot", flush=True)
            sess, data, ok = boot()
            if not ok:
                break
            continue
        if st != "moved":
            continue
        d14, d15 = dump(data, f"hit-{label}{tgt}")
        tag = []
        if d14 < d14_0:
            tag.append(f"BEAT14:{d14}")
        if d15 < d15_0:
            tag.append(f"BEAT15:{d15}")
        if (data.get("levels_completed") or 0) >= 3:
            tag.append("PASS")
        print(f"RESULT {' '.join(tag) or 'FLAT'} {label}{tgt}", flush=True)
        hits.append((tag, label, tgt, d14, d15, step_budget(data["frame"])))
        # reboot after success so next cand is from base pose
        sess, data, ok = boot()
        if not ok:
            break
        dump(data, "rebase")

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)


if __name__ == "__main__":
    main()
