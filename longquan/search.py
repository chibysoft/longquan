"""Longquan configuration-space search (generic, game-agnostic).

Searches the CONFIGURATION space (where lines and objects end up), never the
action tree. Uses target decomposition: iterate line positions (the coupling
variables), then solve objects independently and combine via bitmasks.

Game rule injected as cover/backproject/line_candidates callbacks.
Object cells are ABSOLUTE board coords; this module converts them to offsets
before calling the hypothesis (which expects offsets).
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


def _search_objects(obs, lines, cover, backproject, target_index, all_mask):
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
        if bm == all_mask:
            solutions.append(dict(cfg))
            return
        if idx >= len(obs.objects):
            return
        obj = obs.objects[idx]
        for pos, m in per_obj[idx]:
            combine(idx + 1, {**cfg, obj.id: pos}, bm | m)

    combine(0, {}, 0)
    return solutions


def _config_cost(obs, cfg):
    """Total moves: line moves + object moves. Every move is a real action."""
    cost = 0
    lines = cfg.get("_lines", [])
    cur_lines = {ln.kind: ln.coord for ln in obs.lines}
    for kind, coord in lines:
        cur = cur_lines.get(kind, 0)
        cost += abs(coord - cur)
    for obj in obs.objects:
        if obj.id not in cfg:
            continue
        tx, ty = cfg[obj.id]
        cx, cy = obj.bbox[0], obj.bbox[1]
        cost += abs(tx - cx) + abs(ty - cy)
    return cost


def solve_configs(
    obs: Obs,
    lines: List[Tuple[str, int]],
    cover: CoverFn,
    backproject: BackprojectFn,
    *,
    line_candidates: LineCandidatesFn = None,
    max_solutions: int = 8,
) -> List[Dict]:
    """Return configs sorted by cost (ascending).

    Line positions are candidates ONLY for movable lines; fixed lines stay put.
    The caller passes `lines` as [(kind, coord), ...] plus the movable flag is
    carried on obs.lines (matched by kind+coord).

    Iterates all movable-line candidate positions; for each, finds object
    configs covering all targets; collects all valid configs; sorts by cost.
    """
    targets_sorted = sorted(obs.targets)
    target_index = {t: i for i, t in enumerate(targets_sorted)}
    all_mask = (1 << len(targets_sorted)) - 1
    if all_mask == 0:
        return [{"_lines": lines}]

    if not obs.objects:
        return []

    # Which lines are movable? Match obs.lines (has .movable) to passed lines.
    movable_flags = []
    for kind, coord in lines:
        movable = False
        for ln in obs.lines:
            if ln.kind == kind and ln.coord == coord:
                movable = ln.movable
                break
        movable_flags.append(movable)

    # Build line-position options. For movable lines, enumerate candidates;
    # for fixed lines, keep observed coord.
    line_options = []
    if line_candidates is None or not any(movable_flags):
        line_options = [lines]
    else:
        cands = line_candidates(obs.grid_w, obs.grid_h)
        # Enumerate only over movable line indices.
        movable_idx = [i for i, m in enumerate(movable_flags) if m]
        for i in movable_idx:
            kind, _ = lines[i]
            for cand in cands:
                alt = list(lines)
                alt[i] = (kind, cand)
                line_options.append(alt)

    results = []
    seen = set()
    for ls in line_options:
        sols = _search_objects(obs, ls, cover, backproject, target_index, all_mask)
        for cfg in sols:
            cfg["_lines"] = ls
            key = repr((tuple(sorted(cfg.items())), tuple(ls)))
            if key in seen:
                continue
            seen.add(key)
            results.append(cfg)

    results.sort(key=lambda c: _config_cost(obs, c))
    return results[:max_solutions]


__all__ = ["solve_configs"]
