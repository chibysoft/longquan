"""Longquan motion: turn a target config into an action sequence.

Generic: it only knows "move objects to target positions, cycling selection".
It does NOT know what "move" means physically (that is the hypothesis's job —
see the replay step, which is the source of truth).

Action semantics for the first target game: 1=up, 2=down, 3=left, 4=right,
5=cycle selection.
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


def plan(obs: Obs, config: Dict[str, Tuple[int, int]],
         *, initial_selected: int = 0) -> List[int]:
    """Translate {obj_id: target_pos} into an action sequence.

    Selection cursor starts at `initial_selected` (index into obs.objects).
    Objects are moved in the order they appear in obs.objects.
    """
    actions: List[int] = []
    cursor = initial_selected
    n = len(obs.objects)

    for i, obj in enumerate(obs.objects):
        if obj.id not in config:
            continue
        tx, ty = config[obj.id]
        # current position = bbox origin
        cx, cy = obj.bbox[0], obj.bbox[1]
        # advance selection to this object
        while cursor != i:
            actions.append(SELECT)
            cursor = (cursor + 1) % n
        actions.extend(_move_xy(tx - cx, ty - cy))

    return actions


__all__ = ["plan"]
