"""Early haul15 after mid-east / after deep15 — free ship15 off (50,50) before SE."""
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
    haul15_toward,
    lock_other_ship,
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
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )


def boot_l2():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_haul32"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    data, _ = advance_14_mid_east(sess, data, data.get("levels_completed") or 0, do_clear15=False)
    dump(data, "mid")
    return sess, data


def deep15(sess, data):
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, _ = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, _ = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, _ = move_wp(
        sess, data, max(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (58, 50), freeze14
    )
    dump(data, "deep15")
    return data


def vac15_south(sess, data, tgts):
    """Move west15 further south/west to drag ship15 off (50,50)."""
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    if not flock:
        return data, False
    west = min(flock, key=lambda w: w[0])
    east = max(flock, key=lambda w: w[0])
    for tgt in tgts:
        if max(abs(tgt[0] - east[0]), abs(tgt[1] - east[1])) < 5:
            continue
        if step_budget(data["frame"]) < 4:
            break
        data, newc, st = move_wp(sess, data, west, tgt, freeze14)
        print(f"  vac15 {west}->{tgt} {st}->{newc} bud={step_budget(data['frame'])}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            return data, False
        if st == "moved":
            dump(data, "after-vac")
            return data, True
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        west = min(flock, key=lambda w: w[0])
        east = max(flock, key=lambda w: w[0])
    return data, False


def main():
    plans = [
        ("A haul@mid then deep+seny", "mid_haul"),
        ("B deep then vac4254 then seny", "deep_vac"),
        ("C deep then haul then seny", "deep_haul"),
        ("D baseline seny only", "base"),
    ]
    for name, kind in plans:
        print(f"\n===== {name} =====", flush=True)
        sess, data = boot_l2()
        if kind == "mid_haul":
            data, ok = haul15_toward(sess, data, (34, 57), max_step=6, label="midhaul")
            print(f"  haul ok={ok}", flush=True)
            dump(data, "after-haul")
            data, ok = advance_14_frog_ny_stack(sess, data, (34, 57))
            print(f"  seny ok={ok}", flush=True)
            dump(data, "FINAL")
        elif kind == "deep_vac":
            data = deep15(sess, data)
            data, _ = vac15_south(sess, data, ((42, 54), (38, 52), (40, 56), (36, 54), (48, 54)))
            data, ok = advance_14_frog_ny_stack(sess, data, (34, 57))
            print(f"  seny ok={ok}", flush=True)
            dump(data, "FINAL")
        elif kind == "deep_haul":
            data = deep15(sess, data)
            data, ok = haul15_toward(sess, data, (34, 57), max_step=6, label="deephaul")
            print(f"  haul ok={ok}", flush=True)
            dump(data, "after-haul")
            data, ok = advance_14_frog_ny_stack(sess, data, (34, 57))
            print(f"  seny ok={ok}", flush=True)
            dump(data, "FINAL")
        else:
            data, ok = advance_14_frog_ny_stack(sess, data, (34, 57))
            print(f"  seny ok={ok}", flush=True)
            dump(data, "FINAL")


if __name__ == "__main__":
    main()
