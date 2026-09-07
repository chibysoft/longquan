"""At L5 (10,2) after bottom eject: dump warps and try all actions incl A5."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, _step_cell
from tools.ls20_seated_clear_full import _plan_to_pickup, _plan_to_unlock, _ov
from tools.ls20_l5_unlock_trace import clear_l4
from longquan.interactive.match import mover_bbox_from_cursor


def goto(frame, sess, target, max_steps=50):
    for _ in range(max_steps):
        if ls20.init(frame).cursor == target:
            return frame, True
        offset = ls20.grid_offset(frame)
        walk = ls20.build_walkable(frame, offset, armed=True)
        warps = ls20.detect_warps(frame, offset)
        pickups = ls20.energy_pickups(frame)
        path, _, _, _ = _energy_bfs(
            ls20.init(frame).cursor, MAX_FUEL, 0, walk, pickups, offset,
            lambda c, _f, _p: c == target, warps,
        )
        if not path:
            return frame, False
        frame = sess.action(DIR_TO_ACTION[path[0]])["frame"]
    return frame, ls20.init(frame).cursor == target


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l5_at102"])
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
        frame, _ = goto(frame, sess, (10, 10))
        print("1010", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        # UP eject
        frame = sess.action(1)["frame"]
        cur = ls20.init(frame).cursor
        print("after U", cur, "ui", ls20.ui_energy(frame))
        offset = ls20.grid_offset(frame)
        walk_a = ls20.build_walkable(frame, offset, armed=True)
        walk_u = ls20.build_walkable(frame, offset, armed=False)
        warps = ls20.detect_warps(frame, offset, walk_u)
        stamp = next(g.shape for g in ls20.init(frame).goals if g.id == "ls20-stamp")
        print("stamp", stamp, "ov", _ov(mover_bbox_from_cursor(cur, offset), stamp))
        print("walk (10,1)", (10, 1) in walk_a, (10, 1) in walk_u)
        for d in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            print(f" warp {cur}{d} -> {warps.get((cur, d))}")
        # try dirs from (10,2)
        for name, aid in (("U", 1), ("D", 2), ("L", 3), ("R", 4), ("A5", 5)):
            if ls20.init(frame).cursor != cur:
                # can't easily restore; break
                print("lost", ls20.init(frame).cursor)
                break
            before = ls20.init(frame).cursor
            if aid <= 4:
                a = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}[aid]
                pred = _step_cell(before, a, walk_a, warps)
            else:
                pred = None
            r = sess.action(aid)
            live = ls20.init(r["frame"]).cursor
            print(
                f"{name} pred={pred} live={live} lv={r.get('levels_completed')} "
                f"ui={ls20.ui_energy(r['frame'])} layers="
                f"{__import__('numpy').asarray(r['frame']).shape}"
            )
            frame = r["frame"]
            if int(r.get("levels_completed") or 0) >= 5:
                print("PASS")
                break
            # if moved, try return with goto
            if live != before:
                frame, ok = goto(frame, sess, before, max_steps=25)
                print(" back", ok, ls20.init(frame).cursor)
                cur = ls20.init(frame).cursor
                offset = ls20.grid_offset(frame)
                walk_a = ls20.build_walkable(frame, offset, armed=True)
                warps = ls20.detect_warps(frame, offset)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
