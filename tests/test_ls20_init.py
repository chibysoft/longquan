"""Offline tests for the ls20 frame adapter (init) + move.step + BFS.

These pin the frame->state extraction against a LIVE probe frame
(tests/fixtures/ls20_l1_frame_live.json) — the same frame the online probe
observed, so the walkable model can be checked against the measured
four-direction reach (UP 6 / DOWN 0 / LEFT 3 / RIGHT 3).

This is design-time reference, not a runtime input to any learner (red line 1):
the tests read a frozen frame file, never the engine source.
"""
from __future__ import annotations

import json
import os

import pytest

from longquan.interactive import ls20, move, search
from longquan.interactive.state import WorldState

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ls20_l1_frame_live.json")


@pytest.fixture(scope="module")
def state():
    with open(FIXTURE) as f:
        data = json.load(f)
    return ls20.init(data["frame"])


def _reach(state, d):
    """How many steps in direction d before hitting a non-walkable cell."""
    cx, cy = state.cursor
    n = 0
    while (cx + d[0], cy + d[1]) in state.walkable:
        cx, cy = cx + d[0], cy + d[1]
        n += 1
    return n


def test_init_extracts_cursor(state):
    # moving object anchor (34,45) on a 5px grid with offset (4,0) -> (6,9)
    assert state.cursor == (6, 9)


def test_init_walkable_matches_live_reach(state):
    # The online probe measured: UP 6, DOWN 0, LEFT 3, RIGHT 3 steps.
    assert _reach(state, (0, -1)) == 6   # up
    assert _reach(state, (0, +1)) == 0   # down (wall right below)
    assert _reach(state, (-1, 0)) == 3   # left
    assert _reach(state, (+1, 0)) == 3   # right


def test_init_records_goal_marker(state):
    assert any(g.id == "ls20-marker" for g in state.goals)
    m = next(g for g in state.goals if g.id == "ls20-marker")
    # goal marker color 0/1 bbox top-left is (20,31) in pixel coords
    assert m.pos == (20, 31)
    assert m.shape == (20, 31, 22, 33)
    assert any(g.id == "ls20-stamp" for g in state.goals)


def test_step_moves_on_logical_grid(state):
    s2 = move.step(state, (0, -1))  # up
    assert s2.cursor == (6, 8)
    assert s2.steps_used == 1


def test_step_blocked_does_not_move(state):
    s2 = move.step(state, (0, 1))  # down — wall, no move
    assert s2.cursor == (6, 9)
    assert s2.steps_used == 1       # but the turn burns


def test_bfs_reaches_far_cell_minimally(state):
    # The goal marker sits at pixel (20,31); the nearest walkable logical cell
    # to it is a target we can plan toward. BFS must find a shortest path and
    # its length must equal the grid distance (uniform cost -> BFS optimal).
    target = (4, 9)  # a walkable cell to the upper-left; reachable
    assert target in state.walkable

    def done(s):
        return s.cursor == target

    found, path = search.bfs(state, move.actions, move.step, done)
    assert found
    assert len(path) == abs(6 - 4) + abs(9 - 9)  # manhattan, minimal
    # replay the path to confirm it lands exactly on target
    s = state
    for a in path:
        s = move.step(s, a)
    assert s.cursor == target


def test_bfs_respects_step_limit(state):
    target = (4, 9)

    def done(s):
        return s.cursor == target

    # budget too small to reach -> fail
    found, _ = search.bfs(state, move.actions, move.step, done, max_steps=1)
    assert not found
