"""After L5 unlock+midfuel to (8,1), print stamp path and (10,10) eject."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear_full import _plan_armed_stamp_only, _plan_to_pickup, _plan_to_unlock
from tools.ls20_l5_unlock_trace import clear_l4


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l5_stamp_path"])
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
        # mid via (7,5) R
        from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs
        offset = ls20.grid_offset(frame)
        walk_a = ls20.build_walkable(frame, offset, armed=True)
        warps = ls20.detect_warps(frame, offset)
        pickups = ls20.energy_pickups(frame)
        pm, _, _, _ = _energy_bfs(
            ls20.init(frame).cursor, MAX_FUEL, 0, walk_a, pickups, offset,
            lambda c, _f, _p: c == (7, 5), warps,
        )
        for a in pm or []:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        frame = sess.action(4)["frame"]
        cur = ls20.init(frame).cursor
        print("at", cur, "ui", ls20.ui_energy(frame))
        offset = ls20.grid_offset(frame)
        warps = ls20.detect_warps(frame, offset)
        print("eject1010", {d: warps.get(((10, 10), d)) for d in ((0, -1), (0, 1), (-1, 0), (1, 0))})
        print("eject75", {d: warps.get(((7, 5), d)) for d in ((0, -1), (0, 1), (-1, 0), (1, 0))})
        path, dest, fuel, info = _plan_armed_stamp_only(frame)
        print("stamp dest", dest, "fuel", fuel, "info", info)
        print("path", path)
        # simulate cells
        from tools.ls20_seated_clear import _step_cell
        walk_a = ls20.build_walkable(frame, offset, armed=True)
        c = cur
        for i, a in enumerate(path or []):
            n = _step_cell(c, a, walk_a, warps)
            print(f"  {i} {c} {a} -> {n}")
            c = n
            if c is None:
                break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
