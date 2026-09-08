"""r11l L2 clearer core: park nearest ship, migrate other along clearance path."""
from __future__ import annotations

from collections import deque
from typing import List, Optional, Tuple

import numpy as np

from longquan.interactive import r11l

Pt = Tuple[int, int]
FLOOR, WALL, HAZARD = 5, 2, 10


def _plane(frame):
    a = np.asarray(frame)
    return a[0] if a.ndim == 3 else a


def centroid(wps: List[Pt]) -> Tuple[float, float]:
    n = len(wps)
    return (sum(p[0] for p in wps) / n, sum(p[1] for p in wps) / n)


def ship_footprint_ok(g, x: int, y: int) -> bool:
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < 64 and 0 <= ny < 64):
                return False
            if int(g[ny, nx]) in (WALL, HAZARD):
                return False
    return True


def centroid_ok(wps: List[Pt], g) -> bool:
    cx, cy = centroid(wps)
    return ship_footprint_ok(g, int(round(cx)), int(round(cy)))


def centroid_path_ok(wps_before: List[Pt], wps_after: List[Pt], g, samples: int = 5) -> bool:
    """Reject moves whose interpolated centroid brushes hazard."""
    for t in range(samples + 1):
        u = t / samples
        mid = [
            (int(round(a[0] * (1 - u) + b[0] * u)), int(round(a[1] * (1 - u) + b[1] * u)))
            for a, b in zip(wps_before, wps_after)
        ]
        if not centroid_ok(mid, g):
            return False
    return True


def clearance_path(frame, start: Pt, goal: Pt, step: int = 10) -> Optional[List[Pt]]:
    g = _plane(frame)
    seeds = []
    if ship_footprint_ok(g, *start):
        seeds = [start]
    else:
        for rad in range(1, 8):
            for dy in range(-rad, rad + 1):
                for dx in range(-rad, rad + 1):
                    if max(abs(dx), abs(dy)) != rad:
                        continue
                    p = (start[0] + dx, start[1] + dy)
                    if ship_footprint_ok(g, *p):
                        seeds.append(p)
            if seeds:
                break
    if not seeds:
        return None
    q = deque()
    prev = {}
    for s in seeds:
        q.append(s)
        prev[s] = None
    end = None
    while q:
        x, y = q.popleft()
        if abs(x - goal[0]) + abs(y - goal[1]) <= 3 and ship_footprint_ok(g, x, y):
            end = (x, y)
            break
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) in prev:
                continue
            if not ship_footprint_ok(g, nx, ny):
                continue
            prev[(nx, ny)] = (x, y)
            q.append((nx, ny))
    if end is None:
        return None
    path = []
    cur = end
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    coarse = [path[0]]
    for p in path[1:]:
        if abs(p[0] - coarse[-1][0]) + abs(p[1] - coarse[-1][1]) >= step:
            coarse.append(p)
    if coarse[-1] != path[-1]:
        coarse.append(path[-1])
    return coarse


def stagger_pads(g, center: Pt, n: int) -> List[Pt]:
    out: List[Pt] = []
    cx, cy = center
    rad = 0
    while len(out) < n and rad <= 14:
        for dy in range(-rad, rad + 1):
            for dx in range(-rad, rad + 1):
                if rad > 0 and max(abs(dx), abs(dy)) != rad:
                    continue
                p = (cx + dx, cy + dy)
                if not (0 <= p[0] < 64 and 0 <= p[1] < 64):
                    continue
                if int(g[p[1], p[0]]) != FLOOR:
                    continue
                if not ship_footprint_ok(g, *p) and rad > 0:
                    # pad itself need not be ship-center; just floor + sep
                    pass
                if all(max(abs(p[0] - q[0]), abs(p[1] - q[1])) >= 5 for q in out):
                    out.append(p)
                    if len(out) >= n:
                        return out
        rad += 1
    return out


def nonlocked_wps(frame, locked: List[Pt]) -> List[Pt]:
    out = []
    for w in r11l.waypoints(frame):
        if any(abs(w["c"][0] - fx) + abs(w["c"][1] - fy) <= 2 for fx, fy in locked):
            continue
        out.append(w["c"])
    return out
