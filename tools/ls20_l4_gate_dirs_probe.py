"""After unlock+contact+approach (2,1), dump gate and try every dir + neighbors."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import mover_bbox_from_cursor, carrying_bbox_from_cursor
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import plan_two_phase, _step_cell, _ov
from tools.ls20_seated_clear_full import (
    _plan_to_pickup, _plan_to_unlock, _unlock_candidates, _sync_after_levelup,
    _plan_to_contact, _plan_armed_stamp_only,
)


def stamp9(frame):
    st = ls20.init(frame)
    stamps = [g for g in st.goals if g.id == "ls20-stamp"]
    if not stamps:
        return -1, None
    stamp = stamps[0].shape
    g = ls20._plane(frame)
    x0, y0, x1, y1 = stamp
    return int(np.sum(g[y0:y1 + 1, x0:x1 + 1] == 9)), stamp


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_gate_dirs"])
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
        # contact
        for _ in range(20):
            pc, cc, _, ic = _plan_to_contact(frame)
            if pc is None:
                print("contact fail", ic)
                break
            if len(pc) == 0:
                print("contacted", cc, ic)
                break
            resp = sess.action(DIR_TO_ACTION[pc[0]])
            frame, meta = resp["frame"], resp
        # go to (2,1)
        for _ in range(40):
            path, dest, _, info = _plan_armed_stamp_only(frame)
            if not path:
                print("stamp plan fail", info)
                break
            resp = sess.action(DIR_TO_ACTION[path[0]])
            frame, meta = resp["frame"], resp
            if ls20.init(frame).cursor == (2, 1):
                break
        cur = ls20.init(frame).cursor
        s9, stamp = stamp9(frame)
        offset = ls20.grid_offset(frame)
        walk_a = ls20.build_walkable(frame, offset, armed=True)
        walk_u = ls20.build_walkable(frame, offset, armed=False)
        warps = ls20.detect_warps(frame, offset, walk_u)
        g = ls20._plane(frame)
        print("cur", cur, "ui", ls20.ui_energy(frame), "s9", s9,
              "goals", [g.id for g in ls20.init(frame).goals])
        print("11 in_a/u", (1, 1) in walk_a, (1, 1) in walk_u)
        for cell in [(1, 1), (2, 1), (1, 2), (0, 1), (2, 2)]:
            if cell not in walk_a and cell not in walk_u:
                print(cell, "not walk")
                continue
            px, py = ls20.cursor_to_pixel(cell, offset)
            foot = g[py:py + 2, px:px + 5]
            print(cell, "a", cell in walk_a, "foot", foot.tolist())
        # live try each dir from (2,1) — need restore: only L and see; then new session dirs
        for aid, name in [(3, "L"), (1, "U"), (2, "D"), (4, "R")]:
            # can't restore; just try L first then stop
            pass
        r = sess.action(3)
        print("L", cur, "->", ls20.init(r["frame"]).cursor, "lv", r.get("levels_completed"),
              "s9", stamp9(r["frame"])[0])
        # if still (2,1), try U
        if ls20.init(r["frame"]).cursor == (2, 1):
            r2 = sess.action(1)
            print("U", "->", ls20.init(r2["frame"]).cursor, "lv", r2.get("levels_completed"))
            if ls20.init(r2["frame"]).cursor == (2, 1):
                r3 = sess.action(2)
                print("D", "->", ls20.init(r3["frame"]).cursor)
                r4 = sess.action(4)
                print("R", "->", ls20.init(r4["frame"]).cursor, "lv", r4.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
