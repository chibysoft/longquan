"""Longquan unified observation: game-agnostic, no AR25-specific fields."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class Obj:
    """A recognized object: a connected blob of cells on the board."""
    id: str
    color: int
    cells: List[Tuple[int, int]] = field(default_factory=list)
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)


@dataclass
class Line:
    """A line-like structure. kind is 'V' (vertical, at x=coord) or 'H' (horizontal, at y=coord)."""
    kind: str
    coord: int


@dataclass
class Obs:
    """One frame, reduced to game-agnostic structure."""
    grid_w: int
    grid_h: int
    objects: List[Obj] = field(default_factory=list)
    targets: List[Tuple[int, int]] = field(default_factory=list)
    selected_cells: List[Tuple[int, int]] = field(default_factory=list)
    lines: List[Line] = field(default_factory=list)
    legal_actions: List[int] = field(default_factory=list)
    steps_left: int = 0

    def cell_set(self) -> set:
        return {c for o in self.objects for c in o.cells}


__all__ = ["Obj", "Line", "Obs"]
