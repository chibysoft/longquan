"""Verify unlock at (6,6), oscillate N times, H23, mid-fuel, try gate LEFT."""
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


def advance_to_l4(sess):
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
    return frame, meta


def go(frame, sess, meta, goal, armed=True, limit=40):
    for _ in range(limit):
        cur = ls20.init(frame).cursor
        if cur == goal:
            return frame, meta, True
        offset = ls20.grid_offset(frame)
        walk = ls20.build_walkable(frame, offset, armed=armed)
        walk_u = ls20.build_walkable(frame, offset, armed=False)
        warps = ls20.detect_warps(frame, offset, walk_u)
        pickups = ls20.energy_pickups(frame)
        ui = ls20.ui_energy(frame)
        fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))
        p, _, _, _ = _energy_bfs(
            cur, fuel0, 0, walk, pickups, offset,
            lambda c, _f, _p: c == goal, warps,
        )
        if not p:
            p, _, _, _ = _energy_bfs(
                cur, fuel0, 0, walk_u, pickups, offset,
                lambda c, _f, _p: c == goal, warps,
            )
        if not p:
            return frame, meta, False
        resp = sess.action(DIR_TO_ACTION[p[0]])
        frame, meta = resp["frame"], resp
        if int(meta.get("levels_completed") or 0) >= 4:
            return frame, meta, True
    return frame, meta, ls20.init(frame).cursor == goal


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_osc8_gate"])
        frame, meta = advance_to_l4(sess)
        # bottom pre-fuel + unlock with endpoint verify
        p_pu, _ = _plan_to_pickup(frame, bottom_only=True)
        if p_pu:
            for a in p_pu:
                resp = sess.action(DIR_TO_ACTION[a])
                frame, meta = resp["frame"], resp
        print("pre-unlock", ls20.init(frame).cursor, "pu", ls20.energy_pickups(frame))
        for attempt in range(3):
            p, dest, _ = _plan_to_unlock(frame, (6, 6))
            print(f"unlock plan{attempt} len={None if p is None else len(p)} dest={dest}")
            if not p:
                break
            for a in p:
                resp = sess.action(DIR_TO_ACTION[a])
                frame, meta = resp["frame"], resp
            cur = ls20.init(frame).cursor
            print("after unlock steps", cur)
            if cur == (6, 6):
                break
            # nudge: if at (6,5) D into ring
            if cur == (6, 5):
                resp = sess.action(2)
                frame, meta = resp["frame"], resp
                print("nudge D", ls20.init(frame).cursor)
                if ls20.init(frame).cursor == (6, 6):
                    break
        cur = ls20.init(frame).cursor
        print("UNLOCK END", cur, "pu", ls20.energy_pickups(frame),
              "c9", int((ls20._plane(frame) == 9).sum()))
        if cur not in ((6, 6), (6, 5)):
            print("FAIL not near ring")
            return
        # oscillate 8 full cycles on ring
        if cur == (6, 5):
            resp = sess.action(2)
            frame, meta = resp["frame"], resp
        for i in range(8):
            resp = sess.action(1)  # U to (6,5)
            frame, meta = resp["frame"], resp
            resp = sess.action(2)  # D to (6,6)
            frame, meta = resp["frame"], resp
            print(f"osc{i}", ls20.init(frame).cursor, "c9",
                  int((ls20._plane(frame) == 9).sum()),
                  "unlock_cands", _unlock_candidates(frame))
        # to (4,7) + H23
        frame, meta, ok = go(frame, sess, meta, (4, 7), armed=False)
        print("at47", ls20.init(frame).cursor, ok)
        for a in RITUAL:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
        print("H23 done", ls20.init(frame).cursor, "carry", ls20.init(frame).carrying)
        # mid fuel
        for _ in range(25):
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
                print("mid unreachable", ls20.init(frame).cursor)
                break
            resp = sess.action(DIR_TO_ACTION[p[0]])
            frame, meta = resp["frame"], resp
        print("fueled", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame),
              "pu", ls20.energy_pickups(frame))
        # to (2,1)
        frame, meta, ok = go(frame, sess, meta, (2, 1), armed=True)
        cur = ls20.init(frame).cursor
        arr = np.asarray(frame)
        print("at21", cur, "ui", ls20.ui_energy(frame), "s9", stamp9(frame)[0],
              "carry", ls20.init(frame).carrying,
              "layers", arr.shape[0] if arr.ndim == 3 else 1, "ok", ok)
        # settle: if multilayer, send action that stays or UP no-op?
        for t in range(5):
            before = ls20.init(frame).cursor
            resp = sess.action(3)  # LEFT
            frame, meta = resp["frame"], resp
            after = ls20.init(frame).cursor
            arr = np.asarray(frame)
            print(f"L{t}", before, "->", after, "lv", meta.get("levels_completed"),
                  "layers", arr.shape[0] if arr.ndim == 3 else 1,
                  "s9", stamp9(frame)[0], "ui", ls20.ui_energy(frame))
            if int(meta.get("levels_completed") or 0) >= 4:
                print("CLEARED")
                return
            if after != before:
                print("MOVED", after)
                return
        print("FAIL still blocked")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
