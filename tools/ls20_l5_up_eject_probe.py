"""L5: mid-fuel then go to (10,10) and try UP (recording clear)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, _step_cell
from tools.ls20_seated_clear_full import _plan_to_pickup, _plan_to_unlock
from tools.ls20_l5_unlock_trace import clear_l4


def goto(frame, sess, target, max_steps=40):
    for _ in range(max_steps):
        cur = ls20.init(frame).cursor
        if cur == target:
            return frame, True
        offset = ls20.grid_offset(frame)
        walk = ls20.build_walkable(frame, offset, armed=True)
        warps = ls20.detect_warps(frame, offset)
        pickups = ls20.energy_pickups(frame)
        path, _, _, _ = _energy_bfs(
            cur, MAX_FUEL, 0, walk, pickups, offset,
            lambda c, _f, _p: c == target, warps,
        )
        if not path:
            return frame, False
        frame = sess.action(DIR_TO_ACTION[path[0]])["frame"]
    return frame, ls20.init(frame).cursor == target


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l5_up_eject"])
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
        frame, _ = goto(frame, sess, (7, 5))
        frame = sess.action(4)["frame"]
        print("fueled", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        frame, ok = goto(frame, sess, (10, 10))
        print("at1010", ok, ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        offset = ls20.grid_offset(frame)
        walk_u = ls20.build_walkable(frame, offset, armed=False)
        walk_a = ls20.build_walkable(frame, offset, armed=True)
        warps = ls20.detect_warps(frame, offset, walk_u)
        # column segment
        ys = sorted(y for (x, y) in walk_u if x == 10)
        print("walk_u y", ys)
        print("walk_a y", sorted(y for (x, y) in walk_a if x == 10))
        print("warp", warps.get(((10, 10), (0, -1))))
        cur = ls20.init(frame).cursor
        for name, a in (("U", (0, -1)),):
            pred = _step_cell(cur, a, walk_a, warps)
            r = sess.action(DIR_TO_ACTION[a])
            live = ls20.init(r["frame"]).cursor
            print(
                f"DIR {name} pred={pred} live={live} "
                f"lv={r.get('levels_completed')} ui={ls20.ui_energy(r['frame'])} "
                f"state={r.get('state')}"
            )
    finally:
        sess.close()


if __name__ == "__main__":
    main()
