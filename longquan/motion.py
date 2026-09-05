"""Longquan motion: turn a config (objects + lines) into an action sequence.

Generic: moves objects AND lines to target positions, cycling selection.
Line move: vertical line moves left/right (x changes), horizontal line moves
up/down (y changes) — this is hypothesis-agnostic: a line with kind 'V' is a
column at x, kind 'H' is a row at y.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from .obs import Obs

UP, DOWN, LEFT, RIGHT, SELECT = 1, 2, 3, 4, 5


def _move_xy(dx: int, dy: int) -> List[int]:
    out = []
    if dy > 0:
        out += [DOWN] * dy
    elif dy < 0:
        out += [UP] * (-dy)
    if dx > 0:
        out += [RIGHT] * dx
    elif dx < 0:
        out += [LEFT] * (-dx)
    return out


def plan(obs: Obs, config: Dict, *, initial_selected: int = 0) -> List[int]:
    """Translate config into actions. config has obj_id->pos plus '_lines'->[(kind,coord)]."""
    actions: List[int] = []
    cursor = initial_selected

    # Build a movement plan: lines first (they affect global cover), then objects.
    lines = config.get("_lines", [])
    # current lines from obs
    cur_lines = {ln.kind: ln.coord for ln in obs.lines}

    # total selectable = lines + objects
    line_items = [(k, c) for (k, c) in lines]
    n_lines = len(line_items)
    n_objs = len(obs.objects)
    total = n_lines + n_objs

    def move_cursor_to(index):
        nonlocal cursor
        while cursor != index:
            actions.append(SELECT)
            cursor = (cursor + 1) % max(1, total)

    # move lines (indices 0..n_lines-1)
    for i, (kind, target) in enumerate(line_items):
        if kind == "V":
            cur = cur_lines.get("V", 0)
            dx = target - cur
            dy = 0
        else:
            cur = cur_lines.get("H", 0)
            dx = 0
            dy = target - cur
        if dx == 0 and dy == 0:
            continue
        move_cursor_to(i)
        actions.extend(_move_xy(dx, dy))
        cur_lines[kind] = target

    # move objects (indices n_lines..n_lines+n_objs-1)
    for i, obj in enumerate(obs.objects):
        if obj.id not in config:
            continue
        tx, ty = config[obj.id]
        cx, cy = obj.bbox[0], obj.bbox[1]
        if (tx, ty) == (cx, cy):
            continue
        move_cursor_to(n_lines + i)
        actions.extend(_move_xy(tx - cx, ty - cy))

    return actions


__all__ = ["plan"]
