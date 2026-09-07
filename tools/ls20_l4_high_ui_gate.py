"""At (2,1) after UDD: if L blocked, refill via short loop, retry gate with high ui."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, RITUAL
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

    def at(cell, _f, _p):
        return cell == goal

    return _energy_bfs(state.cursor, fuel0, 0, walk, pickups, offset, at, warps)


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_high_ui_gate"])
        frame, meta = boot_l4(sess)
        for i in range(30):
            p, _, _, _ = plan_to(frame, (4, 7), armed=False)
            if not p:
                break
            if len(p) == 0:
                break
            resp = sess.action(DIR_TO_ACTION[p[0]])
            frame, meta = resp["frame"], resp
            if ls20.init(frame).cursor == (4, 7):
                break
        for a in RITUAL:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
        print("after ritual", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame),
              "carry", ls20.init(frame).carrying)
        # force pickup first
        for i in range(20):
            p_pu, _ = _plan_to_pickup(frame)
            if not p_pu:
                print("no pickup plan at", ls20.init(frame).cursor)
                break
            resp = sess.action(DIR_TO_ACTION[p_pu[0]])
            frame, meta = resp["frame"], resp
            ui = ls20.ui_energy(frame)
            print(f"fuel {i} ->", ls20.init(frame).cursor, "ui", ui)
            if ui >= 70:
                break
        print("fueled", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        # short path to stamp
        for i in range(20):
            path, dest, _, info = _plan_armed_stamp_only(frame)
            if not path:
                print("no stamp", info)
                break
            before = ls20.init(frame).cursor
            ui0 = ls20.ui_energy(frame)
            resp = sess.action(DIR_TO_ACTION[path[0]])
            frame, meta = resp["frame"], resp
            after = ls20.init(frame).cursor
            print(f"{i+1:02d} {before}->{after} ui={ls20.ui_energy(frame)} "
                  f"s9={stamp9(frame)[0]} carry={ls20.init(frame).carrying} "
                  f"lv={meta.get('levels_completed')}")
            if int(meta.get("levels_completed") or 0) >= 4:
                print("CLEARED")
                return
            if after == before == (2, 1):
                print("stuck at ui", ls20.ui_energy(frame))
                # try L explicitly once more
                break
        print("end", ls20.init(frame).cursor, ls20.ui_energy(frame))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
