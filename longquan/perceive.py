"""Longquan closed-book perception: frame -> Obs.

Reads ONLY the rendered frame. Does not read engine source, sprites, or any
canned tables. Color semantics are hypothesis-space parameters told at design
time ("prior review"), not runtime source reading.

Frame physics (measured, not guessed):
- board cell renders as a 3x3 solid block; cell = pixel // 3
- rightmost column (x=63) is UI, bottom row (y=63) is letterbox; crop both
"""
from __future__ import annotations

from typing import List

import numpy as np

from .obs import Obs, Obj

# Hypothesis-space color semantics (parameters, not data-structure constants).
COLOR_BG = 9
COLOR_TARGET = 11
COLOR_LINE = 10
COLOR_SELECTED = 0
COLOR_MIRROR = 4   # render-derived reflection image, NOT a real object


def _grid_cells(cropped: np.ndarray, color: int) -> set:
    ys, xs = np.where(cropped == color)
    cells = set()
    for x, y in zip(xs.tolist(), ys.tolist()):
        gx, gy = int(x) // 3, int(y) // 3
        cells.add((gx, gy))
    return cells


def _connected(cells: set) -> List[set]:
    remaining = set(cells)
    comps: List[set] = []
    while remaining:
        seed = remaining.pop()
        stack = [seed]
        comp = {seed}
        while stack:
            cx, cy = stack.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (cx + dx, cy + dy)
                if n in remaining:
                    remaining.remove(n)
                    comp.add(n)
                    stack.append(n)
        comps.append(comp)
    return comps


def perceive(
    frame,
    *,
    legal_actions: List[int] = (1, 2, 3, 4, 5),
    steps_left: int = 64,
) -> Obs:
    f = np.asarray(frame, dtype=np.int8)
    if f.ndim == 3:
        f = f[0]
    cropped = f[:63, :63]

    # line structures: a color forming a near-full column or row
    line_cells = _grid_cells(cropped, COLOR_LINE)
    line_coords: List[int] = []
    line_span: set = set()
    by_x: dict = {}
    by_y: dict = {}
    for gx, gy in line_cells:
        by_x.setdefault(gx, []).append(gy)
        by_y.setdefault(gy, []).append(gx)
    for gx, gys in by_x.items():
        if len(gys) >= 15:
            line_coords.append(gx)
            line_span |= {(gx, gy) for gy in range(21)}
    for gy, gxs in by_y.items():
        if len(gxs) >= 15:
            line_coords.append(gy)
            line_span |= {(gx, gy) for gx in range(21)}

    targets = sorted(_grid_cells(cropped, COLOR_TARGET))
    target_set = set(targets)
    selected = sorted(_grid_cells(cropped, COLOR_SELECTED))

    # objects: exclude bg/line/target/selected/mirror, then connected blobs
    exclude = {COLOR_BG, COLOR_LINE, COLOR_TARGET, COLOR_SELECTED, COLOR_MIRROR}
    color_cells: dict = {}
    for gy in range(21):
        for gx in range(21):
            c = int(cropped[gy * 3, gx * 3])
            if c in exclude:
                continue
            if (gx, gy) in line_span or (gx, gy) in target_set:
                continue
            color_cells.setdefault(c, set()).add((gx, gy))

    objects: List[Obj] = []
    for color, cells in sorted(color_cells.items()):
        for comp in _connected(cells):
            if len(comp) < 3:
                continue
            xs = [c[0] for c in comp]
            ys = [c[1] for c in comp]
            objects.append(Obj(
                id=f"obj_{len(objects)}",
                color=color,
                cells=sorted(comp),
                bbox=(min(xs), min(ys), max(xs), max(ys)),
            ))

    return Obs(
        grid_w=21,
        grid_h=21,
        objects=objects,
        targets=targets,
        selected_cells=selected,
        line_coords=line_coords,
        legal_actions=list(legal_actions),
        steps_left=steps_left,
    )


__all__ = ["perceive"]
