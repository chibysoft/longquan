"""Offline + composition tests for H19/H20 match clear."""
from __future__ import annotations

import json
import os

import pytest

from longquan.interactive import ls20, match, move, search

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ls20_l1_frame_live.json")


@pytest.fixture
def frame():
    with open(FIXTURE) as f:
        return json.load(f)["frame"]


def test_match_done_false_until_stamp(frame):
    s = ls20.init(frame)
    assert match.done(s) is False


def test_h19_arm_on_marker_overlap(frame):
    s = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    # path to nearest walkable to marker
    marker = next(g for g in s.goals if g.id == "ls20-marker").shape
    cx, cy = (marker[0] + marker[2]) // 2, (marker[1] + marker[3]) // 2
    best = None
    for cell in s.walkable:
        px, py = ls20.cursor_to_pixel(cell, offset)
        d = abs(px - cx) + abs(py - cy)
        if best is None or d < best[0]:
            best = (d, cell)
    target = best[1]
    found, path = search.bfs(s, move.actions, move.step, lambda st: st.cursor == target)
    assert found
    for a in path:
        s = move.step(s, a)
        s = match.react(s, offset=offset)
    assert s.armed is True
    assert match.done(s) is False


def test_h20_stamp_after_arm_with_expanded_walkable(frame):
    s = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    marker = next(g for g in s.goals if g.id == "ls20-marker").shape
    stamp = next(g for g in s.goals if g.id == "ls20-stamp").shape
    # phase 1
    cx, cy = (marker[0] + marker[2]) // 2, (marker[1] + marker[3]) // 2
    best = None
    for cell in s.walkable:
        px, py = ls20.cursor_to_pixel(cell, offset)
        d = abs(px - cx) + abs(py - cy)
        if best is None or d < best[0]:
            best = (d, cell)
    found, path = search.bfs(s, move.actions, move.step, lambda st: st.cursor == best[1])
    assert found
    for a in path:
        s = move.step(s, a)
        s = match.react(s, offset=offset)
    assert s.armed

    # expand walkable (H20)
    walk2 = ls20.build_walkable(frame, offset, armed=True)
    s = type(s)(
        grid_w=s.grid_w, grid_h=s.grid_h, cursor=s.cursor, walkable=walk2,
        carrying=s.carrying, goals=s.goals, steps_used=s.steps_used,
        steps_limit=s.steps_limit, armed=True,
    )
    # target: max overlap with stamp
    def ov(cell):
        px, py = ls20.cursor_to_pixel(cell, offset)
        bb = (px, py, px + 4, py + 1)
        ox0, oy0 = max(bb[0], stamp[0]), max(bb[1], stamp[1])
        ox1, oy1 = min(bb[2], stamp[2]), min(bb[3], stamp[3])
        if ox0 <= ox1 and oy0 <= oy1:
            return (ox1 - ox0 + 1) * (oy1 - oy0 + 1)
        return 0
    cands = [(ov(c), c) for c in walk2 if ov(c) > 0]
    assert cands
    cands.sort(key=lambda t: (-t[0], t[1][0], t[1][1]))
    target = cands[0][1]
    found, path = search.bfs(s, move.actions, move.step, lambda st: st.cursor == target)
    assert found
    for a in path:
        s = move.step(s, a)
        s = match.react(s, offset=offset)
    assert match.done(s)
