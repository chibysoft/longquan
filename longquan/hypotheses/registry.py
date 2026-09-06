"""Primitive registry: the selector's search space.

Each entry maps a primitive name to its module. The selector iterates this
registry, scoring each primitive against the observation, trying them in score
order, and eliminating failed ones via replay.

reflect: fully implemented (verified on AR25).
translate: cover/backproject implemented; verify game not yet picked.
copy: cover/backproject implemented; verify game WITHDRAWN (ls20 -> move+match).
recolor: score only; cover/backproject are TODO pending a verify game.
"""
from __future__ import annotations

from . import copy, recolor, reflect, translate

PRIMITIVES = {
    "reflect": reflect,
    "translate": translate,
    "recolor": recolor,
    "copy": copy,
}

# Order roughly by implementation maturity + commonness. The selector re-ranks
# by score() at runtime; this is just a fallback.
DEFAULT_ORDER = ["reflect", "translate", "recolor", "copy"]


def all_primitives():
    return list(PRIMITIVES.keys())


def get(name):
    return PRIMITIVES[name]


__all__ = ["PRIMITIVES", "DEFAULT_ORDER", "all_primitives", "get"]
