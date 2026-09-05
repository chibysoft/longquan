"""Primitive modules: one per rule primitive.

Each primitive exposes the same interface the generic layers consume:
    score(obs) -> float (match prior for the selector)
    cover(rel_cells, pos, lines) -> set of covered cells
    backproject(rel_cells, targets, lines, w, h) -> candidate positions

To add a new primitive, drop a new module here and register it in registry.py.
"""
from . import reflect, translate, recolor, copy

__all__ = ["reflect", "translate", "recolor", "copy"]
