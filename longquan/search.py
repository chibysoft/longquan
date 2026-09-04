"""Longquan configuration-space search (generic, game-agnostic).

Searches the CONFIGURATION space (where objects end up), never the action tree.
Uses target decomposition for multi-object scenes: fix the coupling variables,
solve each object independently, combine via target bitmasks.

The game rule is injected as `cover` / `backproject` callbacks (see
hypotheses/mirror.py), so this module knows nothing about mirror axes,
reflection, etc. Object cells are ABSOLUTE board coords; this module converts
them to offsets before calling the hypothesis (which expects offsets).
"""
from __future__ import annotations

from typing import Callable, Dict, List, Tuple

from .obs import Obs

CoverFn = Callable[[List[Tuple[int, int]], Tuple[int, int], List[int]], set]
BackprojectFn = Callable[
    [List[Tuple[int, int]], List[Tuple[int, int]], List[int], int, int],
    List[Tuple[int, int]],
]


def _target_bitmap(covered: set, target_index: Dict[Tuple[int, int], int]) -> int:
    bm = 0
    for cell in covered:
        i = target_index.get(cell)
        if i is not None:
            bm |= (1 << i)
    return bm


def solve_configs(
    obs: Obs,
    axes: List[int],
    cover: CoverFn,
    backproject: BackprojectFn,
    *,
    max_solutions: int = 8,
) -> List[Dict[str, Tuple[int, int]]]:
    """Return configs {obj_id: pos} whose union covers all targets."""
    targets_sorted = sorted(obs.targets)
    target_index = {t: i for i, t in enumerate(targets_sorted)}
    all_mask = (1 << len(targets_sorted)) - 1
    if all_mask == 0:
        return [{}]

    movable = list(obs.objects)
    if not movable:
        return []

    per_obj: List[List[Tuple[Tuple[int, int], int]]] = []
    for obj in movable:
        origin = (obj.bbox[0], obj.bbox[1])
        rel_cells = [(x - origin[0], y - origin[1]) for x, y in obj.cells]
        cands = backproject(rel_cells, targets_sorted, axes, obs.grid_w, obs.grid_h)
        entries = []
        for pos in cands:
            bm = _target_bitmap(cover(rel_cells, pos, axes), target_index)
            if bm:
                entries.append((pos, bm))
        per_obj.append(entries)

    solutions: List[Dict[str, Tuple[int, int]]] = []

    def combine(idx: int, cfg: Dict[str, Tuple[int, int]], bm: int) -> None:
        if len(solutions) >= max_solutions:
            return
        if bm == all_mask:
            solutions.append(dict(cfg))
            return
        if idx >= len(movable):
            return
        obj = movable[idx]
        for pos, m in per_obj[idx]:
            combine(idx + 1, {**cfg, obj.id: pos}, bm | m)
            if len(solutions) >= max_solutions:
                return

    combine(0, {}, 0)
    return solutions


__all__ = ["solve_configs"]
