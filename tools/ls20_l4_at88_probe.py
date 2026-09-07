"""At (8,8) on L4 path, dump warps and live-probe all dirs."""
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
from tools.ls20_l4_unlock_trace import advance_to_l4_pre_unlock


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_at88"])
        frame, meta = advance_to_l4_pre_unlock(sess)
        # follow unlock plan until (8,8)
        p, _, _ = _plan_to_unlock(frame, (6, 6))
        for a in p:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            if ls20.init(frame).cursor == (8, 8):
                break
            # if we overshoot, stop when we leave intended
        # if not at 88, navigate
        for _ in range(15):
            if ls20.init(frame).cursor == (8, 8):
                break
            # manual: from (6,10) path first steps
            cur = ls20.init(frame).cursor
            if cur == (6, 10):
                resp = sess.action(1); frame, meta = resp["frame"], resp; continue
            if cur == (6, 9):
                resp = sess.action(1); frame, meta = resp["frame"], resp; continue
            if cur == (6, 8):
                resp = sess.action(4); frame, meta = resp["frame"], resp; continue
            if cur == (7, 8):
                resp = sess.action(4); frame, meta = resp["frame"], resp; continue
            break
        cur = ls20.init(frame).cursor
        print("at", cur)
        if cur != (8, 8):
            print("could not reach 88")
            return
        offset = ls20.grid_offset(frame)
        walk_a = ls20.build_walkable(frame, offset, armed=True)
        walk_u = ls20.build_walkable(frame, offset, armed=False)
        warps = ls20.detect_warps(frame, offset, walk_u)
        import numpy as np
        g = ls20._plane(frame)
        px, py = ls20.cursor_to_pixel((8, 8), offset)
        print("foot", g[py:py + 2, px:px + 5].tolist())
        print("west1", g[py:py + 2, px - 1].tolist() if px > 0 else None)
        print("above1", int(np.sum(g[py - 1, px:px + 5] == 1)) if py > 0 else None)
        print("east1", g[py:py + 2, px + 5:px + 13].tolist())
        for d in DIRS:
            print("model", DIR_TO_ACTION[d], "warp", warps.get((cur, d)),
                  "step", _step_cell(cur, d, walk_a, warps))
        # Can't probe all dirs without restore - just UP once (known bad)
        # Actually open 4 sessions is expensive; probe UP only since that's the bug
        resp = sess.action(1)
        print("live U", cur, "->", ls20.init(resp["frame"]).cursor)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
