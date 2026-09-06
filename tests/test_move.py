"""Offline unit tests for the move primitive + state-space BFS.

These test the ABSTRACT state-machine skeleton (WorldState + move.step/actions
+ search.bfs) with hand-built states — NOT a real ls20 frame. The frame->state
extraction (init) is cognition work still to come; these tests pin down the
transfer/search machinery it will plug into.
"""
from __future__ import annotations

import pytest

from longquan.interactive import move, search
from longquan.interactive.state import WorldState


def _corridor(w=5, h=1, cursor=(0, 0)):
    """A 1-row corridor of walkable cells from (0,0) to (w-1,0)."""
    walkable = frozenset((x, 0) for x in range(w))
    return WorldState(grid_w=w, grid_h=1, cursor=cursor, walkable=walkable,
                      steps_limit=64)


def test_step_moves_into_walkable():
    s = _corridor(cursor=(1, 0))
    s2 = move.step(s, (1, 0))  # right
    assert s2.cursor == (2, 0)
    assert s2.steps_used == 1
    # input state untouched (immutable)
    assert s.cursor == (1, 0) and s.steps_used == 0


def test_step_blocked_by_wall_stays_and_burns_step():
    s = _corridor(cursor=(0, 0))
    s2 = move.step(s, (-1, 0))  # left, off-grid / wall
    assert s2.cursor == (0, 0)      # stays put
    assert s2.steps_used == 1       # but the turn is consumed


def test_step_rejects_unknown_direction():
    s = _corridor()
    with pytest.raises(ValueError):
        move.step(s, (1, 1))


def test_actions_lists_only_walkable_directions():
    s = _corridor(cursor=(1, 0))
    got = set(move.actions(s))
    assert got == {(-1, 0), (1, 0)}  # only left & right (1-row corridor)


def test_actions_empty_when_boxed_in():
    s = _corridor(w=1, cursor=(0, 0))
    assert move.actions(s) == []


def test_move_done_is_always_false():
    s = _corridor()
    assert move.done(s) is False


def test_bfs_finds_minimal_path():
    # 5-cell corridor, goal = reach the far end. done is "cursor == (4,0)".
    init = _corridor(w=5, cursor=(0, 0))

    def done(s):
        return s.cursor == (4, 0)

    found, path = search.bfs(init, move.actions, move.step, done)
    assert found
    assert len(path) == 4            # minimal: 4 right-steps
    assert all(a == (1, 0) for a in path)


def test_bfs_reports_unreachable():
    # Two disconnected rooms; goal is in the far room, unreachable from here.
    walkable = frozenset({(0, 0), (0, 1)})  # cursor room
    init = WorldState(grid_w=3, grid_h=3, cursor=(0, 0), walkable=walkable,
                      steps_limit=16)

    def done(s):
        return s.cursor == (2, 2)  # not walkable, never reachable

    found, path = search.bfs(init, move.actions, move.step, done)
    assert not found
    assert path == []


def test_bfs_respects_step_budget():
    # Goal is 5 steps away but budget is 2 -> must fail.
    init = _corridor(w=6, cursor=(0, 0))
    init = WorldState(grid_w=6, grid_h=1, cursor=(0, 0),
                      walkable=frozenset((x, 0) for x in range(6)),
                      steps_limit=2)

    def done(s):
        return s.cursor == (5, 0)

    found, _ = search.bfs(init, move.actions, move.step, done)
    assert not found
