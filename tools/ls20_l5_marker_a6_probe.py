"""L5: contact marker then (10,10)@ui=8 UP; also try A6 on stamp."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import mover_bbox_from_cursor
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs
from tools.ls20_seated_clear_full import _ov, _plan_to_pickup, _plan_to_unlock
from tools.ls20_l5_unlock_trace import clear_l4


def goto(frame, sess, target, max_steps=80):
    for _ in range(max_steps):
        if ls20.init(frame).cursor == target:
            return frame, True
        offset = ls20.grid_offset(frame)
        walk = ls20.build_walkable(frame, offset, armed=True)
        warps = ls20.detect_warps(frame, offset)
        path, _, _, _ = _energy_bfs(
            ls20.init(frame).cursor, MAX_FUEL, 0, walk, [], offset,
            lambda c, _f, _p: c == target, warps,
        )
        if not path:
            return frame, False
        frame = sess.action(DIR_TO_ACTION[path[0]])["frame"]
    return frame, ls20.init(frame).cursor == target


def marker_cells(frame):
    g = ls20._plane(frame)
    offset = ls20.grid_offset(frame)
    walk = ls20.build_walkable(frame, offset, armed=True)
    cells = []
    ys, xs = np.where((g == 0) | (g == 1))
    for x, y in zip(xs.tolist(), ys.tolist()):
        if y >= 54:
            continue
        # nearest walkable
        best = None
        bd = 99
        for c in walk:
            px, py = ls20.cursor_to_pixel(c, offset)
            d = abs(px + 2 - x) + abs(py - y)
            if d < bd:
                bd = d
                best = c
        if best and best not in cells:
            cells.append(best)
    return cells


def drain_to_1010_ui8(frame, sess):
    frame, _ = goto(frame, sess, (10, 9))
    # bounce 10,8/10,9 until ui~12 then DOWN
    for _ in range(30):
        ui = ls20.ui_energy(frame)
        cur = ls20.init(frame).cursor
        if cur == (10, 9) and ui <= 12:
            frame = sess.action(2)["frame"]
            break
        if cur == (10, 9):
            frame = sess.action(1)["frame"]
        elif cur == (10, 8):
            frame = sess.action(2)["frame"]
        elif cur == (10, 10):
            frame = sess.action(1)["frame"]
            if ls20.init(frame).cursor != (10, 9):
                frame, _ = goto(frame, sess, (10, 9))
        else:
            frame, _ = goto(frame, sess, (10, 9))
    return frame


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l5_marker_a6"])
        frame, _ = clear_l4(sess)
        ppu, _ = _plan_to_pickup(frame, bottom_only=True)
        for a in ppu or []:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        for _ in range(40):
            if ls20.init(frame).cursor == (5, 5):
                break
            p, _, _ = _plan_to_unlock(frame, (5, 5))
            if not p:
                break
            frame = sess.action(DIR_TO_ACTION[p[0]])["frame"]
        # oscillate unlock
        for _ in range(4):
            if ls20.init(frame).cursor == (5, 5):
                frame = sess.action(4)["frame"]
            else:
                frame = sess.action(3)["frame"]
        print("cands", marker_cells(frame)[:8])
        # contact first few marker-adjacent cells
        for t in marker_cells(frame)[:4]:
            frame, ok = goto(frame, sess, t)
            print("contact", t, ok, "ui", ls20.ui_energy(frame))
        frame, _ = goto(frame, sess, (7, 5))
        frame = sess.action(2)["frame"]
        frame, _ = goto(frame, sess, (1, 2))
        print("fueled", ls20.init(frame).cursor, ls20.ui_energy(frame))
        frame = drain_to_1010_ui8(frame, sess)
        print("at", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        # try UP
        r = sess.action(1)
        print("U", ls20.init(r["frame"]).cursor, "lv", r.get("levels_completed"),
              "ui", ls20.ui_energy(r["frame"]))
        frame = r["frame"]
        if int(r.get("levels_completed") or 0) >= 5:
            print("PASS")
            return
        # from wherever, try A6 on stamp center
        stamp = next(g.shape for g in ls20.init(frame).goals if g.id == "ls20-stamp")
        x = (stamp[0] + stamp[2]) // 2
        y = (stamp[1] + stamp[3]) // 2
        print("A6 click", x, y)
        r = sess.action(6, x=x, y=y)
        print("A6", ls20.init(r["frame"]).cursor, "lv", r.get("levels_completed"),
              r.get("state"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
