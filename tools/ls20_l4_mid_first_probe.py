"""After unlock: mid first → (4,7) H23 → stamp; report ui at (2,1)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import carrying_bbox_from_cursor, mover_bbox_from_cursor
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, RITUAL, _energy_bfs
from tools.ls20_seated_clear_full import (
    _ov,
    _plan_armed_stamp_only,
    _plan_to_unlock,
)
from tools.ls20_l4_unlock_trace import advance_to_l4_pre_unlock


def _fuel(ui: int) -> int:
    if ui >= 64 or ui <= 0:
        return MAX_FUEL
    return max((ui - 8) // 4, ui // 2, 1)


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_mid_first"])
        frame, _ = advance_to_l4_pre_unlock(sess)
        p, _, _ = _plan_to_unlock(frame, (6, 6))
        for a in p:
            resp = sess.action(DIR_TO_ACTION[a])
            frame = resp["frame"]
        print("unlock", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))

        offset = ls20.grid_offset(frame)
        walk_u = ls20.build_walkable(frame, offset, armed=False)
        warps = ls20.detect_warps(frame, offset, walk_u)
        mid = [p for p in ls20.energy_pickups(frame) if p[1] < 40]
        fuel0 = _fuel(ls20.ui_energy(frame))

        def at_mid(cell, _f, _p):
            return any(
                _ov(mover_bbox_from_cursor(cell, offset), pb) > 0 for pb in mid
            )

        pm, _, _, _ = _energy_bfs(
            ls20.init(frame).cursor, fuel0, 0, walk_u, mid, offset, at_mid, warps,
        )
        print("midpath", pm)
        for a in pm or []:
            resp = sess.action(DIR_TO_ACTION[a])
            frame = resp["frame"]
        print(
            "after mid",
            ls20.init(frame).cursor,
            "ui",
            ls20.ui_energy(frame),
            "pu",
            ls20.energy_pickups(frame),
        )

        offset = ls20.grid_offset(frame)
        walk_u = ls20.build_walkable(frame, offset, armed=False)
        warps = ls20.detect_warps(frame, offset, walk_u)
        fuel0 = _fuel(ls20.ui_energy(frame))
        p47, _, _, _ = _energy_bfs(
            ls20.init(frame).cursor,
            fuel0,
            0,
            walk_u,
            [],
            offset,
            lambda c, _f, _p: c == (4, 7),
            warps,
        )
        print("p47", p47)
        for a in p47 or []:
            resp = sess.action(DIR_TO_ACTION[a])
            frame = resp["frame"]
        print("at47", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        for a in RITUAL:
            resp = sess.action(DIR_TO_ACTION[a])
            frame = resp["frame"]
        print("postH23", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))

        for i in range(40):
            path, _dest, _fuel_e, ainfo = _plan_armed_stamp_only(frame)
            if path is None:
                print("stamp fail", ainfo)
                break
            if len(path) == 0:
                print("empty path at", ls20.init(frame).cursor)
                break
            a = path[0]
            before = ls20.init(frame).cursor
            resp = sess.action(DIR_TO_ACTION[a])
            frame = resp["frame"]
            cur = ls20.init(frame).cursor
            ui = ls20.ui_energy(frame)
            lv = int(resp.get("levels_completed") or 0)
            print(f"{i} A{DIR_TO_ACTION[a]} {before}->{cur} ui={ui} lv={lv}")
            if lv > 3:
                print("CLEAR")
                break
            if before == cur and before == (2, 1):
                off = ls20.grid_offset(frame)
                print(
                    "gate no-op carry",
                    carrying_bbox_from_cursor(frame, before, off),
                    "ui",
                    ui,
                )
                break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
