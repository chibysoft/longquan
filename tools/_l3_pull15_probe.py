"""d15=1 bud=4: pull ship15 south onto (34,57) via y>=57 pads."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import clear15_corridor, lock_other_ship, near_any
from tools.r11l_seated_clear import clear_l1, reset
from tools._l3_savebud_probe import deep15, se_to_n6038, do_fin15, dump, move15
from tools._l3_d15_1_probe import boot_to_d15_1

GOAL14, GOAL15 = (55, 53), (34, 57)

# Explicit south/goal pulls from (28,56) or (40,56)
CANDS = [
    ("R", (40, 57)),
    ("R", (40, 58)),
    ("R", (34, 58)),
    ("R", (34, 59)),
    ("R", (36, 58)),
    ("R", (38, 58)),
    ("R", (42, 57)),
    ("R", (42, 58)),
    ("L", (28, 57)),
    ("L", (28, 58)),
    ("L", (34, 58)),
    ("L", (32, 58)),
    ("L", (26, 57)),
    ("L", (30, 58)),
    ("R", (48, 57)),
    ("L", (20, 57)),
]


def main():
    hits = []
    for who, tgt in CANDS:
        sess, data, ok = boot_to_d15_1(do_s60=False)  # bud≈4
        if not ok:
            print("boot fail", flush=True)
            continue
        dump(data, "base")
        fr15 = list(lock_other_ship(data["frame"], 14))
        freeze14 = lock_other_ship(data["frame"], 15)
        cur = max(fr15, key=lambda w: w[0]) if who == "R" else min(fr15, key=lambda w: w[0])
        other = next((w for w in fr15 if w != cur), cur)
        if max(abs(tgt[0] - other[0]), abs(tgt[1] - other[1])) < 5:
            print(f"  skip {who} {cur}->{tgt} merge", flush=True)
            continue
        if near_any(tgt, list(freeze14), cheb=5):
            print(f"  skip {who} {cur}->{tgt} near14", flush=True)
            continue
        data, newc, st = move_wp(sess, data, cur, tgt, freeze14)
        print(
            f"  {who} {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}",
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
        elif d15 < 1:
            tags.append(f"BEAT15:{d15}")
        if me15["c"] == GOAL15:
            tags.append("SHIP_ON_GOAL")
        if (data.get("levels_completed") or 0) >= 3:
            tags.append("PASS")
        dump(data, f"hit-{tgt}")
        print(
            f"RESULT {' '.join(tags) or 'LIVE'} {who}{tgt} "
            f"ship15={me15['c']} d14={d14} d15={d15}",
            flush=True,
        )
        hits.append((who, tgt, tags, me15["c"], d14, d15, step_budget(data["frame"])))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    clears = [h for h in hits if "D15CLEAR" in h[2] or "PASS" in h[2] or "SHIP_ON_GOAL" in h[2]]
    print("CLEARS", clears or "none", flush=True)


if __name__ == "__main__":
    main()
