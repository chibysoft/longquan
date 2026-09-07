"""Reach (1,2) without (1,1), try UP into stamp gate."""
from __future__ import annotations

import sys
from pathlib import Path
from collections import deque

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import mover_bbox_from_cursor
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, _step_cell
from tools.ls20_seated_clear_full import _ov, _plan_to_unlock
from tools.ls20_l4_unlock_trace import advance_to_l4_pre_unlock


def fuel(ui: int) -> int:
    if ui >= 64 or ui <= 0:
        return MAX_FUEL
    return max(1, min(MAX_FUEL, max((ui - 8) // 4, ui // 2)))


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_gate_from_12"])
        frame, _ = advance_to_l4_pre_unlock(sess)
        p, _, _ = _plan_to_unlock(frame, (6, 6))
        for a in p:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]

        offset = ls20.grid_offset(frame)
        walk_u = set(ls20.build_walkable(frame, offset, armed=False))
        warps = ls20.detect_warps(frame, offset, walk_u)
        mid = [x for x in ls20.energy_pickups(frame) if x[1] < 40]
        blocked = {
            c for c in walk_u
            if any(_ov(mover_bbox_from_cursor(c, offset), pb) > 0 for pb in mid)
        }
        p47, _, _, _ = _energy_bfs(
            ls20.init(frame).cursor, fuel(ls20.ui_energy(frame)), 0,
            frozenset(walk_u - blocked), [], offset,
            lambda c, _f, _p: c == (4, 7), warps,
        )
        for a in p47:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        for a in ((0, -1), (0, 1)):
            frame = sess.action(DIR_TO_ACTION[a])["frame"]

        offset = ls20.grid_offset(frame)
        walk_a = ls20.build_walkable(frame, offset, armed=True)
        warps = ls20.detect_warps(frame, offset, ls20.build_walkable(frame, offset, armed=False))
        mid = list(ls20.energy_pickups(frame))

        def at_mid(c, _f, _p):
            return any(_ov(mover_bbox_from_cursor(c, offset), pb) > 0 for pb in mid)

        pm, _, _, _ = _energy_bfs(
            ls20.init(frame).cursor, MAX_FUEL, 0, walk_a, mid, offset, at_mid, warps,
        )
        for a in pm:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        print("after mid", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))

        offset = ls20.grid_offset(frame)
        walk_a = ls20.build_walkable(frame, offset, armed=True)
        warps = ls20.detect_warps(frame, offset, ls20.build_walkable(frame, offset, armed=False))
        walk_no11 = frozenset(c for c in walk_a if c != (1, 1))
        start = ls20.init(frame).cursor
        q = deque([(start, [])])
        seen = {start}
        path = None
        while q:
            c, pa = q.popleft()
            if c == (1, 2):
                path = pa
                break
            for d in DIRS:
                n = _step_cell(c, d, walk_no11, warps)
                if n and n not in seen:
                    seen.add(n)
                    q.append((n, pa + [d]))
        print("path to (1,2)", path)
        if not path:
            return
        for a in path:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
            print(" step", a, ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        print("at", ls20.init(frame).cursor)
        for aid, name in ((1, "U"), (3, "L"), (4, "R"), (2, "D")):
            # only one live try per session — UP first
            if name != "U":
                continue
            r = sess.action(aid)
            print(name, ls20.init(r["frame"]).cursor, "lv", r.get("levels_completed"),
                  "ui", ls20.ui_energy(r["frame"]))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
