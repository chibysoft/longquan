"""List pickups immediately after L4 unlock; try eat (20,16) then gate."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import RITUAL, MAX_FUEL, _energy_bfs
from tools.ls20_seated_clear_full import _plan_to_pickup, _plan_armed_stamp_only
from tools.ls20_l4_dd_ritual_probe import boot_l4
from tools.ls20_l4_stamp9_probe import stamp9


def plan_to(frame, goal, armed=False):
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk = ls20.build_walkable(frame, offset, armed=armed)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))
    return _energy_bfs(state.cursor, fuel0, 0, walk, pickups, offset,
                       lambda c, _f, _p: c == goal, warps)


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_mid_pickup"])
        frame, meta = boot_l4(sess)
        g = ls20._plane(frame)
        print("post_unlock pickups", ls20.energy_pickups(frame),
              "c11 playfield", int(np.sum(g[:54] == 11)),
              "at20_16", g[16:19, 20:23].tolist())
        # ritual via 47
        for _ in range(30):
            p, _, _, _ = plan_to(frame, (4, 7))
            if not p or len(p) == 0:
                break
            resp = sess.action(DIR_TO_ACTION[p[0]])
            frame, meta = resp["frame"], resp
            if ls20.init(frame).cursor == (4, 7):
                break
        print("at47 pickups", ls20.energy_pickups(frame), "ui", ls20.ui_energy(frame))
        for a in RITUAL:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
        print("after ritual pickups", ls20.energy_pickups(frame),
              "ui", ls20.ui_energy(frame), "cur", ls20.init(frame).cursor)
        # prefer mid pickup: plan_to_pickup should get nearest
        for i in range(25):
            pu = ls20.energy_pickups(frame)
            print(f"loop{i} pu={pu} cur={ls20.init(frame).cursor} ui={ls20.ui_energy(frame)}")
            p_pu, _ = _plan_to_pickup(frame)
            if not p_pu:
                # try walk to cell near (4,3) which is pickup (20,16) -> cursor ~ (3,3)
                p, _, _, _ = plan_to(frame, (3, 3), armed=True)
                if not p:
                    p, _, _, _ = plan_to(frame, (4, 3), armed=True)
                if not p:
                    print("cannot reach mid")
                    break
                resp = sess.action(DIR_TO_ACTION[p[0]])
                frame, meta = resp["frame"], resp
                continue
            resp = sess.action(DIR_TO_ACTION[p_pu[0]])
            frame, meta = resp["frame"], resp
            if ls20.ui_energy(frame) >= 70:
                print("REFILLED", ls20.init(frame).cursor, ls20.ui_energy(frame))
                break
        # now stamp with high ui - hope short
        for i in range(15):
            path, dest, _, info = _plan_armed_stamp_only(frame)
            if not path:
                print("no path", info)
                break
            before = ls20.init(frame).cursor
            resp = sess.action(DIR_TO_ACTION[path[0]])
            frame, meta = resp["frame"], resp
            after = ls20.init(frame).cursor
            print(f"{i+1:02d} {before}->{after} ui={ls20.ui_energy(frame)} "
                  f"s9={stamp9(frame)[0]} lv={meta.get('levels_completed')}")
            if int(meta.get("levels_completed") or 0) >= 4:
                print("CLEARED")
                return
            if after == before == (2, 1):
                print("STUCK ui", ls20.ui_energy(frame))
                break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
