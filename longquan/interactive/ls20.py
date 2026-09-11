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
STEP = 5                         # pixel step per action (px)
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
    """Live-probed L3+: portal cells (horizontal + vertical + L4 eject).

    Horizontal: walkable cell with a color-1 strip immediately west of the 5x2
    footprint, and a contiguous same-row run to the right. Any action (including
    UP) teleports to the rightmost cell of the run, then applies the action once
    (blocked => stay on land). Exception: if the cell north is the L4 ring-hop
    pad, UP walks normally ((8,6)→(8,5), H5ab). L3 top-of-shaft / L4 corridor.

    Vertical (live-probed E2 + L4 H5w): a color-1 HORIZONTAL bar directly above
    the 5x2 footprint. Any action teleports to the bottom of the contiguous
    column run, then applies the action once (blocked => stay on bottom).
    Dirs already claimed by a horizontal portal on the same cell are kept.
    L3: {(10,1), DOWN} -> (10,9).  L4: {(3,7), LEFT} -> (2,9), etc.  L1/L2: empty.

    Vertical eject (live-probed L4 H6 + L5): bottom of a contiguous column run
    of length >= 5 whose footprint has a color-1 OR color-4 rail within ~6px
    to the EAST. Any action teleports to the TOP of that run, then applies the
    action once (blocked => stay on top). L4: (7,5) east-1. L5: (7,5) east-4
    and (10,10) east-4 long shaft → (10,1) stamp.

    Ring hop (live H5ab + (8,8)/(4,8)): rightmost cell of a horizontal
    walkable run with an east color-1 rail; ANY action teleports to the
    leftmost cell of that run, then applies the action. Mid may be walkable.
    """
    if offset is None:
        offset = grid_offset(frame)
    if walkable is None:
        walkable = build_walkable(frame, offset, armed=False)
    g = _plane(frame)
    H, W = g.shape
    mw = MOVE_SHAPE[0]
    warps = {}

    # --- vertical eject FIRST (L4/L5): needed so ring-hop mid=(7,5) is known
    # before horizontal UP-exemption checks the hop pad at (8,5).
    walk_a_eject = build_walkable(frame, offset, armed=True)
    cols: dict[int, list[int]] = {}
    for (cx, cy) in walkable:
        cols.setdefault(cx, []).append(cy)
    for cx, ys in cols.items():
        ys = sorted(ys)
        seg_start = prev = ys[0]
        segments = []
        for y in ys[1:]:
            if y == prev + 1:
                prev = y
                continue
            segments.append((seg_start, prev))
            seg_start = prev = y
        segments.append((seg_start, prev))
        for y0, y1 in segments:
            if y1 - y0 + 1 < 5:
                continue
            bottom = (cx, y1)
            top = (cx, y0)
            if bottom == top:
                continue
            px, py = cursor_to_pixel(bottom, offset)
            x1 = min(px + 20, W)
            if px + mw >= W:
                continue
            east = g[py:py + 2, px + mw:x1]
            # L4: color-1 rail. L5 east-4:
            #   - short shaft len==5: first non-floor within 6px is color-4
            #     ((7,5)→(7,1)); wider padding ((6,5)) rejected.
            #   - long shaft on rightmost cols (cx>=10): IMMEDIATE east
            #     column all color-4 ((10,10)→(10,1) stamp). Do NOT apply
            #     to mid cols — L2 false ejects (6,8)/(2,7).
            has_e1 = bool(np.any(east == 1))
            has_e4 = False
            if not has_e1:
                seg_len = y1 - y0 + 1
                if seg_len == 5:
                    for xi in range(min(6, east.shape[1])):
                        col = east[:, xi]
                        if np.all(col == 3):
                            continue
                        has_e4 = bool(np.any(col == 4) and not np.any(col == 12))
                        break
                elif (
                    cx >= 10
                    and east.shape[1] > 0
                    and np.all(east[:, 0] == 4)
                ):
                    has_e4 = True
            if not (has_e1 or has_e4):
                continue
            # Shaft truncated above an armed-only cell (L6 stamp gate (10,10)):
            # walk_u ends at (10,9) and short east-4 falsely ejects → (10,5),
            # blocking the live DOWN to (10,10). Skip mid-shaft ejects.
            below = (cx, y1 + 1)
            if below not in walkable and below in walk_a_eject:
                continue
            # L4 post-ring-crush: (6,6) gains east color-1 smear + color-9/12
            # footprint → false eject. Live: only UP to (6,5). Real pads are
            # clean when the mover is elsewhere; color-12 on-pad is handled
            # by ignoring 12 only for rightmost long east-4 shafts (L5).
            foot = g[py:py + 2, px:px + mw]
            if has_e4 and cx >= 10:
                if np.any(foot == 9):
                    continue
            elif np.any((foot == 9) | (foot == 12)):
                continue
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                warps[(bottom, d)] = top

    def _ring_hop_source(cx, cy) -> bool:
        """True if (cx,cy) is an L4 ring-hop pad.

        Live: rightmost cell of a horizontal walkable run with an east color-1
        rail. ANY action teleports to the LEFTMOST cell of that run, then
        applies the action. Mid may be walkable ((8,8)/(4,8)). Skip color-9
        (post-crush (6,6) false positive). Color-12 alone is the mover on pad
        (L5 (10,6) live hop must still fire while standing there).
        """
        if (cx, cy) not in walkable:
            return False
        if (cx + 1, cy) in walkable:
            return False  # only rightmost of the run hops
        px, py = cursor_to_pixel((cx, cy), offset)
        if px + mw >= W or py + 1 >= H:
            return False
        foot = g[py:py + 2, px:px + mw]
        if np.any(foot == 9):
            return False
        if not np.any(g[py:py + 2, px + mw:min(px + 8, W)] == 1):
            return False
        x = cx
        while (x - 1, cy) in walkable:
            x -= 1
        land = (x, cy)
        if land == (cx, cy):
            return False
        return True

    def _ring_hop_land(cx, cy):
        x = cx
        while (x - 1, cy) in walkable:
            x -= 1
        return (x, cy)

    for (cx, cy) in walkable:
        px, py = cursor_to_pixel((cx, cy), offset)
        if px < 0 or py < 0 or py + 1 >= H:
            continue
        # --- horizontal portal: color-1 strip west + same-row run ---
        # Warps store RAW land; `_step_cell` applies the action after teleport.
        # UP normally triggers (live post-unlock (6,4) UP → (10,3)).
        # Exception: north is ring-hop pad — (8,6) UP walks to (8,5) (H5ab).
        if px > 0 and int(np.sum(g[py:py + 2, px - 1] == 1)) >= 2:
            x = cx
            while (x + 1, cy) in walkable:
                x += 1
            land = (x, cy)
            if land != (cx, cy):
                dirs_h = [(1, 0), (-1, 0), (0, 1), (0, -1)]  # R L D U
                if _ring_hop_source(cx, cy - 1):
                    dirs_h = [(1, 0), (-1, 0), (0, 1)]  # not UP
                for d in dirs_h:
                    # do not overwrite eject on the same (cell,dir)
                    if ((cx, cy), d) in warps:
                        continue
                    warps[((cx, cy), d)] = land
        # --- vertical portal: color-1 HORIZONTAL bar directly above ---
        if py - 1 >= 0 and px + mw <= W and int(np.sum(g[py - 1, px:px + mw] == 1)) >= 2:
            y = cy
            while (cx, y + 1) in walkable:
                y += 1
            land = (cx, y)
            if land != (cx, cy):
                for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if ((cx, cy), d) in warps:
                        continue
                    warps[((cx, cy), d)] = land

    # --- L4 ring approach (live H5ab + (8,8)/(4,8)): east color-1 rail on the
    # rightmost cell of a horizontal run. ANY action teleports to the LEFTMOST
    # cell of that run, then applies the action (blocked => stay on land).
    # Post-crush (6,6) color-9/12 + east smear → skipped (false hop).
    for (cx, cy) in list(walkable):
        if any(((cx, cy), d) in warps for d in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            continue
        if not _ring_hop_source(cx, cy):
            continue
        land = _ring_hop_land(cx, cy)
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
