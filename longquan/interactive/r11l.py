"""r11l frame model (closed-book recon).

Live-probed + design-time mechanics (2026-09-08, game_id=r11l-495a7899):

- ACTION6 only (tags=click). Select waypoint / move selected / animate.
- Waypoints: 5×5 crosses — unselected color 3, selected color 0.
- Ship: color-6 core + chrome ring (L1: color 15; L2+: may be 12 or 15);
  center = mean of that ship's waypoint centers.
- Goal (L1–L3): hollow diamond of the ship's chrome color; win = every ship
  collides with its matching-chrome goal (both must cover in L2+).
- Move: click empty twice (arm + animate). Select: click cross once.
- Move is rejected (noop) or lethal if the resulting ship centroid's 5×5
  footprint hits wall(2) / hazard(10). Stacking two wps on one cell becomes
  a select, not a move — keep Chebyshev ≥5 between wp centers.
- Walls color 2; left column color 0 = step budget UI.

L4+ adds chrome matching / pickups — not covered here yet.
"""
from __future__ import annotations

from collections import Counter, deque
from typing import List, Optional, Tuple

import numpy as np

FLOOR = 5
WALL = 2
HAZARD = 10
SHIP_CORE = 6
CHROME = 15
WP_IDLE = 3
WP_SELECTED = 0
Pt = Tuple[int, int]


def _plane(frame) -> np.ndarray:
    a = np.asarray(frame)
    return a[0] if a.ndim == 3 else a


def _components(g: np.ndarray, color: int, min_n: int = 1, max_n: int = 10**9):
    h, w = g.shape
    vis = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(h):
        for x in range(w):
            if g[y, x] != color or vis[y, x]:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells: List[Pt] = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and not vis[ny, nx] and g[ny, nx] == color:
                        vis[ny, nx] = True
                        q.append((nx, ny))
            if min_n <= len(cells) <= max_n:
                xs = [c[0] for c in cells]
                ys = [c[1] for c in cells]
                out.append(
                    {
                        "n": len(cells),
                        "bbox": (min(xs), min(ys), max(xs), max(ys)),
                        "c": ((min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2),
                        "cells": cells,
                    }
                )
    out.sort(key=lambda b: (-b["n"], b["c"]))
    return out


def ships(frame) -> List[dict]:
    """Each color-6 core with majority nearby chrome color (12/15/…)."""
    g = _plane(frame)
    ys, xs = np.where(g == SHIP_CORE)
    out = []
    for x, y in zip(xs.tolist(), ys.tolist()):
        colors: Counter = Counter()
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                ny, nx = y + dy, x + dx
                if 0 <= ny < g.shape[0] and 0 <= nx < g.shape[1]:
                    c = int(g[ny, nx])
                    if c not in (FLOOR, SHIP_CORE, 0, 1, WALL, HAZARD, WP_IDLE):
                        colors[c] += 1
        chrome = colors.most_common(1)[0][0] if colors else CHROME
        out.append({"c": (x, y), "chrome": chrome})
    return out


def ship_center(frame) -> Optional[Pt]:
    """Single-ship helper (L1); for multi-ship use ``ships``."""
    ss = ships(frame)
    if not ss:
        return None
    if len(ss) == 1:
        return ss[0]["c"]
    xs = [s["c"][0] for s in ss]
    ys = [s["c"][1] for s in ss]
    return (int(sum(xs) / len(xs)), int(sum(ys) / len(ys)))


def waypoints(frame) -> List[dict]:
    """5×5 crosses: selected (color 0, exclude left UI bar) + idle (color 3)."""
    g = _plane(frame)
    out: List[dict] = []
    for color in (WP_IDLE, WP_SELECTED):
        for b in _components(g, color, min_n=8, max_n=16):
            x0, y0, x1, y1 = b["bbox"]
            if color == WP_SELECTED and x1 <= 0:
                continue
            if color == WP_SELECTED and (y1 - y0) >= 20:
                continue
            b = dict(b)
            b["selected"] = color == WP_SELECTED
            b["color"] = color
            out.append(b)
    return out


def goals(frame) -> List[dict]:
    """Hollow chrome diamonds matching ship chrome colors (not ship bodies)."""
    g = _plane(frame)
    sh = ships(frame)
    if not sh:
        return []
    ship_pts = [s["c"] for s in sh]
    rings = []
    for col in {s["chrome"] for s in sh}:
        pts = [
            (x, y)
            for y in range(g.shape[0])
            for x in range(g.shape[1])
            if g[y, x] == col
            and min(abs(x - sx) + abs(y - sy) for sx, sy in ship_pts) > 5
        ]
        unused = set(pts)
        while unused:
            seed = next(iter(unused))
            q = deque([seed])
            unused.remove(seed)
            cl = [seed]
            while q:
                cx, cy = q.popleft()
                for p in list(unused):
                    if abs(p[0] - cx) + abs(p[1] - cy) <= 3:
                        unused.remove(p)
                        q.append(p)
                        cl.append(p)
            if len(cl) >= 8:
                xs = [p[0] for p in cl]
                ys = [p[1] for p in cl]
                rings.append(
                    {
                        "n": len(cl),
                        "c": (int(sum(xs) / len(xs)), int(sum(ys) / len(ys))),
                        "bbox": (min(xs), min(ys), max(xs), max(ys)),
                        "chrome": col,
                    }
                )
    rings.sort(key=lambda r: (r.get("chrome", 0), r["c"]))
    return rings


def assign_waypoints(frame) -> Optional[List[Tuple[dict, List[dict]]]]:
    """Partition waypoints so each subset's centroid matches a ship core."""
    sh = ships(frame)
    wps = waypoints(frame)
    n = len(wps)
    if len(sh) == 1:
        return [(sh[0], wps)]
    if len(sh) != 2 or n < 2:
        return None
    best = None
    for mask in range(1, 2**n - 1):
        a = [wps[i] for i in range(n) if mask & (1 << i)]
        b = [wps[i] for i in range(n) if not mask & (1 << i)]
        if not a or not b:
            continue
        ca = (sum(w["c"][0] for w in a) / len(a), sum(w["c"][1] for w in a) / len(a))
        cb = (sum(w["c"][0] for w in b) / len(b), sum(w["c"][1] for w in b) / len(b))
        for s0, s1 in (sh, list(reversed(sh))):
            e = (
                abs(ca[0] - s0["c"][0])
                + abs(ca[1] - s0["c"][1])
                + abs(cb[0] - s1["c"][0])
                + abs(cb[1] - s1["c"][1])
            )
            if best is None or e < best[0]:
                best = (e, [(s0, a), (s1, b)])
    return None if best is None else best[1]


def move_target(frame, goal: Pt, margin: int = 8) -> Pt:
    """Empty floor near goal, not inside any waypoint bbox, not on wall."""
    g = _plane(frame)
    gx, gy = goal
    bbs = [w["bbox"] for w in waypoints(frame)]
    cands: List[Tuple[int, int, int]] = []
    for y in range(max(0, gy - margin), min(g.shape[0], gy + margin + 1)):
        for x in range(max(0, gx - margin), min(g.shape[1], gx + margin + 1)):
            if int(g[y, x]) != FLOOR:
                continue
            if any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in bbs):
                continue
            cands.append((abs(x - gx) + abs(y - gy), x, y))
    if not cands:
        return goal
    cands.sort()
    return (cands[0][1], cands[0][2])


def plan_l1_clicks(frame) -> List[Pt]:
    """Open-loop L1 plan: move selected wp → select other → move to goal."""
    wps = waypoints(frame)
    gs = goals(frame)
    if len(gs) < 1 or len(wps) < 2:
        raise RuntimeError(f"L1 layout unexpected; wps={len(wps)} goals={len(gs)}")
    goal = gs[0]["c"]
    idle = [w for w in wps if not w["selected"]] or wps
    mt1 = move_target(frame, goal)
    mt2 = move_target(frame, goal)
    return [mt1, mt1, idle[0]["c"], mt2, mt2]


def score_frame(frame) -> float:
    """Selector hint: click-only board with ship core + waypoint crosses."""
    g = _plane(frame)
    if not np.any(g == SHIP_CORE):
        return 0.0
    wps = waypoints(frame)
    if len(wps) < 1:
        return 0.0
    score = 0.55
    if goals(frame):
        score += 0.25
    if np.any(g == WALL):
        score += 0.1
    return float(min(1.0, score))


__all__ = [
    "ship_center",
    "ships",
    "waypoints",
    "goals",
    "assign_waypoints",
    "move_target",
    "plan_l1_clicks",
    "score_frame",
]
