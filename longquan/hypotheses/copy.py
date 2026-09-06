"""Copy primitive: an object is duplicated N times at offsets (UNVERIFIED).

The rule is "copy the source object onto every target position". The free
parameter `param` is the COMPLETE list of copy offsets [(dx, dy), ...] relative
to the source bbox origin; a copy at offset (dx, dy) occupies the source's
rel_cells shifted by pos + (dx, dy). The source object itself is always part of
the result (same contract as reflect's "source + mirror").

Interface (matches the primitive contract):
    score(obs) -> float
    cover(rel_cells, pos, param) -> set
    backproject(rel_cells, targets, param, w, h) -> candidate positions
"""
from __future__ import annotations

from typing import Iterable, List, Tuple


def score(obs) -> float:
    """Match prior: copy games show repeated identical shapes. Weak heuristic."""
    if not getattr(obs, "objects", None):
        return 0.0
    return 0.3  # weak prior; refine after exploring a real copy game


def _shape_at(rel_cells: Iterable[Tuple[int, int]], bx: int, by: int) -> set:
    """Board cells occupied by the shape when its bbox origin sits at (bx, by)."""
    return {(bx + cx, by + cy) for cx, cy in rel_cells}


def cover(
    rel_cells: Iterable[Tuple[int, int]],
    pos: Tuple[int, int],
    param: Iterable[Tuple[int, int]],
) -> set:
    """Covered cells for the object at pos: source itself plus every copy.

    `param` is the complete copy-offset list: one cover call answers for ALL
    copies, not a single one. Returns the union of source cells and the cells
    of each copy, all as board coordinates.
    """
    bx, by = pos
    covered = _shape_at(rel_cells, bx, by)
    for dx, dy in param:
        covered |= _shape_at(rel_cells, bx + dx, by + dy)
    return covered


def backproject(
    rel_cells: Iterable[Tuple[int, int]],
    targets: List[Tuple[int, int]],
    param: Iterable[Tuple[int, int]],
    grid_w: int,
    grid_h: int,
) -> List[Tuple[int, int]]:
    """Source bbox origins that could cover at least one target.

    A source origin is a candidate when the source itself or any copy can put
    one of its rel_cells onto a target cell. Off-grid origins are filtered out;
    the caller decides which candidates actually cover all targets via cover().
    """
    offsets = list(param)
    cands = set()
    for tx, ty in targets:
        for cx, cy in rel_cells:
            # Source itself covers the target.
            cands.add((tx - cx, ty - cy))
            # A copy shifted by (dx, dy) covers the target.
            for dx, dy in offsets:
                cands.add((tx - dx - cx, ty - dy - cy))
    valid = set()
    for bx, by in cands:
        if 0 <= bx < grid_w and 0 <= by < grid_h:
            valid.add((bx, by))
    return sorted(valid)


__all__ = ["score", "cover", "backproject"]
