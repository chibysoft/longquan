"""Shared helpers for ls20 online probes (move validate + match probe)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from longquan.interactive import ls20
from longquan.interactive.state import WorldState

PALETTE_Y_MIN = 54
LEFT_UI_X_MAX = 12


def plane(frame) -> np.ndarray:
    a = np.asarray(frame, dtype=np.int8)
    return a[0] if a.ndim == 3 else a


def color_blobs(grid: np.ndarray, color: int):
    H, W = grid.shape
    vis = np.zeros_like(grid, dtype=bool)
    out = []
    for y in range(H):
        for x in range(W):
            if grid[y, x] != color or vis[y, x]:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 0 <= ny < H and not vis[ny, nx] and grid[ny, nx] == color:
                        vis[ny, nx] = True
                        q.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            out.append((len(cells), (min(xs), min(ys), max(xs), max(ys))))
    out.sort(key=lambda t: -t[0])
    return out


def playfield_9(grid: np.ndarray):
    return [(n, b) for n, b in color_blobs(grid, 9) if b[1] < PALETTE_Y_MIN]


def blob_near_mover(blobs, bbox12, margin=4):
    if bbox12 is None:
        return []
    x0, y0, x1, y1 = bbox12
    out = []
    for n, b in blobs:
        near = (
            b[0] <= x1 + margin and b[2] >= x0 - margin
            and b[1] <= y1 + margin + ls20.STEP and b[3] >= y0 - margin
        )
        if near:
            out.append((n, b))
    return out


def fixed_playfield_9(blobs, bbox12):
    near = {b for _, b in blob_near_mover(blobs, bbox12)}
    return [(n, b) for n, b in blobs if b not in near]


@dataclass
class Snap:
    levels: int
    state: str
    n01: int
    bbox01: Optional[Tuple[int, int, int, int]]
    blobs9: list
    bbox12: Optional[Tuple[int, int, int, int]]
    cursor: Optional[Tuple[int, int]]
    n11: int


def snap(frame, meta) -> Snap:
    g = plane(frame)
    ys, xs = np.where(np.isin(g, [0, 1]))
    n01 = int(len(xs))
    bbox01 = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if n01 else None
    try:
        cur = ls20.init(frame).cursor
    except Exception:
        cur = None
    return Snap(
        levels=int(meta.get("levels_completed", 0) or 0),
        state=str(meta.get("state", "")),
        n01=n01,
        bbox01=bbox01,
        blobs9=playfield_9(g),
        bbox12=ls20.locate_mover(frame),
        cursor=cur,
        n11=int(np.count_nonzero(g == 11)),
    )


def nearest_walkable(state: WorldState, offset, px, py):
    best = None
    for cell in state.walkable:
        ax, ay = ls20.cursor_to_pixel(cell, offset)
        d = abs(ax - px) + abs(ay - py)
        key = (d, cell[0], cell[1])
        if best is None or key < best[0]:
            best = (key, cell, d)
    return best[1], best[2]


def playfield_color5_blocks(grid: np.ndarray):
    out = []
    for n, b in color_blobs(grid, 5):
        if b[0] < LEFT_UI_X_MAX:
            continue
        if b[1] >= PALETTE_Y_MIN:
            continue
        out.append((n, b))
    return out


def windows_5x5_paint(grid: np.ndarray, min_paint: int = 15):
    raw = []
    for y in range(0, PALETTE_Y_MIN - 4):
        for x in range(LEFT_UI_X_MAX, 60):
            win = grid[y:y + 5, x:x + 5]
            if win.shape != (5, 5):
                continue
            n5 = int(np.count_nonzero(win == 5))
            n9 = int(np.count_nonzero(win == 9))
            if n5 + n9 >= min_paint:
                raw.append((n5 + n9, n5, n9, x, y))
    raw.sort(reverse=True)
    kept = []
    for item in raw:
        _, _, _, x, y = item
        if any(abs(x - kx) < 3 and abs(y - ky) < 3 for *_, kx, ky in kept):
            continue
        kept.append(item)
    return kept
