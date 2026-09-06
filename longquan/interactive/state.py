"""Shared world state for interactive primitives.

Interactive rules are state machines: `step(state, action) -> state`. The
`WorldState` here is the GAME-AGNOSTIC state all interactive primitives operate
on. Each primitive's `step` mutates only the fields it owns (move touches only
`cursor` + `steps_used`; match touches only `goals`); composition is a sequence
of `step` calls, and the search drives it.

`WorldState` is a frozen dataclass so it's hashable (the BFS visited set needs
it) and immutable (no accidental cross-branch mutation during search).

This is the DRAFT structure from docs/primitive-interface-interactive.md §3.
Fields are filled in as primitives get proven on real games; do NOT pre-build
fields for sequence/gravity/waypoint before they're needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, FrozenSet, Tuple

# Action = a direction delta. Interactive primitives expose SEMANTIC actions
# (directions), NOT engine action ids; mapping semantic -> engine id is the
# motion layer's job (see longquan/motion.py UP/DOWN/LEFT/RIGHT).
Action = Tuple[int, int]

# The four cardinal move directions, in a stable order.
DIRS: Tuple[Action, ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))  # L, R, U, D


@dataclass(frozen=True)
class Piece:
    """A board piece that can move / be eliminated. Frozen so it's hashable."""
    id: str
    color: int
    cells: Tuple[Tuple[int, int], ...] = ()
    alive: bool = True


@dataclass(frozen=True)
class Goal:
    """A goal to satisfy: a target slot / cell / pair requirement."""
    id: str
    kind: str = "slot"          # "slot" / "cell" / "pair" (draft; expand on need)
    pos: Tuple[int, int] = (0, 0)
    shape: Any = None
    color: int = None
    rotation: Any = None
    done: bool = False


@dataclass(frozen=True)
class WorldState:
    """One state of an interactive game, game-agnostic.

    cursor   : position of the player/controllable object (move acts on it).
    walkable : set of cells the cursor may step onto (walls/obstacles excluded).
    carrying : what the player carries (shape/color/rotation), or None.
    goals    : the goals still to satisfy (match acts on these).
    steps_used / steps_limit : step budget (RHAE penalty is steps², so minimal
                               steps is the search objective).
    """
    grid_w: int
    grid_h: int
    cursor: Tuple[int, int] = None
    walkable: FrozenSet[Tuple[int, int]] = field(default_factory=frozenset)
    carrying: Any = None
    goals: Tuple[Goal, ...] = ()
    steps_used: int = 0
    steps_limit: int = 0
    armed: bool = False  # H19: visited color0/1 zone (carrying overlapped marker)
