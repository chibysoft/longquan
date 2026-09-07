"""Trace unlock plan from (6,10) step-by-step vs live."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import plan_two_phase, _step_cell
from tools.ls20_seated_clear_full import (
    _plan_to_pickup, _plan_to_unlock, _sync_after_levelup, _unlock_candidates,
)


def advance_to_l4_pre_unlock(sess):
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
    return frame, meta


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_unlock_trace"])
        frame, meta = advance_to_l4_pre_unlock(sess)
        print("start", ls20.init(frame).cursor, "pu", ls20.energy_pickups(frame))
        p, dest, fuel = _plan_to_unlock(frame, (6, 6))
        print("plan", [DIR_TO_ACTION[a] for a in p], "dest", dest)
        # simulate offline
        offset = ls20.grid_offset(frame)
        walk_a = ls20.build_walkable(frame, offset, armed=True)
        walk_u = ls20.build_walkable(frame, offset, armed=False)
        warps = ls20.detect_warps(frame, offset, walk_u)
        cur = ls20.init(frame).cursor
        print("sim:")
        for i, a in enumerate(p, 1):
            nxt = _step_cell(cur, a, walk_a, warps)
            print(f"  {i} A{DIR_TO_ACTION[a]} {cur}->{nxt} warp={warps.get((cur,a))}")
            cur = nxt
        # live
        print("live:")
        cur = ls20.init(frame).cursor
        for i, a in enumerate(p, 1):
            pred = _step_cell(cur, a, walk_a, warps)
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            # refresh model from new frame? for diagnosis use old warps first
            live = ls20.init(frame).cursor
            mismatch = " MISMATCH" if live != pred else ""
            print(f"  {i} A{DIR_TO_ACTION[a]} pred={pred} live={live}{mismatch} "
                  f"ui={ls20.ui_energy(frame)}")
            cur = live
            # rebuild warps from live frame for next pred
            offset = ls20.grid_offset(frame)
            walk_a = ls20.build_walkable(frame, offset, armed=True)
            walk_u = ls20.build_walkable(frame, offset, armed=False)
            warps = ls20.detect_warps(frame, offset, walk_u)
        print("END", ls20.init(frame).cursor, "cands", _unlock_candidates(frame))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
