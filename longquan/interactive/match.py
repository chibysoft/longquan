"""Match primitive — seated facts H5/H6 + H19/H20 (L1 clear).

SUPPORTED:
  H6  — color9 under color12 is carrying (tracks mover).
  H19 — visit color0/1 zone (carrying overlaps marker) then enter start-shape
        band => levels+1. Moves only; ACTION5 not required for clear.
  H20 — after arming at 0/1, UP from the shape-gate cell enters the former
        color9-blocked cell and clears.

H5 remains true as an ACTION5 side-effect (marker clear) but is NOT the
level-up rule.

Evidence: docs/ls20-match-hypotheses-h16.md + online two-phase probe.
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

from .state import Goal, WorldState

BBox = Tuple[int, int, int, int]
INTERACT = "interact"  # H5 side-effect only; not required for H19 clear


def score(obs) -> float:
    return 0.4


def actions(state: WorldState) -> List[Any]:
    # Level-clear path is move-composed; interact is optional (H5).
    return [INTERACT]


def _overlap(a: BBox, b: BBox) -> int:
    ox0, oy0 = max(a[0], b[0]), max(a[1], b[1])
    ox1, oy1 = min(a[2], b[2]), min(a[3], b[3])
    if ox0 <= ox1 and oy0 <= oy1:
        return (ox1 - ox0 + 1) * (oy1 - oy0 + 1)
    return 0


def carrying_bbox_from_cursor(cursor, offset) -> BBox:
    """H6: carrying top-left is (px, py+2) for a 5x3-ish blob under the 5x2 mover."""
    from . import ls20
    px, py = ls20.cursor_to_pixel(cursor, offset)
    return (px, py + 2, px + 4, py + 4)


def mover_bbox_from_cursor(cursor, offset) -> BBox:
    from . import ls20
    px, py = ls20.cursor_to_pixel(cursor, offset)
    return (px, py, px + 4, py + 1)


def react(state: WorldState, *, offset: Tuple[int, int]) -> WorldState:
    """Apply H19/H20 geometry after a move (no engine calls).

    Arm when carrying overlaps the marker goal bbox (stored in goal.shape).
    Stamp when armed and mover overlaps the stamp goal bbox.
    """
    marker = None
    stamp = None
    for g in state.goals:
        if g.id == "ls20-marker" and isinstance(g.shape, tuple) and len(g.shape) == 4:
            marker = g.shape
        if g.id == "ls20-stamp" and isinstance(g.shape, tuple) and len(g.shape) == 4:
            stamp = g.shape

    armed = state.armed
    if marker is not None and state.cursor is not None:
        cb = carrying_bbox_from_cursor(state.cursor, offset)
        if _overlap(cb, marker) > 0:
            armed = True

    new_goals = []
    stamped = False
    for g in state.goals:
        if (
            armed
            and g.id == "ls20-stamp"
            and stamp is not None
            and state.cursor is not None
            and _overlap(mover_bbox_from_cursor(state.cursor, offset), stamp) > 0
        ):
            new_goals.append(Goal(
                id=g.id, kind=g.kind, pos=g.pos, shape=g.shape,
                color=g.color, rotation=g.rotation, done=True,
            ))
            stamped = True
        else:
            new_goals.append(g)

    return WorldState(
        grid_w=state.grid_w,
        grid_h=state.grid_h,
        cursor=state.cursor,
        walkable=state.walkable,
        carrying=state.carrying,
        goals=tuple(new_goals),
        steps_used=state.steps_used,
        steps_limit=state.steps_limit,
        armed=armed,
    )


def step(state: WorldState, action) -> WorldState:
    """interact = H5 identity on WorldState (engine clears marker; we don't fake it)."""
    if action != INTERACT:
        raise ValueError(f"match: unknown action {action!r}")
    return state


def done(state: WorldState) -> bool:
    """H19/H20: stamped when the stamp goal is marked done."""
    stamps = [g for g in state.goals if g.id == "ls20-stamp"]
    if not stamps:
        return False
    return all(g.done for g in stamps)


def carrying_from_frame(frame, mover_bbox: Optional[Tuple[int, int, int, int]]):
    from . import ls20
    return ls20.carrying_near_mover(frame, mover_bbox)


__all__ = [
    "score", "actions", "step", "done", "react", "INTERACT",
    "carrying_from_frame", "carrying_bbox_from_cursor", "mover_bbox_from_cursor",
]
