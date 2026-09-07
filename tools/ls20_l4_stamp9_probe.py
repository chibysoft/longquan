"""After unlock, reach (2,1) via (4,1)-(3,1); dump stamp9 and live dirs."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import mover_bbox_from_cursor
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import plan_two_phase, _step_cell, _ov
from tools.ls20_seated_clear_full import (
    _plan_to_pickup, _plan_to_unlock, _unlock_candidates, _sync_after_levelup,
    _plan_armed_stamp_only,
)


def stamp9(frame):
    st = ls20.init(frame)
    stamp = next(g.shape for g in st.goals if g.id == "ls20-stamp")
    g = ls20._plane(frame)
    x0, y0, x1, y1 = stamp
    return int(np.sum(g[y0:y1 + 1, x0:x1 + 1] == 9)), stamp


def to_l4_unlock(sess):
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
        frame, meta = _sync_after_levelup(sess, frame)
    p_pu, _ = _plan_to_pickup(frame)
    if p_pu:
        for a in p_pu:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
    p, _, _ = _plan_to_unlock(frame, (6, 6))
    for a in p:
        resp = sess.action(DIR_TO_ACTION[a])
        frame, meta = resp["frame"], resp
    return frame, meta


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_stamp9"])
        frame, meta = to_l4_unlock(sess)
        s9, stamp = stamp9(frame)
        print("post_unlock", ls20.init(frame).cursor, "stamp9", s9, "ui", ls20.ui_energy(frame))
        # closed-loop toward stamp, log stamp9 each step
        for i in range(20):
            path, dest, fuel, info = _plan_armed_stamp_only(frame)
            if not path:
                print("no path", info)
                break
            a = path[0]
            before = ls20.init(frame).cursor
            s9b, _ = stamp9(frame)
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            after = ls20.init(frame).cursor
            s9a, _ = stamp9(frame)
            print(f"{i+1:02d} A{DIR_TO_ACTION[a]} {before}->{after} "
                  f"stamp9 {s9b}->{s9a} lv={meta.get('levels_completed')} "
                  f"ui={ls20.ui_energy(frame)}")
            if int(meta.get("levels_completed") or 0) >= 4:
                print("CLEARED")
                return
            if after == (2, 1):
                break
        # at or near (2,1): probe dirs
        cur = ls20.init(frame).cursor
        offset = ls20.grid_offset(frame)
        walk_a = ls20.build_walkable(frame, offset, armed=True)
        walk_u = ls20.build_walkable(frame, offset, armed=False)
        warps = ls20.detect_warps(frame, offset, walk_u)
        s9, stamp = stamp9(frame)
        ov = _ov(mover_bbox_from_cursor(cur, offset), stamp)
        print("PROBE cur", cur, "stamp9", s9, "ov", ov,
              "11_a", (1, 1) in walk_a, "11_u", (1, 1) in walk_u)
        for d in DIRS:
            print(" model", DIR_TO_ACTION[d], _step_cell(cur, d, walk_a, warps),
                  "warp", warps.get((cur, d)))
        for aid in (1, 2, 3, 4):
            # each probe needs restore — only try L once from fresh
            pass
        # try LEFT once
        r = sess.action(3)
        print("live L", cur, "->", ls20.init(r["frame"]).cursor,
              "stamp9", stamp9(r["frame"])[0], "lv", r.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
