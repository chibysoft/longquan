"""After mid refill at ~ui84, go to (1,2) then UP into (1,1) — avoid (2,1) LEFT."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import mover_bbox_from_cursor
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import RITUAL, MAX_FUEL, _energy_bfs, _ov, plan_two_phase
from tools.ls20_seated_clear_full import (
    _plan_to_pickup, _plan_to_unlock, _sync_after_levelup, _unlock_candidates,
)
from tools.ls20_l4_stamp9_probe import stamp9


def boot(sess):
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


def bfs_to(frame, goal, armed=True):
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
        sess.open(tags=["ls20_l4_via12_up"])
        frame, meta = boot(sess)
        print("pu", ls20.energy_pickups(frame))
        for _ in range(25):
            p, _, _, _ = bfs_to(frame, (4, 7), armed=False)
            if not p or len(p) == 0:
                break
            resp = sess.action(DIR_TO_ACTION[p[0]])
            frame, meta = resp["frame"], resp
            if ls20.init(frame).cursor == (4, 7):
                break
        for a in RITUAL:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
        # mid fuel to (3,3)
        for _ in range(20):
            mid = [p for p in ls20.energy_pickups(frame) if p[1] < 40]
            if not mid or ls20.ui_energy(frame) >= 70:
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
            print("fuel", ls20.init(frame).cursor, ls20.ui_energy(frame))
        print("fueled at", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        # go to (1,2)
        for i in range(20):
            p, _, _, _ = bfs_to(frame, (1, 2), armed=True)
            if not p:
                print("no path to 12", ls20.init(frame).cursor)
                break
            if len(p) == 0:
                break
            resp = sess.action(DIR_TO_ACTION[p[0]])
            frame, meta = resp["frame"], resp
            print(f"to12 {i}", ls20.init(frame).cursor, ls20.ui_energy(frame))
            if ls20.init(frame).cursor == (1, 2):
                break
            if ls20.init(frame).cursor == (2, 1):
                print("avoided? landed 21 — go back")
                resp = sess.action(4)  # R away
                frame, meta = resp["frame"], resp
        cur = ls20.init(frame).cursor
        print("try UP from", cur)
        resp = sess.action(1)
        frame, meta = resp["frame"], resp
        print("after U", ls20.init(frame).cursor, "lv", meta.get("levels_completed"),
              "s9", stamp9(frame)[0], "ui", ls20.ui_energy(frame))
        if int(meta.get("levels_completed") or 0) < 4:
            resp = sess.action(3)
            print("after L", ls20.init(resp["frame"]).cursor, resp.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
