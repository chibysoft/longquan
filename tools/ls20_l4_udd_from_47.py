"""Unlock → go to (4,7) → UDD (UP lands on contact) → stamp (1,1)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, RITUAL
from tools.ls20_seated_clear_full import (
    _plan_to_pickup, _plan_to_unlock, _sync_after_levelup, _unlock_candidates,
    _plan_armed_stamp_only,
)
from tools.ls20_l4_dd_ritual_probe import boot_l4
from tools.ls20_l4_stamp9_probe import stamp9
from tools.ls20_seated_clear import plan_two_phase


def plan_to(frame, goal):
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))

    def at(cell, _f, _p):
        return cell == goal

    return _energy_bfs(state.cursor, fuel0, 0, walk_u, pickups, offset, at, warps)


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_udd_from_47"])
        frame, meta = boot_l4(sess)
        # navigate to (4,7) unarmed
        for i in range(30):
            p, c, f, pm = plan_to(frame, (4, 7))
            if not p:
                print("cannot reach 47", ls20.init(frame).cursor)
                break
            if len(p) == 0:
                break
            resp = sess.action(DIR_TO_ACTION[p[0]])
            frame, meta = resp["frame"], resp
            print(f"nav {i} ->", ls20.init(frame).cursor, "carry", ls20.init(frame).carrying)
            if ls20.init(frame).cursor == (4, 7):
                break
        print("pre-ritual", ls20.init(frame).cursor, "carry", ls20.init(frame).carrying)
        for a in RITUAL:
            before = ls20.init(frame).cursor
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            print("ritual", a, before, "->", ls20.init(frame).cursor,
                  "carry", ls20.init(frame).carrying)
        # stamp closed-loop
        for i in range(40):
            path, dest, _, info = _plan_armed_stamp_only(frame)
            if not path:
                print("no path", info, ls20.init(frame).cursor)
                break
            before = ls20.init(frame).cursor
            resp = sess.action(DIR_TO_ACTION[path[0]])
            frame, meta = resp["frame"], resp
            after = ls20.init(frame).cursor
            print(f"{i+1:02d} {before}->{after} carry={ls20.init(frame).carrying} "
                  f"s9={stamp9(frame)[0]} lv={meta.get('levels_completed')}")
            if int(meta.get("levels_completed") or 0) >= 4:
                print("CLEARED")
                return
            if after == before == (2, 1):
                print("stuck")
                break
        print("fail", ls20.init(frame).cursor)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
