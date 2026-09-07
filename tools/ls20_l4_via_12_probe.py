"""Try entering gate via (1,2) UP instead of (2,1) LEFT."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import plan_two_phase, _step_cell, _ov, MAX_FUEL, _energy_bfs
from tools.ls20_seated_clear_full import (
    _plan_to_pickup, _plan_to_unlock, _sync_after_levelup, _unlock_candidates,
    _plan_to_contact,
)
from longquan.interactive.match import mover_bbox_from_cursor
from tools.ls20_l4_stamp9_probe import stamp9
from tools.ls20_l4_dd_ritual_probe import boot_l4


def plan_to_cell(frame, goal_cell, armed=True):
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk = ls20.build_walkable(frame, offset, armed=armed)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))

    def at(cell, _f, _p):
        return cell == goal_cell

    return _energy_bfs(state.cursor, fuel0, 0, walk, pickups, offset, at, warps)


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_via_12"])
        frame, meta = boot_l4(sess)
        # contact
        for _ in range(20):
            pc, cc, _, ic = _plan_to_contact(frame)
            if pc is None:
                break
            if len(pc) == 0 or ls20.init(frame).cursor == (4, 6):
                break
            resp = sess.action(DIR_TO_ACTION[pc[0]])
            frame, meta = resp["frame"], resp
        print("at", ls20.init(frame).cursor)
        # go to (1,2)
        for i in range(40):
            p, c, f, pm = plan_to_cell(frame, (1, 2), armed=True)
            if not p:
                print("cannot reach (1,2)", ls20.init(frame).cursor)
                # try (1,2) unarmed
                p, c, f, pm = plan_to_cell(frame, (1, 2), armed=False)
                if not p:
                    print("unarmed also fail")
                    break
            resp = sess.action(DIR_TO_ACTION[p[0]])
            frame, meta = resp["frame"], resp
            cur = ls20.init(frame).cursor
            print(f"{i+1:02d} -> {cur} s9={stamp9(frame)[0]}")
            if cur == (1, 2):
                break
        cur = ls20.init(frame).cursor
        print("try from", cur)
        offset = ls20.grid_offset(frame)
        walk_a = ls20.build_walkable(frame, offset, armed=True)
        warps = ls20.detect_warps(frame, offset, ls20.build_walkable(frame, offset, armed=False))
        for d in DIRS:
            print("model", DIR_TO_ACTION[d], _step_cell(cur, d, walk_a, warps))
        for aid, name in [(1, "U"), (3, "L"), (2, "D"), (4, "R")]:
            before = ls20.init(frame).cursor
            resp = sess.action(aid)
            frame, meta = resp["frame"], resp
            after = ls20.init(frame).cursor
            print(name, before, "->", after, "lv", meta.get("levels_completed"),
                  "s9", stamp9(frame)[0])
            if int(meta.get("levels_completed") or 0) >= 4:
                print("CLEARED")
                return
            if after != before and after != cur:
                cur = after
                # continue probing from new cell only for first move
                if name == "U":
                    break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
