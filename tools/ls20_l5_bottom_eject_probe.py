"""L5: reach (10,10) after unlock and probe eject/stamp (recording path)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, _step_cell
from tools.ls20_seated_clear_full import _plan_to_pickup, _plan_to_unlock
from tools.ls20_l5_unlock_trace import clear_l4


def goto(frame, sess, target, armed=True, max_steps=60):
    for i in range(max_steps):
        cur = ls20.init(frame).cursor
        if cur == target:
            return frame, True
        offset = ls20.grid_offset(frame)
        walk = ls20.build_walkable(frame, offset, armed=armed)
        warps = ls20.detect_warps(frame, offset)
        pickups = ls20.energy_pickups(frame)
        path, _, _, _ = _energy_bfs(
            cur, MAX_FUEL, 0, walk, pickups, offset,
            lambda c, _f, _p: c == target, warps,
        )
        if not path:
            print(f"NO_PATH {cur}->{target}")
            return frame, False
        a = path[0]
        pred = _step_cell(cur, a, walk, warps)
        r = sess.action(DIR_TO_ACTION[a])
        live = ls20.init(r["frame"]).cursor
        mark = "OK" if live == pred else "BAD"
        if mark == "BAD" or i < 3 or live == target:
            print(f"  {i:02d} {cur} {a} pred={pred} live={live} {mark}")
        frame = r["frame"]
    return frame, ls20.init(frame).cursor == target


def dump_eject_candidate(frame, cell=(10, 10)):
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    g = ls20._plane(frame)
    mw = ls20.MOVE_SHAPE[0]
    px, py = ls20.cursor_to_pixel(cell, offset)
    H, W = g.shape
    east = g[py:py + 2, px + mw:min(px + 20, W)] if px + mw < W else None
    foot = g[py:py + 2, px:px + mw] if px + mw <= W else None
    print(
        f"cell {cell} in_walk={cell in walk_u} pxpy=({px},{py}) W={W} "
        f"east={None if east is None else east.tolist()} "
        f"foot={None if foot is None else foot.tolist()}"
    )
    for d in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        print(f"  model warp {d} -> {warps.get((cell, d))}")


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l5_bottom_eject"])
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
        print("unlock", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))

        # recording: mid fuel via (7,5) R, unlock already done; go bottom path
        # simpler: BFS to (10,10)
        frame, ok = goto(frame, sess, (10, 10), armed=True)
        print("at1010", ok, ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        dump_eject_candidate(frame, (10, 10))
        dump_eject_candidate(frame, (10, 6))

        cur = ls20.init(frame).cursor
        if cur != (10, 10):
            return
        offset = ls20.grid_offset(frame)
        walk_a = ls20.build_walkable(frame, offset, armed=True)
        warps = ls20.detect_warps(frame, offset)
        for name, a in (("U", (0, -1)), ("D", (0, 1)), ("L", (-1, 0)), ("R", (1, 0))):
            # re-goto if needed
            if ls20.init(frame).cursor != (10, 10):
                frame, ok = goto(frame, sess, (10, 10), armed=True, max_steps=30)
                print("re", ok, ls20.init(frame).cursor)
                if not ok:
                    break
            cur = ls20.init(frame).cursor
            pred = _step_cell(cur, a, walk_a, warps)
            r = sess.action(DIR_TO_ACTION[a])
            live = ls20.init(r["frame"]).cursor
            print(
                f"DIR {name} pred={pred} live={live} "
                f"lv={r.get('levels_completed')} ui={ls20.ui_energy(r['frame'])}"
            )
            frame = r["frame"]
            if int(r.get("levels_completed") or 0) >= 5:
                print("PASS L5")
                break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
