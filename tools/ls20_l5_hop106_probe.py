"""L5: live 4-dir at (10,6) + dump false ring-hop candidates vs model.

Gets to L5 via seated clear path (reuse unlock_trace helpers), unlocks (5,5),
mid-fuels via (7,5), then navigates toward (10,6) and probes U/D/L/R.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import mover_bbox_from_cursor
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, _step_cell
from tools.ls20_seated_clear_full import (
    _ov,
    _plan_armed_stamp_only,
    _plan_to_pickup,
    _plan_to_unlock,
)
from tools.ls20_l5_unlock_trace import clear_l4


def _dump_hops(frame, tag: str):
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    warps = ls20.detect_warps(frame, offset, walk_u)
    g = ls20._plane(frame)
    mw = ls20.MOVE_SHAPE[0]
    hops = []
    for (cell, d), land in warps.items():
        if d != (0, -1):
            continue
        # hop pads have ALL dirs → same land (before step)
        lands = {warps.get((cell, dd)) for dd in ((1, 0), (-1, 0), (0, 1), (0, -1))}
        if len(lands) == 1 and None not in lands and next(iter(lands)) != cell:
            # likely hop or eject; eject land is same column
            if land[0] != cell[0]:
                hops.append((cell, land))
    hops = sorted(set(hops))
    print(f"=== hops {tag} count={len(hops)}")
    for cell, land in hops:
        cx, cy = cell
        px, py = ls20.cursor_to_pixel(cell, offset)
        east = g[py:py + 2, px + mw:min(px + 10, g.shape[1])]
        foot = g[py:py + 2, px:px + mw]
        print(
            f"  hop {cell}->{land} east={east.tolist()} foot9/12="
            f"{bool(np.any((foot == 9) | (foot == 12)))} "
            f"N_walk={(cx, cy - 1) in walk_u} S_walk={(cx, cy + 1) in walk_u} "
            f"in_walk_a={cell in walk_a}"
        )
    for cell in ((10, 6), (8, 8), (4, 8), (8, 5), (10, 5), (9, 1), (10, 1)):
        print(
            f"  cell {cell} walk_u={cell in walk_u} walk_a={cell in walk_a} "
            f"warpU={warps.get((cell, (0, -1)))} "
            f"warpR={warps.get((cell, (1, 0)))}"
        )
    st = _plan_armed_stamp_only(frame)
    print(f"  stamp_plan path_len={st[3].get('path_len')} dest={st[1]} info={st[3]}")


def _goto(frame, sess, target, armed=True, max_steps=40):
    for i in range(max_steps):
        cur = ls20.init(frame).cursor
        if cur == target:
            return frame, True
        offset = ls20.grid_offset(frame)
        walk = ls20.build_walkable(frame, offset, armed=armed)
        warps = ls20.detect_warps(frame, offset)
        pickups = ls20.energy_pickups(frame)
        ui = ls20.ui_energy(frame)
        fuel0 = MAX_FUEL if pickups or ui >= 64 else max(8, ui // 2)

        def goal(c, _f, _p):
            return c == target

        path, _, _, _ = _energy_bfs(
            cur, fuel0, 0, walk, pickups, offset, goal, warps,
        )
        if not path:
            print(f"  NO_PATH {cur}->{target} armed={armed}")
            return frame, False
        a = path[0]
        pred = _step_cell(cur, a, walk, warps)
        r = sess.action(DIR_TO_ACTION[a])
        live = ls20.init(r["frame"]).cursor
        print(f"  {i:02d} {cur} {a} pred={pred} live={live} "
              f"{'OK' if live == pred else 'BAD'} warp={warps.get((cur, a))}")
        frame = r["frame"]
        if live != pred:
            # keep going with replan
            pass
    return frame, ls20.init(frame).cursor == target


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l5_hop106"])
        frame, _ = clear_l4(sess)
        print("L5 start", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        _dump_hops(frame, "pre-unlock")

        ppu, _ = _plan_to_pickup(frame, bottom_only=True)
        for a in ppu or []:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        for i in range(40):
            if ls20.init(frame).cursor == (5, 5):
                break
            p, _, _ = _plan_to_unlock(frame, (5, 5))
            if not p:
                print("unlock stuck", ls20.init(frame).cursor)
                break
            frame = sess.action(DIR_TO_ACTION[p[0]])["frame"]
        print("unlocked?", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        _dump_hops(frame, "post-unlock")

        # mid-fuel via (7,5) RIGHT eject → often (8,1)
        frame, ok = _goto(frame, sess, (7, 5), armed=True)
        print("at75", ok, ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        if ok:
            r = sess.action(4)  # RIGHT
            frame = r["frame"]
            print("eject R", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        _dump_hops(frame, "post-eject")

        # try reach (10,6) unarmed then armed
        for armed in (True, False):
            frame, ok = _goto(frame, sess, (10, 6), armed=armed, max_steps=50)
            print(f"reach106 armed={armed}", ok, ls20.init(frame).cursor)
            if ok:
                break

        cur = ls20.init(frame).cursor
        if cur != (10, 6):
            # try any cell on col 10
            for ty in range(10, 0, -1):
                frame, ok = _goto(frame, sess, (10, ty), armed=True, max_steps=30)
                if ok:
                    print("reached", (10, ty))
                    break

        cur = ls20.init(frame).cursor
        print("PROBE_AT", cur)
        _dump_hops(frame, "at-probe")
        if cur == (10, 6) or cur[0] == 10:
            offset = ls20.grid_offset(frame)
            walk_a = ls20.build_walkable(frame, offset, armed=True)
            warps = ls20.detect_warps(frame, offset)
            for name, a in (("U", (0, -1)), ("D", (0, 1)), ("L", (-1, 0)), ("R", (1, 0))):
                pred = _step_cell(cur, a, walk_a, warps)
                r = sess.action(DIR_TO_ACTION[a])
                live = ls20.init(r["frame"]).cursor
                print(f"DIR {name} pred={pred} live={live} "
                      f"{'OK' if live == pred else 'MISMATCH'} "
                      f"warp={warps.get((cur, a))} lv={r.get('levels_completed')}")
                # undo by opposite if possible — don't; just re-goto cell
                frame = r["frame"]
                if live != cur:
                    # try return
                    frame, _ = _goto(frame, sess, cur, armed=True, max_steps=20)
                    cur = ls20.init(frame).cursor
                    print("  back", cur)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
