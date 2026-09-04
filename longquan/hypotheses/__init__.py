"""Hypothesis-space modules: one per game rule.

Each module exposes the same interface the generic search consumes:
    cover(obj_cells, pos, axes) -> set of covered cells
    backproject(obj_cells, targets, axes, w, h) -> candidate positions

To add a new game, drop a new module here and inject its cover/backproject
into loop.solve(). The generic search / motion / loop layers never change.
"""
from . import mirror

__all__ = ["mirror"]
