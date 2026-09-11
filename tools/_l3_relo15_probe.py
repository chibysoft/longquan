"""After early-dock: relocate chrome15 pads to unseal 14 approach, then SE."""
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
from tools._l3_savebud_probe import deep15, do_fin15, dump, move14, se_to_n6038

GOAL14, GOAL15 = (55, 53), (34, 57)

# (which pad, tgt) — E=eastmost, W=westmost
RELOS = [
    ("E4062", "E", (40, 62)),
    ("E4862", "E", (48, 62)),
    ("E4860", "E", (48, 60)),
    ("E3462", "E", (34, 62)),
    ("E4464", "E", (44, 64)),
    ("W2060", "W", (20, 60)),
    ("W2458", "W", (24, 58)),
    ("W2862", "W", (28, 62)),
    ("E40_W20", "both", [(40, 62), (20, 58)]),
    ("E48_W24", "both", [(48, 60), (24, 58)]),
]


def boot_docked():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_relo15"]},
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
    data, _ = do_fin15(sess, data)
    freeze14 = lock_other_ship(data["frame"], 15)
    west = min(lock_other_ship(data["frame"], 14), key=lambda w: w[0])
    data, _, st = move_wp(sess, data, west, (28, 58), freeze14)
    if st != "moved":
        return sess, data, False
    dump(data, "docked")
    return sess, data, True


def score(data):
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
    d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
    return me14["c"], me15["c"], d14, d15, step_budget(data["frame"])


def move15_role(sess, data, role, tgt):
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    cur = max(flock, key=lambda w: w[0]) if role == "E" else min(flock, key=lambda w: w[0])
    other = next(w for w in flock if w != cur)
    if max(abs(tgt[0] - other[0]), abs(tgt[1] - other[1])) < 5:
        return data, "merge"
    if near_any(tgt, list(freeze14), cheb=5):
        return data, "near14"
    data, newc, st = move_wp(sess, data, cur, tgt, freeze14)
    print(f"  relo15 {cur}->{tgt} {st}->{newc}", flush=True)
    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, "dead"
    return data, st


def main():
    hits = []
    for name, role, tgt in RELOS:
        print(f"\n===== {name} =====", flush=True)
        sess, data, ok = boot_docked()
        if not ok:
            print("boot fail", flush=True)
            continue
        if role == "both":
            # tgt is list [east_tgt, west_tgt]
            data, st = move15_role(sess, data, "E", tgt[0])
            if st != "moved":
                print(f"SOFT E {st}", flush=True)
                continue
            _, _, _, d15, _ = score(data)
            if d15 > 0:
                print(f"LOST15 after E d15={d15}", flush=True)
                continue
            data, st = move15_role(sess, data, "W", tgt[1])
            if st != "moved":
                print(f"SOFT W {st}", flush=True)
                continue
        else:
            data, st = move15_role(sess, data, role, tgt)
            if st != "moved":
                print(f"SOFT {st}", flush=True)
                continue
        ship14, ship15, d14, d15, bud = score(data)
        print(f"  after-relo ship15={ship15} d15={d15} bud={bud}", flush=True)
        if d15 > 0:
            print("LOST15", flush=True)
            continue
        # SE + optional S6048
        data, ok = se_to_n6038(sess, data)
        dump(data, "after-SE")
        if "frame" not in data:
            continue
        ship14, ship15, d14, d15, bud = score(data)
        # try goalish S from leftover
        if bud >= 2 and d15 == 0:
            for who, stgt in (("S", (60, 48)), ("S", (55, 53)), ("S", (52, 50)), ("N", (55, 50))):
                if step_budget(data["frame"]) < 2:
                    break
                before = d14
                data, st = move14(sess, data, who, stgt)
                if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                    print(f"DEAD pull {stgt}", flush=True)
                    break
                if st != "moved":
                    continue
                ship14, ship15, d14, d15, bud = score(data)
                print(f"  pull {who}{stgt} d14 {before}->{d14} bud={bud}", flush=True)
                if d15 > 0:
                    print("LOST15 on pull", flush=True)
                    break
        ship14, ship15, d14, d15, bud = score(data) if "frame" in data else (None, None, 99, 99, 0)
        tags = []
        if d15 == 0:
            tags.append("d15=0")
        if d14 < 26:
            tags.append(f"BEAT:{d14}")
        if (data.get("levels_completed") or 0) >= 3:
            tags.append("PASS")
        print(
            f"RESULT {' '.join(tags) or 'LIVE'} {name} "
            f"ship14={ship14} d14={d14} d15={d15} bud={bud}",
            flush=True,
        )
        hits.append((d14, -bud, name, ship14, d15))
    print("\n===== BEST =====", flush=True)
    for h in sorted(hits)[:10]:
        print(h, flush=True)


if __name__ == "__main__":
    main()
