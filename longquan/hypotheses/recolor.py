"""Recolor primitive: colors are mapped by a table.

The rule is "color A becomes color B" for some mapping. The free parameter is
the mapping table. Full cover/backproject semantics need exploration of a real
recolor game before implementation (stage 1 will pick a game and reverse it).

Interface (primitive contract):
    score(obs) -> float
    cover(...) / backproject(...) -> TODO: implement after picking a verify game
"""
from __future__ import annotations

from typing import Iterable, List, Tuple


def score(obs) -> float:
    """Match prior: recolor games have many objects/targets with a small set of
    colors that look like a permutation. Weak heuristic for now."""
    if not getattr(obs, "objects", None):
        return 0.0
    return 0.3  # weak prior; refine after exploring a real recolor game


def cover(rel_cells, pos, param):
    """TODO: implement after picking a recolor verify game (stage 1)."""
    raise NotImplementedError("recolor.cover not yet implemented")


def backproject(rel_cells, targets, param, grid_w, grid_h):
    """TODO: implement after picking a recolor verify game (stage 1)."""
    raise NotImplementedError("recolor.backproject not yet implemented")


__all__ = ["score", "cover", "backproject"]
