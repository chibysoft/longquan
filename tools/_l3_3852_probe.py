"""(42,50)->(38,52) then frog no-N; scan 14 exits with more bud."""
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


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me['c']} d14={d14} free={sorted(free)} "
        f"d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_3852"]},
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
    d0 = dump(data, f"frog-ok={ok}")
    if data.get("state") == "GAME_OVER" or "frame" not in data:
        print("GO", flush=True)
        return
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        print("n<2", free, flush=True)
        return
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    cands = [
        (s, (40, 46)),
        (s, (42, 46)),
        (s, (38, 46)),
        (s, (40, 48)),
        (s, (42, 48)),
        (n, (45, 40)),
        (n, (46, 40)),
        (n, (44, 38)),
        (n, (46, 38)),
    ]
    if n != (43, 38):
        cands.insert(5, (n, (43, 38)))
    else:
        cands.insert(5, (n, (44, 40)))
    for cur, ld in cands:
        if step_budget(data["frame"]) < 4:
            break
        if near_any(ld, list(fr15), cheb=5):
            print(f"skip near15 {ld}", flush=True)
            continue
        other = s if cur == n else n
        if max(abs(ld[0] - other[0]), abs(ld[1] - other[1])) < 5:
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(
            f"  {cur}->{ld} {st}->{newc} ship={me['c']} d14={d14}({d14-d0:+d}) "
            f"bud={step_budget(data['frame'])}",
            flush=True,
        )
        if st == "dead":
            print("DEAD", flush=True)
            return
        if st == "moved":
            dump(data, "HIT")
            print("SUCCESS", flush=True)
            return
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) < 2:
            break
        s = max(free, key=lambda w: (w[1], w[0]))
        n = min(free, key=lambda w: (w[1], w[0]))
    dump(data, "end")
    print("done", flush=True)


if __name__ == "__main__":
    main()
