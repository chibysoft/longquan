"""Translate primitive: the object moves by a fixed (dx, dy) vector.

The rule is "object(s) are shifted by the same offset". The free parameter is
the shift vector (dx, dy), enumerated by the search.

Interface (matches the primitive contract):
    score(obs) -> float
    cover(rel_cells, pos, param) -> set  (param = (dx, dy); here cover is just
        the object's own cells shifted, since translation doesn't add cells)
    backproject(rel_cells, targets, param, w, h) -> candidate positions
"""
from __future__ import annotations

from typing import Iterable, List, Tuple


def score(obs) -> float:
    """Match prior: translation games have objects + targets with a consistent
    offset relationship. Weak heuristic: objects present => moderate score."""
    if not getattr(obs, "objects", None):
        return 0.0
    return 0.4  # weak prior; translation is common but this is not a strong signal


def cover(
    rel_cells: Iterable[Tuple[int, int]],
    pos: Tuple[int, int],
    param,
) -> set:
    """Translation: the object occupies its own cells (shifted by pos). The
    'covered' cells are just the object at pos. param (dx,dy) is not used to
    add cells — translation preserves shape."""
    bx, by = pos
    return {(bx + cx, by + cy) for cx, cy in rel_cells}


def backproject(
    rel_cells: Iterable[Tuple[int, int]],
    targets: List[Tuple[int, int]],
    param,
    grid_w: int,
    grid_h: int,
) -> List[Tuple[int, int]]:
    """Object positions that put some cell onto a target (direct overlap)."""
    cands = set()
    for tx, ty in targets:
        for cx, cy in rel_cells:
            cands.add((tx - cx, ty - cy))
    valid = set()
    for bx, by in cands:
        if 0 <= bx < grid_w and 0 <= by < grid_h:
            valid.add((bx, by))
    return sorted(valid)


__all__ = ["score", "cover", "backproject"]
