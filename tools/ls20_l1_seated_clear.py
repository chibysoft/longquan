"""Seated L1 clear planner (H19/H20) — no canned action table.

Phase 1: BFS to color0/1 neighborhood (arm).
Phase 2: rebuild walkable with armed=True; BFS to max overlap with stamp block.
Execute online; require levels_completed >= 1.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20, match, move, search
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_probe_lib import nearest_walkable


def plan_two_phase(frame):
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    marker = next(g for g in state.goals if g.id == "ls20-marker").shape
    stamp = next(g for g in state.goals if g.id == "ls20-stamp").shape

    t1, _ = nearest_walkable(
        state, offset,
        (marker[0] + marker[2]) // 2, (marker[1] + marker[3]) // 2,
    )
    found, path1 = search.bfs(state, move.actions, move.step, lambda s: s.cursor == t1)
    if not found:
        raise RuntimeError("phase1 unreachable")
    for a in path1:
        state = move.step(state, a)
        state = match.react(state, offset=offset)
    if not state.armed:
        raise RuntimeError("phase1 did not arm")

    walk2 = ls20.build_walkable(frame, offset, armed=True)
    state = type(state)(
        grid_w=state.grid_w, grid_h=state.grid_h, cursor=state.cursor,
        walkable=walk2, carrying=state.carrying, goals=state.goals,
        steps_used=state.steps_used, steps_limit=state.steps_limit, armed=True,
    )

    def ov(cell):
        px, py = ls20.cursor_to_pixel(cell, offset)
        bb = (px, py, px + 4, py + 1)
        ox0, oy0 = max(bb[0], stamp[0]), max(bb[1], stamp[1])
        ox1, oy1 = min(bb[2], stamp[2]), min(bb[3], stamp[3])
        if ox0 <= ox1 and oy0 <= oy1:
            return (ox1 - ox0 + 1) * (oy1 - oy0 + 1)
        return 0

    cands = [(ov(c), c) for c in walk2 if ov(c) > 0]
    cands.sort(key=lambda t: (-t[0], t[1][0], t[1][1]))
    t2 = cands[0][1]
    found, path2 = search.bfs(state, move.actions, move.step, lambda s: s.cursor == t2)
    if not found:
        raise RuntimeError("phase2 unreachable")
    return path1 + path2, t1, t2


def main() -> int:
    key = _api_key()
    sess = OnlineSession(key)
    try:
        sess.open(tags=["ls20_l1_seated_clear"])
        reset = sess.reset()
        frame, meta = reset["frame"], reset
        path, t1, t2 = plan_two_phase(frame)
        print(f"plan phase1_target={t1} phase2_target={t2} len={len(path)}")
        print("actions", [DIR_TO_ACTION[a] for a in path])
        for i, a in enumerate(path, 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            lv = int(meta.get("levels_completed") or 0)
            print(f"{i:02d} ACTION{DIR_TO_ACTION[a]} bbox={ls20.locate_mover(frame)} lv={lv}")
            if lv >= 1:
                print("PASS levels>=1")
                return 0
        print("FAIL levels still", meta.get("levels_completed"))
        return 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
