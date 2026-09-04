"""Longquan unified observation: game-agnostic, no AR25-specific fields.

The observation is a plain description of "what is on the board right now",
independent of any particular game's mechanics. Game-specific knowledge
(e.g. "axis", "mirror reflection") lives in the hypothesis-space modules
(hypotheses/), NOT in this data structure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class Obj:
    """A recognized object: a connected blob of cells on the board."""
    id: str
    color: int
    cells: List[Tuple[int, int]] = field(default_factory=list)  # board coords
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)  # min_x, min_y, max_x, max_y


@dataclass
class Obs:
    """One frame, reduced to game-agnostic structure."""
    grid_w: int
    grid_h: int
    objects: List[Obj] = field(default_factory=list)
    targets: List[Tuple[int, int]] = field(default_factory=list)
    selected_cells: List[Tuple[int, int]] = field(default_factory=list)
    # Line-like structures on the board (a hypothesis decides what they mean,
    # e.g. mirror axes). Raw structure, not a game concept.
    line_coords: List[int] = field(default_factory=list)
    legal_actions: List[int] = field(default_factory=list)
    steps_left: int = 0

    def cell_set(self) -> set:
        return {c for o in self.objects for c in o.cells}


__all__ = ["Obj", "Obs"]
