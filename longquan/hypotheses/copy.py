"""Copy primitive: an object is duplicated N times at offsets.

The rule is "copy the object several times". The free parameter is (count,
offset). Full cover/backproject semantics need exploration of a real copy game
before implementation (stage 1 will pick a game and reverse it).

Interface (primitive contract):
    score(obs) -> float
    cover(...) / backproject(...) -> TODO: implement after picking a verify game
"""
from __future__ import annotations

from typing import Iterable, List, Tuple


def score(obs) -> float:
    """Match prior: copy games show repeated identical shapes. Weak heuristic."""
    if not getattr(obs, "objects", None):
        return 0.0
    return 0.3  # weak prior; refine after exploring a real copy game


def cover(rel_cells, pos, param):
    """TODO: implement after picking a copy verify game (stage 1)."""
    raise NotImplementedError("copy.cover not yet implemented")


def backproject(rel_cells, targets, param, grid_w, grid_h):
    """TODO: implement after picking a copy verify game (stage 1)."""
    raise NotImplementedError("copy.backproject not yet implemented")


__all__ = ["score", "cover", "backproject"]
