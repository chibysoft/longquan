"""L2: can stamp alone clear? Does soft-reset preserve armed?"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20, move, search
from longquan.interactive.state import WorldState
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import _ov_stamp, plan_two_phase
from tools._probe_l2_arm import clear_to_l2, locate_any


def path_to_stamp(frame, armed=False):
    st = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk = ls20.build_walkable(frame, offset, armed=armed)
    stamp = [g.shape for g in st.goals if g.id == "ls20-stamp"][0]
    state = WorldState(
        grid_w=st.grid_w, grid_h=st.grid_h, cursor=st.cursor,
        walkable=walk, carrying=st.carrying, goals=st.goals,
        steps_used=0, steps_limit=99, armed=armed,
    )
    cands = [(_ov_stamp(c, offset, stamp), c) for c in walk if _ov_stamp(c, offset, stamp) > 0]
    cands.sort(key=lambda t: (-t[0], t[1][0], t[1][1]))
    t2 = cands[0][1]
    found, path = search.bfs(state, move.actions, move.step, lambda s: s.cursor == t2)
    return found, path, t2, stamp


def main():
    sess = OnlineSession(_api_key())
    sess.open(tags=["ls20_stamp_only"])
    try:
        frame, meta = clear_to_l2(sess)
        found, path, t2, stamp = path_to_stamp(frame, armed=False)
        print("unarmed path to stamp", found, "len", len(path) if found else None, "t2", t2)
        # try armed path length without going to marker first - may be shorter through 9s
        found_a, path_a, t2a, _ = path_to_stamp(frame, armed=True)
        print("armed-as-if path to stamp", found_a, "len", len(path_a) if found_a else None, "t2", t2a)
        if found and len(path) <= 19:
            for i, d in enumerate(path, 1):
                out = sess.action(DIR_TO_ACTION[d])
                frame, meta = out["frame"], out
                bb, shape = locate_any(frame)
                lv = meta.get("levels_completed")
                print(f"{i:02d} A{DIR_TO_ACTION[d]} mover={bb} lv={lv} layers={shape[0]}")
                if int(lv or 0) >= 2:
                    print("CLEARED WITHOUT ARM")
                    return
                if shape[0] > 1:
                    print("flash")
                    break
        else:
            print("skip stamp-only exec; too long or unreachable unarmed")
            # Instead: arm, flash, check if still armed after respawn by trying short stamp path
            path2, info = plan_two_phase(frame)
            for d in path2[: info["path1_len"]]:
                out = sess.action(DIR_TO_ACTION[d])
                frame, meta = out["frame"], out
            print("armed at", locate_any(frame))
            # burn to flash
            while True:
                out = sess.action(1)
                frame, meta = out["frame"], out
                bb, shape = locate_any(frame)
                if shape[0] > 1:
                    print("flashed, mover", bb)
                    break
            # after flash, try walk into a formerly color9-only cell near stamp
            # if armed preserved, armed walkable cells that were blocked unarmed become enterable
            out = sess.action(2)  # settle after flash
            frame, meta = out["frame"], out
            print("post-flash", locate_any(frame), "carry", ls20.carrying_near_mover(frame))
            found, path, t2, stamp = path_to_stamp(frame, armed=True)
            print("post-flash armed path len", len(path) if found else None)
            # compare: can we enter a cell that is unarmed-blocked?
            walk_u = ls20.build_walkable(frame, ls20.grid_offset(frame), armed=False)
            walk_a = ls20.build_walkable(frame, ls20.grid_offset(frame), armed=True)
            only_a = walk_a - walk_u
            print("armed-only cells", len(only_a), "sample", list(only_a)[:8])
    finally:
        sess.close()


if __name__ == "__main__":
    main()
