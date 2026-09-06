"""After L2 marker touch, can we enter armed-only stamp cell (2,8)?"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20, move, search
from longquan.interactive.state import WorldState
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import plan_two_phase, _ov_stamp
from tools._probe_l2_arm import clear_to_l2, locate_any


def main():
    sess = OnlineSession(_api_key())
    sess.open(tags=["ls20_arm_check"])
    try:
        frame, meta = clear_to_l2(sess)
        path, info = plan_two_phase(frame)
        # execute through first marker touch (path1_len)
        for i, d in enumerate(path[: info["path1_len"]], 1):
            out = sess.action(DIR_TO_ACTION[d])
            frame, meta = out["frame"], out
            print(f"p1 {i:02d} A{DIR_TO_ACTION[d]} {locate_any(frame)}")
        print("pickups left", ls20.energy_pickups(frame))
        # from here: plan to stamp assuming armed, with energy pickups still available
        offset = ls20.grid_offset(frame)
        st = ls20.init(frame)
        walk = ls20.build_walkable(frame, offset, armed=True)
        stamp = info["stamp"]
        state = WorldState(
            grid_w=64, grid_h=64, cursor=st.cursor, walkable=walk,
            carrying=st.carrying, goals=st.goals, steps_used=0, steps_limit=99, armed=True,
        )
        cands = [( _ov_stamp(c, offset, stamp), c) for c in walk if _ov_stamp(c, offset, stamp) >= 10]
        cands.sort(key=lambda t: (-t[0], t[1][0], t[1][1]))
        t2 = cands[0][1]
        found, path2 = search.bfs(state, move.actions, move.step, lambda s: s.cursor == t2)
        print("path2 found", found, "len", len(path2), "t2", t2)
        for i, d in enumerate(path2, 1):
            out = sess.action(DIR_TO_ACTION[d])
            frame, meta = out["frame"], out
            bb, shape = locate_any(frame)
            lv = meta.get("levels_completed")
            print(f"p2 {i:02d} A{DIR_TO_ACTION[d]} mover={bb} layers={shape[0]} lv={lv} c11={int((ls20._plane(frame)==11).sum())}")
            if int(lv or 0) >= 2:
                print("CLEARED — arming works")
                return
            if shape[0] > 1 and bb == (29, 40, 33, 41):
                print("soft-reset")
                return
        print("no clear — arming likely FAILED")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
