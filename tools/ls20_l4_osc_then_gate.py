"""Preserve mid pickup; osc ring 8x; UDD from 47; mid fuel; LEFT at (2,1) ui~74."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import RITUAL, MAX_FUEL, _energy_bfs, plan_two_phase
from tools.ls20_seated_clear_full import (
    _plan_to_pickup, _plan_to_unlock, _sync_after_levelup, _unlock_candidates,
    _plan_armed_stamp_only,
)
from tools.ls20_l4_stamp9_probe import stamp9
from longquan.interactive.match import mover_bbox_from_cursor
from tools.ls20_seated_clear import _ov


def boot_to_l4_unlock_keep_mid(sess):
    resp = sess.reset()
    frame, meta = resp["frame"], resp
    while int(meta.get("levels_completed") or 0) < 3:
        lv = int(meta.get("levels_completed") or 0)
        for cand in _unlock_candidates(frame):
            p_pu, _ = _plan_to_pickup(frame, bottom_only=True)
            if p_pu:
                for a in p_pu:
                    resp = sess.action(DIR_TO_ACTION[a])
                    frame, meta = resp["frame"], resp
            p, _, _ = _plan_to_unlock(frame, cand)
            if p:
                for a in p:
                    resp = sess.action(DIR_TO_ACTION[a])
                    frame, meta = resp["frame"], resp
        path, _ = plan_two_phase(frame)
        for a in path:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            if int(meta.get("levels_completed") or 0) > lv:
                break
        frame, meta = _sync_after_levelup(sess, frame)
    p_pu, _ = _plan_to_pickup(frame, bottom_only=True)
    if p_pu:
        for a in p_pu:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
    p, _, _ = _plan_to_unlock(frame, (6, 6))
    for a in p:
        resp = sess.action(DIR_TO_ACTION[a])
        frame, meta = resp["frame"], resp
    return frame, meta


def plan_to(frame, goal, armed=False):
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk = ls20.build_walkable(frame, offset, armed=armed)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))
    return _energy_bfs(state.cursor, fuel0, 0, walk, pickups, offset,
                       lambda c, _f, _p: c == goal, warps)


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_osc_then_gate"])
        frame, meta = boot_to_l4_unlock_keep_mid(sess)
        print("unlock", ls20.init(frame).cursor, "pu", ls20.energy_pickups(frame))
        for i in range(8):
            cur = ls20.init(frame).cursor
            aid = 1 if cur[1] >= 6 else 2
            resp = sess.action(aid)
            frame, meta = resp["frame"], resp
            print(f"osc{i}", ls20.init(frame).cursor, ls20.energy_pickups(frame))
        for _ in range(30):
            p, _, _, _ = plan_to(frame, (4, 7), armed=False)
            if not p or len(p) == 0:
                break
            resp = sess.action(DIR_TO_ACTION[p[0]])
            frame, meta = resp["frame"], resp
            if ls20.init(frame).cursor == (4, 7):
                break
        for a in RITUAL:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
        print("after H23", ls20.init(frame).cursor, "carry", ls20.init(frame).carrying)
        # mid fuel
        mid = [p for p in ls20.energy_pickups(frame) if p[1] < 40]
        for _ in range(20):
            if ls20.ui_energy(frame) >= 70 or not mid:
                break
            offset = ls20.grid_offset(frame)
            walk_a = ls20.build_walkable(frame, offset, armed=True)
            walk_u = ls20.build_walkable(frame, offset, armed=False)
            warps = ls20.detect_warps(frame, offset, walk_u)
            ui = ls20.ui_energy(frame)
            fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))
            p, _, _, _ = _energy_bfs(
                ls20.init(frame).cursor, fuel0, 0, walk_a, mid, offset,
                lambda c, _f, _p: any(_ov(mover_bbox_from_cursor(c, offset), pb) > 0 for pb in mid),
                warps,
            )
            if not p:
                break
            resp = sess.action(DIR_TO_ACTION[p[0]])
            frame, meta = resp["frame"], resp
            mid = [x for x in ls20.energy_pickups(frame) if x[1] < 40]
            print("fuel", ls20.init(frame).cursor, ls20.ui_energy(frame))
        for i in range(12):
            path, _, _, _ = _plan_armed_stamp_only(frame)
            if not path:
                break
            before = ls20.init(frame).cursor
            resp = sess.action(DIR_TO_ACTION[path[0]])
            frame, meta = resp["frame"], resp
            after = ls20.init(frame).cursor
            import numpy as np
            arr = np.asarray(frame)
            print(f"{i+1} {before}->{after} ui={ls20.ui_energy(frame)} "
                  f"s9={stamp9(frame)[0]} layers={arr.shape[0] if arr.ndim==3 else 1} "
                  f"lv={meta.get('levels_completed')} carry={ls20.init(frame).carrying}")
            if int(meta.get("levels_completed") or 0) >= 4:
                print("CLEARED")
                return
            if after == before == (2, 1):
                # try LEFT twice more
                for t in range(3):
                    r = sess.action(3)
                    frame, meta = r["frame"], r
                    print(f"extraL{t}", ls20.init(frame).cursor, meta.get("levels_completed"),
                          "layers", np.asarray(frame).shape)
                break
        print("FAIL", ls20.init(frame).cursor, ls20.ui_energy(frame))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
