"""Mirror-reflection hypothesis (AR25): the game rule as a cover function.

This is the ONLY place that knows about mirror axes and reflection. The generic
search in `search.py` calls `cover()` without knowing what the rule is. To port
Longquan to a new game, write a new hypothesis module with the same interface.

Interface:
    cover(obj_cells, pos, axes) -> set of covered board cells
    backproject(obj_cells, targets, axes, grid_w, grid_h) -> candidate positions
"""
from __future__ import annotations

from typing import Iterable, List, Tuple


def reflect(cell: Tuple[int, int], axis: int, vertical: bool) -> Tuple[int, int]:
    """Mirror a single cell over a vertical (x=axis) or horizontal (y=axis) line."""
    x, y = cell
    if vertical:
        return (2 * axis - x, y)
    return (x, 2 * axis - y)


def cover(
    obj_cells: Iterable[Tuple[int, int]],
    pos: Tuple[int, int],
    axes: Iterable[int],
    *,
    vertical: bool = True,
    bounce_limit: int = 12,
) -> set:
    """All cells covered by the object at pos, including recursive reflection.

    obj_cells are relative offsets from the object's top-left; pos is that
    top-left in board coords. axes are the mirror-axis positions.
    """
    bx, by = pos
    covered: set = set()
    seen: set = set()
    queue: List[Tuple[Tuple[int, int], int]] = []

    for cx, cy in obj_cells:
        seed = (bx + cx, by + cy)
        covered.add(seed)
        seen.add(seed)
        queue.append((seed, 0))

    while queue:
        (px, py), depth = queue.pop(0)
        if depth > bounce_limit:
            continue
        for ax in axes:
            rx, ry = reflect((px, py), ax, vertical)
            if (rx, ry) in seen:
                continue
            seen.add((rx, ry))
            covered.add((rx, ry))
            queue.append(((rx, ry), depth + 1))
    return covered


def backproject(
    obj_cells: Iterable[Tuple[int, int]],
    targets: List[Tuple[int, int]],
    axes: Iterable[int],
    grid_w: int,
    grid_h: int,
    *,
    vertical: bool = True,
) -> List[Tuple[int, int]]:
    """Object top-left positions that could cover >=1 target (direct or single reflect)."""
    axes = list(axes)
    cands = set()
    for tx, ty in targets:
        for cx, cy in obj_cells:
            cands.add((tx - cx, ty - cy))
            for ax in axes:
                rx, ry = reflect((tx, ty), ax, vertical)
                cands.add((rx - cx, ry - cy))
    valid = set()
    for bx, by in cands:
        if 0 <= bx < grid_w and 0 <= by < grid_h:
            valid.add((bx, by))
    return sorted(valid)


__all__ = ["cover", "backproject", "reflect"]
