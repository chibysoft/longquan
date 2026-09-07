"""Compare eject false-positive at (6,6) post-unlock vs real (7,5)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import plan_two_phase
from tools.ls20_seated_clear_full import (
    _plan_to_pickup, _plan_to_unlock, _unlock_candidates, _sync_after_levelup,
)


def rail_info(frame, cell):
    offset = ls20.grid_offset(frame)
    g = ls20._plane(frame)
    H, W = g.shape
    mw = 5
    cx, cy = cell
    px, py = ls20.cursor_to_pixel((cx, cy), offset)
    east = g[py:py + 2, px + mw:min(px + 20, W)]
    above = g[max(0, py - 1), px:px + mw]
    foot = g[py:py + 2, px:px + mw]
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    ys = sorted(y for (x, y) in walk_u if x == cx)
    # east-1 along full column cells
    rail_rows = 0
    for y in ys:
        pxx, pyy = ls20.cursor_to_pixel((cx, y), offset)
        e = g[pyy:pyy + 2, pxx + mw:min(pxx + 20, W)]
        if np.any(e == 1):
            rail_rows += 1
    return {
        "cell": cell,
        "ys_col": ys,
        "east1_foot": int(np.sum(east == 1)),
        "above1": int(np.sum(above == 1)),
        "foot9": int(np.sum(foot == 9)),
        "foot12": int(np.sum(foot == 12)),
        "foot0": int(np.sum(foot == 0)),
        "rail_rows_east1": rail_rows,
        "in_u": cell in walk_u,
        "in_a": cell in ls20.build_walkable(frame, offset, armed=True),
    }


def advance_to_l4(sess):
    resp = sess.reset()
    frame, meta = resp["frame"], resp
    while int(meta.get("levels_completed") or 0) < 3:
        lv = int(meta.get("levels_completed") or 0)
        for cand in _unlock_candidates(frame):
            p_pu, _ = _plan_to_pickup(frame)
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
        if int(meta.get("levels_completed") or 0) > lv:
            frame, meta = _sync_after_levelup(sess, frame)
        else:
            raise RuntimeError(f"stuck at lv={lv}")
    return frame, meta


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_eject_fp"])
        frame, meta = advance_to_l4(sess)
        print("PRE75", rail_info(frame, (7, 5)))
        offset = ls20.grid_offset(frame)
        print("PRE66 in_u/a", (6, 6) in ls20.build_walkable(frame, offset, armed=False),
              (6, 6) in ls20.build_walkable(frame, offset, armed=True))
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            for a in p_pu:
                resp = sess.action(DIR_TO_ACTION[a])
                frame, meta = resp["frame"], resp
        p, _, _ = _plan_to_unlock(frame, (6, 6))
        for a in p:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
        print("POST66", rail_info(frame, (6, 6)))
        print("POST75", rail_info(frame, (7, 5)))
        # live dirs: U then we are not at 66; probe D/L/R need separate sessions
        # or walk back. Just U once:
        cur = ls20.init(frame).cursor
        r = sess.action(1)
        print("live U", cur, "->", ls20.init(r["frame"]).cursor)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
