"""Mirror-reflection hypothesis (AR25).

The ONLY place that knows about mirror lines and reflection. The generic
search calls cover/backproject without knowing the rule. Supports both vertical
and horizontal mirror lines; lines are movable, so this module also provides
candidate line positions for the search to iterate.

Interface:
    cover(rel_cells, pos, lines) -> set of covered cells
    backproject(rel_cells, targets, lines, w, h) -> candidate object positions
    line_candidates(grid_w, grid_h) -> candidate line coord values
"""
from __future__ import annotations

from typing import Iterable, List, Tuple


def _reflect(cell: Tuple[int, int], kind: str, coord: int) -> Tuple[int, int]:
    x, y = cell
    if kind == "V":
        return (2 * coord - x, y)
    return (x, 2 * coord - y)


def cover(
    rel_cells: Iterable[Tuple[int, int]],
    pos: Tuple[int, int],
    lines: Iterable[Tuple[str, int]],
    *,
    bounce_limit: int = 12,
) -> set:
    """Covered cells for object at pos, under given (kind, coord) lines."""
    lines = list(lines)
    bx, by = pos
    covered: set = set()
    seen: set = set()
    queue: List[Tuple[Tuple[int, int], int]] = []

    for cx, cy in rel_cells:
        seed = (bx + cx, by + cy)
        covered.add(seed)
        seen.add(seed)
        queue.append((seed, 0))

    while queue:
        (px, py), depth = queue.pop(0)
        if depth > bounce_limit:
            continue
        for kind, coord in lines:
            rx, ry = _reflect((px, py), kind, coord)
            if (rx, ry) in seen:
                continue
            seen.add((rx, ry))
            covered.add((rx, ry))
            queue.append(((rx, ry), depth + 1))
    return covered


def backproject(
    rel_cells: Iterable[Tuple[int, int]],
    targets: List[Tuple[int, int]],
    lines: Iterable[Tuple[str, int]],
    grid_w: int,
    grid_h: int,
) -> List[Tuple[int, int]]:
    """Object positions that could cover >=1 target (direct or single reflect)."""
    lines = list(lines)
    cands = set()
    for tx, ty in targets:
        for cx, cy in rel_cells:
            cands.add((tx - cx, ty - cy))
            for kind, coord in lines:
                rx, ry = _reflect((tx, ty), kind, coord)
                cands.add((rx - cx, ry - cy))
    valid = set()
    for bx, by in cands:
        if 0 <= bx < grid_w and 0 <= by < grid_h:
            valid.add((bx, by))
    return sorted(valid)


def line_candidates(grid_w: int, grid_h: int) -> List[int]:
    """Candidate coord values for a movable line (any board column/row)."""
    return list(range(max(grid_w, grid_h)))


__all__ = ["cover", "backproject", "line_candidates"]
