"""ls20 frame adapter: 64x64 pixel frame -> WorldState (game-specific).

The frame->state extraction is GAME-SPECIFIC: it encodes ls20's colors, step
size, and layout. The move/step/actions machinery in `move.py` is game-agnostic
(it steps +/-1 on logical cells); this adapter normalizes ls20's pixel frame
down to logical cells so the agnostic machinery applies unchanged.

REVERSE-ENGINEERED FROM LIVE PROBES (not engine source — see red lines):
  - moving object = color 12 (a 5x2 block), NOT color 0/1. Color 0/1 is a
    static 3x3 marker that never moves when an action is sent.
  - step size = 5px; ACTION1/2/3/4 = up/down/left/right.
  - walkable = a logical cell whose 5x2 footprint contains NO obstacle color.
    Obstacles = {4 (wall), 9 (carrying paint / other 9-blocks)}. Color 5 (start shape) is NOT
    an obstacle — the object can stand half-on it (y15 = {5,3} is walkable).
  - the 5px grid is anchored to the moving object itself: offset (x0 % 5, y0 % 5).
  - H6: color-9 glued under the mover is carrying render (tracks cursor), not a fixed slot.

These were confirmed against LIVE frames (tests/fixtures/ls20_l1_frame_live.json):
the walkable model reproduces the live four-direction reach exactly —
UP 6 / DOWN 0 / LEFT 3 / RIGHT 3 steps before hitting a wall.

Note: the goal marker (color 0/1) sits on a DIFFERENT 5px grid than the moving
object (its anchor offset is (0,1) vs the object's (4,0)). So the goal is
recorded in PIXEL coordinates here; matching its logical-cell normalization to
the moving object is `match`'s job, not `move`'s.
"""
from __future__ import annotations

from typing import FrozenSet, Optional, Tuple

import numpy as np

from .state import Goal, WorldState

# Pixel bbox of the moving object: (x0, y0, x1, y1) inclusive.
BBox = Tuple[int, int, int, int]

# --- ls20-specific color semantics (live-probed, see docs/ls20-frame-semantics.md) ---
MOVE_COLOR = 12                  # the controllable 5x2 block
GOAL_MARKER_COLORS = (0, 1)      # static 3x3 marker (target location)
OBSTACLE_COLORS = frozenset({4, 9})  # 4 = wall, 9 = goal-slot marker
STEP = 5                         # pixel step per action
MOVE_SHAPE = (5, 2)              # moving-object footprint (width, height)
STEPS_LIMIT = 42                 # ls20 StepCounter (reverse-engineered, see fixtures/README)


def _plane(frame):
    """Collapse a (layers, H, W) or (H, W) frame to a single HxW int grid.

    Multi-layer flash frames (soft-reset / level transition) put the real board
    on a non-zero layer; prefer the layer that still contains color-12.
    """
    a = np.asarray(frame, dtype=np.int8)
    if a.ndim == 2:
        return a
    for i in range(a.shape[0]):
        if np.any(a[i] == MOVE_COLOR):
            return a[i]
    return a[0]


def _bbox(grid, colors):
    ys, xs = np.where(np.isin(grid, colors))
    if len(xs) == 0:
        return None
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


def locate_mover(frame) -> Optional[BBox]:
    """Locate the controllable 5x2 color-12 block (not other color-12 deco)."""
    from collections import deque

    g = _plane(frame)
    H, W = g.shape
    vis = np.zeros_like(g, dtype=bool)
    best = None  # (score, bbox) — prefer exact 5x2 / 10px blob
    for y in range(H):
        for x in range(W):
            if g[y, x] != MOVE_COLOR or vis[y, x]:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 0 <= ny < H and not vis[ny, nx] and g[ny, nx] == MOVE_COLOR:
                        vis[ny, nx] = True
                        q.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            bb = (min(xs), min(ys), max(xs), max(ys))
            w, h = bb[2] - bb[0] + 1, bb[3] - bb[1] + 1
            n = len(cells)
            # Exact mover footprint scores highest; reject huge blobs.
            if n > 20 or w > 8 or h > 4:
                continue
            score = 100 if (w, h, n) == (5, 2, 10) else (n if n <= 12 else 0)
            if score <= 0:
                continue
            if best is None or score > best[0]:
                best = (score, bb)
    return None if best is None else best[1]


def energy_pickups(frame) -> Tuple[BBox, ...]:
    """Playfield color-11 pickup blobs (exclude bottom UI bar y>=54).

    L2+ : stepping onto a pickup refills the step bar (H21). Without pickups,
    the bar empties in ~20 moves and the engine soft-resets to spawn.
    """
    from collections import deque

    g = _plane(frame)
    H, W = g.shape
    vis = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(H):
        for x in range(W):
            if g[y, x] != 11 or vis[y, x] or y >= 54:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 0 <= ny < H and not vis[ny, nx] and g[ny, nx] == 11:
                        vis[ny, nx] = True
                        q.append((nx, ny))
            if len(cells) > 30:  # UI fragments / noise
                continue
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            out.append((min(xs), min(ys), max(xs), max(ys)))
    out.sort(key=lambda b: (b[1], b[0]))
    return tuple(out)


def ui_energy(frame) -> int:
    """Color-11 pixel count on the bottom step bar (y>=61)."""
    g = _plane(frame)
    return int(np.sum(g[61:63] == 11))


def grid_offset(frame) -> Tuple[int, int]:
    """5px-grid anchor (ox, oy) derived from the mover's current pixel position."""
    bb = locate_mover(frame)
    if bb is None:
        raise ValueError("ls20.grid_offset: no moving object (color 12) in frame")
    return bb[0] % STEP, bb[1] % STEP


def cursor_to_pixel(cursor: Tuple[int, int], offset: Tuple[int, int]) -> Tuple[int, int]:
    """Logical cursor -> predicted top-left pixel of the 5x2 mover."""
    ox, oy = offset
    cx, cy = cursor
    return ox + STEP * cx, oy + STEP * cy


def carrying_near_mover(frame, mover_bbox: Optional[BBox] = None):
    """H6 (seated): color-9 blob glued under the mover = carrying render.

    Returns (pixel_count, bbox) or None. Excludes bottom palette (y>=54).
    """
    from collections import deque

    bb = mover_bbox if mover_bbox is not None else locate_mover(frame)
    if bb is None:
        return None
    g = _plane(frame)
    H, W = g.shape
    vis = np.zeros_like(g, dtype=bool)
    x0, y0, x1, y1 = bb
    margin = 4
    best = None
    for y in range(H):
        for x in range(W):
            if g[y, x] != 9 or vis[y, x]:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 0 <= ny < H and not vis[ny, nx] and g[ny, nx] == 9:
                        vis[ny, nx] = True
                        q.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            b = (min(xs), min(ys), max(xs), max(ys))
            if b[1] >= 54:
                continue
            near = (
                b[0] <= x1 + margin and b[2] >= x0 - margin
                and b[1] <= y1 + margin + STEP and b[3] >= y0 - margin
            )
            if near:
                cand = (len(cells), b)
                if best is None or cand[0] > best[0]:
                    best = cand
    return best


def detect_warps(frame, offset: Optional[Tuple[int, int]] = None, walkable=None):
    """Live-probed L3+: top-band portal cells.

    Pattern: walkable cell with no UP neighbor, color-1 strip immediately west of
    the 5x2 footprint, and a contiguous same-row run to the right. Any action
    from that cell teleports to the rightmost cell of the run (engine flash).
    L1/L2: empty. L3: {(1,1), *DIRS} -> (6,1).
    """
    if offset is None:
        offset = grid_offset(frame)
    if walkable is None:
        walkable = build_walkable(frame, offset, armed=False)
    g = _plane(frame)
    warps = {}
    for (cx, cy) in walkable:
        if (cx, cy - 1) in walkable:
            continue
        px, py = cursor_to_pixel((cx, cy), offset)
        if px <= 0 or py + 1 >= g.shape[0]:
            continue
        if not np.any(g[py:py + 2, px - 1] == 1):
            continue
        x = cx
        while (x + 1, cy) in walkable:
            x += 1
        land = (x, cy)
        if land == (cx, cy):
            continue
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            warps[((cx, cy), d)] = land
    return warps


def build_walkable(frame, offset: Optional[Tuple[int, int]] = None, *, armed: bool = False):
    """Logical walkable cells. Unarmed: obstacles {4,9}. Armed (H20): {4} only."""
    g = _plane(frame)
    H, W = g.shape
    if offset is None:
        bb = locate_mover(frame)
        if bb is None:
            raise ValueError("build_walkable: no mover")
        offset = (bb[0] % STEP, bb[1] % STEP)
    ox, oy = offset
    obstacles = frozenset({4}) if armed else OBSTACLE_COLORS
    mw, mh = MOVE_SHAPE
    walkable = set()
    for cx in range(-1, (W + STEP) // STEP + 1):
        for cy in range(-1, (H + STEP) // STEP + 1):
            px, py = ox + STEP * cx, oy + STEP * cy
            if px < 0 or py < 0 or px + mw > W or py + mh > H:
                continue
            footprint = g[py:py + mh, px:px + mw]
            if not np.any(np.isin(footprint, tuple(obstacles))):
                walkable.add((cx, cy))
    return frozenset(walkable)


def stamp_block(frame) -> Optional[BBox]:
    """Playfield color-5 main block (start-shape / stamp band)."""
    g = _plane(frame)
    from collections import deque
    H, W = g.shape
    vis = np.zeros_like(g, dtype=bool)
    best = None
    for y in range(H):
        for x in range(W):
            if g[y, x] != 5 or vis[y, x] or x < 12 or y >= 54:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 0 <= ny < H and not vis[ny, nx] and g[ny, nx] == 5:
                        vis[ny, nx] = True
                        q.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            cand = (len(cells), (min(xs), min(ys), max(xs), max(ys)))
            if best is None or cand[0] > best[0]:
                best = cand
    return None if best is None else best[1]


def init(frame) -> WorldState:
    """Build a WorldState from an ls20 pixel frame.

    Extracts:
      - cursor  : the moving object's logical-cell position (5px grid, anchored
                  to the object itself).
      - walkable: logical cells the object's 5x2 footprint can occupy.
      - goals   : ls20-marker (color0/1 bbox) + ls20-stamp (color5 playfield block).
      - carrying: H6 color9 blob under mover.

    L3+: color-12 deco exists; ALWAYS locate via `locate_mover` (5x2 match),
    never a raw all-color-12 bbox.
    """
    from collections import deque

    g = _plane(frame)
    H, W = g.shape

    obj = locate_mover(frame)
    if obj is None:
        raise ValueError("ls20.init: no moving object (color 12) in frame")

    ox, oy = obj[0] % STEP, obj[1] % STEP
    cursor = ((obj[0] - ox) // STEP, (obj[1] - oy) // STEP)
    walkable = build_walkable(frame, (ox, oy), armed=False)

    goals_list = []
    # Marker: compact playfield color-0/1 blob (~3x3), reject flat chrome strips.
    vis = np.zeros_like(g, dtype=bool)
    marker_cands = []
    for y in range(H):
        for x in range(W):
            if g[y, x] not in GOAL_MARKER_COLORS or vis[y, x] or y >= 54:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (0 <= nx < W and 0 <= ny < H and not vis[ny, nx]
                            and g[ny, nx] in GOAL_MARKER_COLORS):
                        vis[ny, nx] = True
                        q.append((nx, ny))
            if not (3 <= len(cells) <= 12):
                continue
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            bb = (min(xs), min(ys), max(xs), max(ys))
            bw, bh = bb[2] - bb[0] + 1, bb[3] - bb[1] + 1
            if bw > 6 or bh > 6 or bw < 2 or bh < 2:
                continue
            marker_cands.append((len(cells), bb))
    if marker_cands:
        marker_cands.sort(key=lambda t: (abs(t[0] - 5), t[1][1], t[1][0]))
        gm = marker_cands[0][1]
        goals_list.append(Goal(
            id="ls20-marker", kind="cell", pos=(gm[0], gm[1]), shape=gm, color=0,
        ))
    sb = stamp_block(frame)
    if sb is not None:
        goals_list.append(Goal(
            id="ls20-stamp", kind="slot", pos=(sb[0], sb[1]), shape=sb, color=5,
        ))

    carrying = carrying_near_mover(frame, obj)

    return WorldState(
        grid_w=W,
        grid_h=H,
        cursor=cursor,
        walkable=walkable,
        carrying=carrying,
        goals=tuple(goals_list),
        steps_used=0,
        steps_limit=STEPS_LIMIT,
        armed=False,
    )


__all__ = [
    "init", "locate_mover", "grid_offset", "cursor_to_pixel", "carrying_near_mover",
    "build_walkable", "detect_warps", "stamp_block", "energy_pickups", "ui_energy",
    "MOVE_COLOR", "GOAL_MARKER_COLORS", "OBSTACLE_COLORS",
    "STEP", "MOVE_SHAPE", "STEPS_LIMIT",
]
