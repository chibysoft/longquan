"""From N43: try SOUTH first; avoid N≥47 on y36."""
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

DEAD = {(45, 36), (46, 36), (47, 36), (48, 36), (48, 46), (27, 40), (28, 40), (38, 44)}


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    print(
        f"{label} ship={me['c']} d14={d14} free={sorted(free)} n={len(free)} "
        f"bud={step_budget(data['frame'])}"
    )
    return fr15, free, me


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3south"]},
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
    data, ok = advance_14_frog_ny_stack(sess, data, (34, 57))
    dump(data, "N43")
    if not ok:
        return

    fr15, free, me = dump(data, "try")
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    # SOUTH / SE first
    cands = [
        (s, (s[0], s[1] + 2), "Ss2"),
        (s, (s[0], s[1] + 4), "Ss4"),
        (s, (s[0], s[1] + 6), "Ss6"),
        (s, (s[0] + 2, s[1] + 2), "Sse"),
        (s, (s[0] + 2, s[1] + 4), "Sse"),
        (s, (s[0] + 4, s[1] + 2), "Sse"),
        (s, (40, 48), "S48"),
        (s, (40, 50), "S50"),
        (s, (42, 48), "S42_48"),
        (n, (n[0], n[1] + 2), "Ns2"),
        (n, (n[0], n[1] + 4), "Ns4"),
        (n, (43, 40), "N40"),
        (n, (44, 38), "N38"),
        (n, (42, 38), "N38"),
        (n, (44, 36), "N44"),
        (n, (n[0] + 1, n[1]), "Ne1"),
    ]
    for cur, ld, lab in cands:
        if ld in DEAD:
            print(f"  skip dead {ld}")
            continue
        other = s if cur == n else n
        if cheb(ld, other) < 5:
            print(f"  skip merge {ld}")
            continue
        if near_any(ld, list(fr15), cheb=5):
            print(f"  near15 {ld}")
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        print(f"  {lab} {cur}->{ld} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", ld)
            return
        if st == "moved":
            dump(data, "HIT")
            return
    print("none")


if __name__ == "__main__":
    main()
