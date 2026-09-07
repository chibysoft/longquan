"""Stage 2: rule = a sequence of geometric primitives (Program).

A Program is an ordered list of ops. Each op is a dict with an "op" key and
free parameters. Execution is Grid -> Grid on synthetic (or real) 2D color
grids — the acceptance for stage 2 is composition on synthetic frames, not
live ARC-AGI-3 games.

Complexity (MDL precursor) = number of ops + parameter bit cost.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableSequence, Sequence, Tuple, Union

import numpy as np

Grid = np.ndarray  # 2D int, dtype whatever
Op = Dict[str, Any]
BG = 0


def _bits(n: int) -> int:
    """Bits to encode a non-negative integer (0 -> 1)."""
    n = abs(int(n))
    if n == 0:
        return 1
    return n.bit_length()


def _as_grid(grid) -> np.ndarray:
    g = np.asarray(grid)
    if g.ndim != 2:
        raise ValueError(f"grid must be 2D, got shape {g.shape}")
    return g.copy()


def _reflect_cell(x: int, y: int, axis: str, coord: int) -> Tuple[int, int]:
    if axis == "V":
        return (2 * coord - x, y)
    if axis == "H":
        return (x, 2 * coord - y)
    raise ValueError(f"axis must be 'V' or 'H', got {axis!r}")


def apply_reflect(grid: Grid, *, axis: str, coord: int, bg: int = BG) -> Grid:
    """Union of source cells and their reflections across (axis, coord).

    Matches the geometric spirit of hypotheses.reflect.cover: colored cells
    are mirrored onto the board; out-of-bounds reflections are dropped.
    """
    g = _as_grid(grid)
    h, w = g.shape
    out = np.full_like(g, bg)
    # Keep background, then paint source + mirrors (later paint wins on clash).
    for y in range(h):
        for x in range(w):
            c = int(g[y, x])
            if c == bg:
                continue
            out[y, x] = c
            rx, ry = _reflect_cell(x, y, axis, int(coord))
            if 0 <= rx < w and 0 <= ry < h:
                out[ry, rx] = c
    return out


def apply_recolor(grid: Grid, *, mapping: Mapping[int, int], bg: int = BG) -> Grid:
    """Apply a color map; unmapped colors (and bg) stay put unless remapped."""
    g = _as_grid(grid)
    out = g.copy()
    # Vectorized where possible; mapping is small.
    for src, dst in mapping.items():
        out[g == int(src)] = int(dst)
    return out


def apply_translate(grid: Grid, *, dx: int, dy: int, bg: int = BG) -> Grid:
    """Shift non-bg cells by (dx, dy); cells leaving the board are dropped."""
    g = _as_grid(grid)
    h, w = g.shape
    out = np.full_like(g, bg)
    dx, dy = int(dx), int(dy)
    for y in range(h):
        for x in range(w):
            c = int(g[y, x])
            if c == bg:
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                out[ny, nx] = c
    return out


def apply_copy(grid: Grid, *, offsets: Sequence[Tuple[int, int]], bg: int = BG) -> Grid:
    """Duplicate every non-bg cell to each offset (union with source)."""
    g = _as_grid(grid)
    h, w = g.shape
    out = g.copy()
    for y in range(h):
        for x in range(w):
            c = int(g[y, x])
            if c == bg:
                continue
            for dx, dy in offsets:
                nx, ny = x + int(dx), y + int(dy)
                if 0 <= nx < w and 0 <= ny < h:
                    out[ny, nx] = c
    return out


_APPLY = {
    "reflect": lambda g, op: apply_reflect(g, axis=op["axis"], coord=op["coord"],
                                           bg=op.get("bg", BG)),
    "recolor": lambda g, op: apply_recolor(g, mapping=op["mapping"],
                                           bg=op.get("bg", BG)),
    "translate": lambda g, op: apply_translate(g, dx=op["dx"], dy=op["dy"],
                                               bg=op.get("bg", BG)),
    "copy": lambda g, op: apply_copy(g, offsets=op["offsets"],
                                     bg=op.get("bg", BG)),
}


def op_param_bits(op: Op) -> int:
    """Parameter bit cost for one op (excluding the op-type tag)."""
    name = op["op"]
    if name == "reflect":
        return 1 + _bits(op["coord"])  # axis bit + coord
    if name == "recolor":
        mapping = op["mapping"]
        return sum(_bits(k) + _bits(v) for k, v in mapping.items())
    if name == "translate":
        return _bits(op["dx"]) + _bits(op["dy"])
    if name == "copy":
        return sum(_bits(dx) + _bits(dy) for dx, dy in op["offsets"])
    raise ValueError(f"unknown op {name!r}")


def complexity(ops: Sequence[Op]) -> int:
    """MDL precursor: #ops + sum of parameter bits."""
    return len(ops) + sum(op_param_bits(o) for o in ops)


def execute_ops(ops: Sequence[Op], grid) -> np.ndarray:
    """Run ops in order; returns a new grid."""
    g = _as_grid(grid)
    for op in ops:
        name = op["op"]
        if name not in _APPLY:
            raise ValueError(f"unknown op {name!r}; known={sorted(_APPLY)}")
        g = _APPLY[name](g, op)
    return g


@dataclass(frozen=True)
class Program:
    """Ordered geometric-primitive sequence."""

    ops: Tuple[Op, ...]

    @classmethod
    def from_ops(cls, ops: Iterable[Op]) -> "Program":
        frozen: List[Op] = []
        for op in ops:
            o = dict(op)
            if "mapping" in o:
                o["mapping"] = {int(k): int(v) for k, v in dict(o["mapping"]).items()}
            if "offsets" in o:
                o["offsets"] = [tuple(p) for p in o["offsets"]]
            frozen.append(o)
        return cls(ops=tuple(frozen))

    @classmethod
    def from_json(cls, data: Sequence[Op]) -> "Program":
        return cls.from_ops(data)

    def to_json(self) -> List[Op]:
        out: List[Op] = []
        for op in self.ops:
            o = dict(op)
            if "mapping" in o:
                o["mapping"] = {int(k): int(v) for k, v in o["mapping"].items()}
            if "offsets" in o:
                o["offsets"] = [list(p) for p in o["offsets"]]
            out.append(o)
        return out

    def complexity(self) -> int:
        return complexity(self.ops)

    def execute(self, grid) -> np.ndarray:
        return execute_ops(self.ops, grid)

    def __len__(self) -> int:
        return len(self.ops)


__all__ = [
    "Program",
    "Op",
    "BG",
    "apply_reflect",
    "apply_recolor",
    "apply_translate",
    "apply_copy",
    "complexity",
    "op_param_bits",
    "execute_ops",
]
