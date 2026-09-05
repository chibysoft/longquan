"""Longquan configuration-space search (generic, game-agnostic).

Searches the CONFIGURATION space (where lines and objects end up), never the
action tree. Uses target decomposition: iterate line positions (the coupling
variables), then solve objects independently and combine via bitmasks.

Game rule injected as cover/backproject/line_candidates callbacks.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Tuple

from .obs import Obs

CoverFn = Callable[[List[Tuple[int, int]], Tuple[int, int], List[Tuple[str, int]]], set]
BackprojectFn = Callable[
    [List[Tuple[int, int]], List[Tuple[int, int]], List[Tuple[str, int]], int, int],
    List[Tuple[int, int]],
]
LineCandidatesFn = Callable[[int, int], List[int]]


def _target_bitmap(covered: set, target_index: Dict[Tuple[int, int], int]) -> int:
    bm = 0
    for cell in covered:
        i = target_index.get(cell)
        if i is not None:
            bm |= (1 << i)
    return bm


def _search_objects(obs, lines, cover, backproject, target_index, all_mask,
                    max_solutions):
    """For fixed line positions, find object configs covering all targets."""
    targets_sorted = sorted(obs.targets)
    per_obj = []
    for obj in obs.objects:
        origin = (obj.bbox[0], obj.bbox[1])
        rel_cells = [(x - origin[0], y - origin[1]) for x, y in obj.cells]
        cands = backproject(rel_cells, targets_sorted, lines, obs.grid_w, obs.grid_h)
        entries = []
        for pos in cands:
            bm = _target_bitmap(cover(rel_cells, pos, lines), target_index)
            if bm:
                entries.append((pos, bm))
        per_obj.append(entries)

    solutions = []

    def combine(idx, cfg, bm):
        if len(solutions) >= max_solutions:
            return
        if bm == all_mask:
            solutions.append(dict(cfg))
            return
        if idx >= len(obs.objects):
            return
        obj = obs.objects[idx]
        for pos, m in per_obj[idx]:
            combine(idx + 1, {**cfg, obj.id: pos}, bm | m)
            if len(solutions) >= max_solutions:
                return

    combine(0, {}, 0)
    return solutions


def solve_configs(
    obs: Obs,
    lines: List[Tuple[str, int]],
    cover: CoverFn,
    backproject: BackprojectFn,
    *,
    line_candidates: LineCandidatesFn = None,
    max_solutions: int = 8,
) -> List[Dict]:
    """Return configs. Each config is {obj_id: pos} plus a special '_lines' key
    holding the chosen line positions [(kind, coord), ...]."""
    targets_sorted = sorted(obs.targets)
    target_index = {t: i for i, t in enumerate(targets_sorted)}
    all_mask = (1 << len(targets_sorted)) - 1
    if all_mask == 0:
        return [{"_lines": lines}]

    if not obs.objects:
        return []

    # Iterate line positions. For lines already detected as movable, try all
    # candidates; if line_candidates is None, keep the observed lines fixed.
    line_options = [lines]  # default: keep observed
    if line_candidates is not None and lines:
        for i, (kind, _) in enumerate(lines):
            for cand in line_candidates(obs.grid_w, obs.grid_h):
                alt = list(lines)
                alt[i] = (kind, cand)
                line_options.append(alt)

    results = []
    seen = set()
    for ls in line_options:
        sols = _search_objects(obs, ls, cover, backproject, target_index,
                               all_mask, max_solutions)
        for cfg in sols:
            key = repr(sorted(cfg.items()))
            if key in seen:
                continue
            seen.add(key)
            cfg["_lines"] = ls
            results.append(cfg)
            if len(results) >= max_solutions:
                return results
    return results


__all__ = ["solve_configs"]
