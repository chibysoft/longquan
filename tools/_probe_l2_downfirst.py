"""Probe: after L2 arm, go DOWN first (recording-like) then up to stamp."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import plan_two_phase
from tools._probe_l2_arm import clear_to_l2, locate_any


def main():
    sess = OnlineSession(_api_key())
    sess.open(tags=["ls20_down_first"])
    try:
        frame, meta = clear_to_l2(sess)
        path, info = plan_two_phase(frame)
        for d in path[: info["path1_len"]]:
            out = sess.action(DIR_TO_ACTION[d])
            frame, meta = out["frame"], out
        print("at marker", locate_any(frame))
        # DOWN once like recording
        for aid, label in [(2, "down"), (2, "down2"), (1, "up"), (1, "up2"), (1, "up3"),
                           (1, "up4"), (1, "up5"), (1, "up6"), (1, "up7"), (1, "up8"),
                           (1, "up9"), (1, "up10")]:
            out = sess.action(aid)
            frame, meta = out["frame"], out
            bb, shape = locate_any(frame)
            print(f"{label} A{aid} mover={bb} layers={shape[0]} lv={meta.get('levels_completed')}")
            if shape[0] > 1:
                print("SOFT RESET")
                break
        # if still alive, replan phase2 from here
        if np.asarray(frame).shape[0] == 1:
            st = ls20.init(frame)
            # force armed
            from longquan.interactive.state import WorldState
            offset = ls20.grid_offset(frame)
            walk2 = ls20.build_walkable(frame, offset, armed=True)
            stamp = [g for g in st.goals if g.id == "ls20-stamp"][0].shape
            # import plan helper
            from tools.ls20_seated_clear import _ov_stamp
            from longquan.interactive import move, search, match
            state = WorldState(
                grid_w=st.grid_w, grid_h=st.grid_h, cursor=st.cursor,
                walkable=walk2, carrying=st.carrying, goals=st.goals,
                steps_used=0, steps_limit=st.steps_limit, armed=True,
            )
            cands = [(_ov_stamp(c, offset, stamp), c) for c in walk2 if _ov_stamp(c, offset, stamp) > 0]
            cands.sort(key=lambda t: (-t[0], t[1][0], t[1][1]))
            t2 = cands[0][1]
            found, path2 = search.bfs(state, move.actions, move.step, lambda s: s.cursor == t2)
            print("phase2 found", found, "t2", t2, "len", len(path2) if found else None)
            if found:
                for i, d in enumerate(path2, 1):
                    out = sess.action(DIR_TO_ACTION[d])
                    frame, meta = out["frame"], out
                    bb, shape = locate_any(frame)
                    lv = meta.get("levels_completed")
                    print(f"p2 {i:02d} A{DIR_TO_ACTION[d]} mover={bb} layers={shape[0]} lv={lv}")
                    if int(lv or 0) >= 2:
                        print("PASS L2")
                        break
                    if shape[0] > 1:
                        print("SOFT RESET in p2")
                        break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
