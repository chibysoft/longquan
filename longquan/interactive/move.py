"""Move primitive: the cursor/controllable object moves one step per action.

The rule fragment "move" only knows how the cursor steps through the walkable
area. It does NOT know goals or matching (that's the `match` primitive); a
real game = move + match composed by the search. Hence `done` is always False
here — moving alone never clears a goal.

Interface (state machine, see docs/primitive-interface-interactive.md):
    score(obs) -> float
    init(...)  -> WorldState   (TODO: frame->state is cognition, not yet done)
    actions(state) -> [Action]
    step(state, action) -> WorldState
    done(state) -> bool
"""
from __future__ import annotations

from typing import List

from .state import DIRS, Action, WorldState


def score(obs) -> float:
    """Match prior: does the observation look like a move game?

    Weak placeholder — a real move detector reads "a controllable cursor +
    a walkable floor + walls" from the frame. Until the frame->state extraction
    exists, this returns a neutral prior so the selector doesn't over-favor it.
    """
    return 0.3


def actions(state: WorldState) -> List[Action]:
    """Directions the cursor can actually move this step (walkable, in-bounds)."""
    out: List[Action] = []
    cx, cy = state.cursor
    for dx, dy in DIRS:
        if (cx + dx, cy + dy) in state.walkable:
            out.append((dx, dy))
    return out


def step(state: WorldState, action: Action) -> WorldState:
    """Apply one move. Cursor steps in `action` if walkable, else stays put.

    Every action consumes one step of budget (even a blocked move — matching
    engine semantics where a wall push still burns a turn). Returns a NEW
    WorldState; the input is untouched.
    """
    if action not in DIRS:
        raise ValueError(f"move: unknown direction {action!r}")
    dx, dy = action
    cx, cy = state.cursor
    nxt = (cx + dx, cy + dy)
    cursor = nxt if nxt in state.walkable else (cx, cy)
    return WorldState(
        grid_w=state.grid_w,
        grid_h=state.grid_h,
        cursor=cursor,
        walkable=state.walkable,
        carrying=state.carrying,
        goals=state.goals,
        steps_used=state.steps_used + 1,
        steps_limit=state.steps_limit,
        armed=state.armed,
    )


def done(state: WorldState) -> bool:
    """Move alone never clears a goal; termination comes from match/others."""
    return False


__all__ = ["score", "actions", "step", "done"]
