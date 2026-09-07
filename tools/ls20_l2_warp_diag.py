"""Diagnose L2 stamp PLAN FAIL after eject/hop foot changes."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, _step_cell
from tools.ls20_seated_clear_full import (
    _plan_armed_stamp_only,
    _plan_to_contact,
    _plan_to_pickup,
    _sync_after_levelup,
)


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l2_warp_diag"])
        frame = sess.reset()["frame"]
        # L1 clear (same open actions as seated clear usually finds)
        path = [( -1, 0), (-1, 0), (-1, 0), (0, -1), (0, -1), (0, -1),
                (1, 0), (0, -1), (1, 0), (1, 0), (0, -1), (0, -1), (0, -1)]
        for a in path:
            r = sess.action(DIR_TO_ACTION[a])
            frame = r["frame"]
            if int(r.get("levels_completed") or 0) >= 1:
                break
        print("after L1", r.get("levels_completed"), ls20.init(frame).cursor)
        frame, meta = _sync_after_levelup(sess, frame)
        print("sync", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))

        offset = ls20.grid_offset(frame)
        walk_u = ls20.build_walkable(frame, offset, armed=False)
        walk_a = ls20.build_walkable(frame, offset, armed=True)
        warps = ls20.detect_warps(frame, offset, walk_u)
        ejects = []
        hops = []
        for (cell, d), land in warps.items():
            if d != (0, -1):
                continue
            lands = {warps.get((cell, dd)) for dd in ((1, 0), (-1, 0), (0, 1), (0, -1))}
            if len(lands) != 1 or None in lands:
                continue
            land0 = next(iter(lands))
            if land0[0] == cell[0] and land0[1] < cell[1]:
                ejects.append((cell, land0))
            elif land0[0] != cell[0]:
                hops.append((cell, land0))
        print("ejects", sorted(set(ejects)))
        print("hops/horiz", sorted(set(hops)))

        ppu, info = _plan_to_pickup(frame)
        print("pickup", ppu, info)
        pc, ic = _plan_to_contact(frame)[:2], _plan_to_contact(frame)[3]
        print("contact", pc, ic)
        ps = _plan_armed_stamp_only(frame)
        print("stamp", ps[1], ps[3])

        # try with fuel max from current
        stamp = next(g.shape for g in ls20.init(frame).goals if g.id == "ls20-stamp")
        from longquan.interactive.match import mover_bbox_from_cursor
        from tools.ls20_seated_clear_full import _ov

        def at_stamp(cell, _f, _p):
            return _ov(mover_bbox_from_cursor(cell, offset), stamp) >= 10

        pickups = ls20.energy_pickups(frame)
        for fuel in (5, 20, MAX_FUEL):
            p, c, f, _ = _energy_bfs(
                ls20.init(frame).cursor, fuel, 0, walk_a, pickups, offset, at_stamp, warps,
            )
            print(f"bfs fuel={fuel} path={None if p is None else len(p)} dest={c}")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
