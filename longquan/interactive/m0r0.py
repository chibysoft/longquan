"""m0r0 frame model (closed-book recon).

Live-probed facts (2026-09-08, game_id=m0r0-492f87ba):

- Twin color-10 blocks; 5 floor; paints are walls (L1: 11/12, L2+: 6/15).
- Color 8 = hazard checker: motion may step onto it, but any further action
  while a footprint covers 8 soft-resets the level. Planner never expands
  hazard states.
- ACTION1..4: mirrored *intent*, independent per-piece motion (step = piece_w).
- Mate: flush-adjacent (merged CC), then compress:
  - horizontal join → ACTION4 (seated L1+L2+L3)
  - vertical stack → ACTION1/2 (seated L1; L2 vertical alone did not clear)
- L3+: color-9 markers are solid obstacles for pieces; relocate via
  ACTION6-select → steer → A6-on-ghost deposit, then mate as usual.
- After clear: n10 halves; leftover single block; next ACTION respawns next
  twin layout (piece_w may shrink: 5→4→…).

This module: perception + kinematics + mate planning — seated clearer uses it.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

FLOOR = 5
HAZARD = 8
PIECE = 10
PAINT_L = 11
PAINT_R = 12
PAINT_L2_L = 6
PAINT_L2_R = 15
# Engine allows stepping onto hazard; planner filters those states out.
WALKABLE = frozenset({FLOOR, HAZARD, PIECE})
# L3+ color-9 markers are solid for pieces (not walkable) and for other markers.
MARKER = 9
MARKER_BLOCK = frozenset({6, 15, 1, 8, 9, 10, 11})  # walls/hazard/ghosts/markers/pieces/paint-11
WALLS = frozenset({PAINT_L, PAINT_R, PAINT_L2_L, PAINT_L2_R})

BBox = Tuple[int, int, int, int]
PiecePair = Tuple[BBox, BBox]
Tl = Tuple[int, int]


@dataclass(frozen=True)
class KinParams:
    piece_w: int = 5
    step: int = 5
    mirror_sum: int = 58


L1 = KinParams(5, 5, 58)
L2 = KinParams(4, 4, 60)


def _plane(frame) -> np.ndarray:
    a = np.asarray(frame)
    return a[0] if a.ndim == 3 else a


def locate_pieces(frame) -> List[BBox]:
    g = _plane(frame)
    vis = np.zeros_like(g, dtype=bool)
    out: List[BBox] = []
    h, w = g.shape
    for y in range(h):
        for x in range(w):
            if g[y, x] != PIECE or vis[y, x]:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and not vis[ny, nx] and g[ny, nx] == PIECE:
                        vis[ny, nx] = True
                        q.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            out.append((min(xs), min(ys), max(xs), max(ys)))
    return sorted(out)


def infer_params(frame) -> KinParams:
    pcs = locate_pieces(frame)
    if len(pcs) != 2:
        if len(pcs) == 1:
            w = pcs[0][2] - pcs[0][0] + 1
            h = pcs[0][3] - pcs[0][1] + 1
            side = min(w, h)
            return KinParams(side, side, 64 - side - 1)
        return L1
    a, b = pcs
    pw = a[2] - a[0] + 1
    return KinParams(pw, pw, a[0] + b[0])


def mirror_tl_x(left_tl_x: int, params: KinParams = L1) -> int:
    return params.mirror_sum - left_tl_x


def _bb_from_tl(tl: Tl, w: int) -> BBox:
    x, y = tl
    return (x, y, x + w - 1, y + w - 1)


def _overlaps(a: BBox, b: BBox) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _edge_adjacent(a: BBox, b: BBox) -> Optional[str]:
    if a[0] == b[0] and a[2] == b[2]:
        if a[3] + 1 == b[1] or b[3] + 1 == a[1]:
            return "v"
    if a[1] == b[1] and a[3] == b[3]:
        if a[2] + 1 == b[0] or b[2] + 1 == a[0]:
            return "h"
    return None


def contact_from_merged(bb: BBox, piece_w: int) -> Optional[str]:
    w = bb[2] - bb[0] + 1
    h = bb[3] - bb[1] + 1
    if w == piece_w and h == 2 * piece_w:
        return "v"
    if h == piece_w and w == 2 * piece_w:
        return "h"
    return None


def hits_hazard(base: np.ndarray, pieces: Sequence[BBox]) -> bool:
    for x0, y0, x1, y1 in pieces:
        if np.any(base[y0:y1 + 1, x0:x1 + 1] == HAZARD):
            return True
    return False


def mate_compress_actions(frame, params: Optional[KinParams] = None) -> List[int]:
    pcs = locate_pieces(frame)
    if params is None:
        params = infer_params(frame) if len(pcs) == 2 else L1
    if len(pcs) == 1:
        axis = contact_from_merged(pcs[0], params.piece_w)
        if axis == "h":
            return [4]
        if axis == "v":
            return [1, 2]
        return []
    if len(pcs) != 2:
        return []
    axis = _edge_adjacent(pcs[0], pcs[1])
    if axis == "h":
        return [4]
    if axis == "v":
        return [1, 2]
    return []


def can_place_vs(g: np.ndarray, tl: Tl, block: BBox, piece_w: int) -> bool:
    x, y = tl
    if x < 0 or y < 0:
        return False
    h, w = g.shape
    if x + piece_w > w or y + piece_w > h:
        return False
    bx0, by0, bx1, by1 = block
    for yy in range(y, y + piece_w):
        for xx in range(x, x + piece_w):
            if bx0 <= xx <= bx1 and by0 <= yy <= by1:
                return False
            if int(g[yy, xx]) not in WALKABLE:
                return False
    return True


def intended_tls(left: BBox, right: BBox, aid: int, step: int) -> Optional[Tuple[Tl, Tl]]:
    deltas = {1: (0, -step), 2: (0, step), 3: (-step, 0), 4: (step, 0)}
    if aid not in deltas:
        return None
    dx, dy = deltas[aid]
    return (left[0] + dx, left[1] + dy), (right[0] - dx, right[1] + dy)


def apply_action(
    frame,
    pieces: Optional[Sequence[BBox]] = None,
    aid: int = 1,
    params: Optional[KinParams] = None,
) -> Optional[PiecePair]:
    g = _plane(frame)
    bbs = list(pieces) if pieces is not None else locate_pieces(frame)
    if len(bbs) != 2:
        return None
    if params is None:
        pw = bbs[0][2] - bbs[0][0] + 1
        params = KinParams(pw, pw, bbs[0][0] + bbs[1][0])
    left, right = bbs[0], bbs[1]
    intent = intended_tls(left, right, aid, params.step)
    if intent is None:
        return None
    nL_tl, nR_tl = intent
    move_l = can_place_vs(g, nL_tl, right, params.piece_w)
    move_r = can_place_vs(g, nR_tl, left, params.piece_w)
    if not move_l and not move_r:
        return None
    new_l = _bb_from_tl(nL_tl, params.piece_w) if move_l else left
    new_r = _bb_from_tl(nR_tl, params.piece_w) if move_r else right
    if _overlaps(new_l, new_r):
        return None
    return tuple(sorted([new_l, new_r]))  # type: ignore[return-value]


def synthesize_grid(base: np.ndarray, pieces: Sequence[BBox]) -> np.ndarray:
    g = base.copy()
    g[g == PIECE] = FLOOR
    for x0, y0, x1, y1 in pieces:
        g[y0:y1 + 1, x0:x1 + 1] = PIECE
    return g


def reachable(frame, params: Optional[KinParams] = None) -> Dict[PiecePair, List[int]]:
    """BFS avoiding hazard footprints (color 8)."""
    g0 = _plane(frame)
    start_list = locate_pieces(frame)
    if len(start_list) != 2:
        return {}
    if params is None:
        params = infer_params(frame)
    start: PiecePair = (start_list[0], start_list[1])
    if hits_hazard(g0, start):
        return {start: []}
    q = deque([start])
    seen: Dict[PiecePair, List[int]] = {start: []}
    while q:
        bbs = q.popleft()
        path = seen[bbs]
        if _edge_adjacent(bbs[0], bbs[1]):
            continue
        g = synthesize_grid(g0, bbs)
        for aid in (1, 2, 3, 4):
            nxt = apply_action(g, bbs, aid, params)
            if nxt is None or nxt in seen:
                continue
            if hits_hazard(g0, nxt):
                continue
            seen[nxt] = path + [aid]
            q.append(nxt)
    return seen


def find_mate_path(frame, params: Optional[KinParams] = None) -> Optional[List[int]]:
    """Shortest safe path to a mateable config + compress aid.

    Prefers horizontal join + ACTION4 (works L1 and L2). Falls back to
    vertical + ACTION1.
    """
    if params is None:
        params = infer_params(frame)
    pcs = locate_pieces(frame)
    if len(pcs) == 1:
        comp = mate_compress_actions(frame, params)
        return [comp[0]] if comp else None
    if len(pcs) != 2:
        return None
    comp0 = mate_compress_actions(frame, params)
    if comp0:
        return [comp0[0]]

    reach = reachable(frame, params)
    best_h: Optional[List[int]] = None
    best_v: Optional[List[int]] = None
    for bbs, path in reach.items():
        axis = _edge_adjacent(bbs[0], bbs[1])
        if axis == "h":
            cand = path + [4]
            if best_h is None or len(cand) < len(best_h):
                best_h = cand
        elif axis == "v":
            cand = path + [1]
            if best_v is None or len(cand) < len(best_v):
                best_v = cand
    return best_h or best_v


def color_blobs(frame, color: int) -> List[BBox]:
    """Axis-aligned bboxes of 4-connected components of `color`."""
    g = _plane(frame)
    h, w = g.shape
    vis = np.zeros_like(g, dtype=bool)
    out: List[BBox] = []
    for y in range(h):
        for x in range(w):
            if int(g[y, x]) != color or vis[y, x]:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells: List[Tl] = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and not vis[ny, nx] and int(g[ny, nx]) == color:
                        vis[ny, nx] = True
                        q.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            out.append((min(xs), min(ys), max(xs), max(ys)))
    return sorted(out)


def markers_blocking_mate(frame, params: Optional[KinParams] = None) -> List[BBox]:
    """Color-9 blobs whose removal alone would unlock a flush-mate path (L3)."""
    if find_mate_path(frame, params) is not None:
        return []
    g = _plane(frame).copy()
    blockers: List[BBox] = []
    for m in color_blobs(frame, MARKER):
        g2 = g.copy()
        x0, y0, x1, y1 = m
        g2[y0 : y1 + 1, x0 : x1 + 1] = FLOOR
        if find_mate_path([g2.tolist()], params) is not None:
            blockers.append(m)
    return blockers


def selected_marker_bbox(frame, w: Optional[int] = None) -> Optional[BBox]:
    """Compact color-11 marker while selected (walls may also be color 11)."""
    blobs = color_blobs(frame, 11)
    cands = []
    for b in blobs:
        bw, bh = b[2] - b[0] + 1, b[3] - b[1] + 1
        if bw != bh:
            continue
        if w is not None and bw != w:
            continue
        if 2 <= bw <= 5:
            cands.append(b)
    if not cands:
        return None
    # prefer exact w, else smallest compact square (not the wall mega-blob)
    cands.sort(key=lambda b: (b[2] - b[0] + 1) ** 2)
    return cands[0]


def infer_marker_size(frame) -> int:
    ms = color_blobs(frame, MARKER)
    if ms:
        return ms[0][2] - ms[0][0] + 1
    sel = selected_marker_bbox(frame)
    if sel:
        return sel[2] - sel[0] + 1
    return 2


def _marker_can_place(g: np.ndarray, tl: Tl, w: int = 2) -> bool:
    x, y = tl
    h, W = g.shape
    if x < 0 or y < 0 or x + w > W or y + w > h:
        return False
    return all(int(c) not in MARKER_BLOCK for c in g[y : y + w, x : x + w].ravel())


def _grid_without_markers(frame, w: Optional[int] = None) -> np.ndarray:
    g = _plane(frame).copy()
    for m in color_blobs(frame, MARKER):
        g[m[1] : m[3] + 1, m[0] : m[2] + 1] = FLOOR
    sel = selected_marker_bbox(frame, w)
    if sel is not None:
        g[sel[1] : sel[3] + 1, sel[0] : sel[2] + 1] = FLOOR
    return g


def marker_steer_path(
    frame,
    start_tl: Tl,
    goal_tl: Tl,
    step: Optional[int] = None,
    w: Optional[int] = None,
) -> Optional[List[int]]:
    """BFS for selected marker from start_tl to goal_tl."""
    if w is None:
        w = infer_marker_size(frame)
    if step is None:
        step = infer_params(frame).step
    g = _grid_without_markers(frame, w)
    if not _marker_can_place(g, goal_tl, w):
        return None
    q = deque([start_tl])
    prev: Dict[Tl, Optional[Tl]] = {start_tl: None}
    prev_a: Dict[Tl, Optional[int]] = {start_tl: None}
    deltas = {1: (0, -step), 2: (0, step), 3: (-step, 0), 4: (step, 0)}
    while q:
        cur = q.popleft()
        if cur == goal_tl:
            break
        for aid, (dx, dy) in deltas.items():
            nxt = (cur[0] + dx, cur[1] + dy)
            if nxt in prev:
                continue
            if _marker_can_place(g, nxt, w):
                prev[nxt] = cur
                prev_a[nxt] = aid
                q.append(nxt)
    if goal_tl not in prev:
        return None
    out: List[int] = []
    cur: Optional[Tl] = goal_tl
    while cur is not None and prev[cur] is not None:
        out.append(int(prev_a[cur]))  # type: ignore[arg-type]
        cur = prev[cur]
    return list(reversed(out))


def marker_reachable_tls(
    frame, start_tl: Tl, step: Optional[int] = None, w: Optional[int] = None
) -> List[Tl]:
    if w is None:
        w = infer_marker_size(frame)
    if step is None:
        step = infer_params(frame).step
    g = _grid_without_markers(frame, w)
    q = deque([start_tl])
    seen = {start_tl}
    deltas = ((0, -step), (0, step), (-step, 0), (step, 0))
    while q:
        x, y = q.popleft()
        for dx, dy in deltas:
            nxt = (x + dx, y + dy)
            if nxt in seen:
                continue
            if _marker_can_place(g, nxt, w):
                seen.add(nxt)
                q.append(nxt)
    return sorted(seen)


def mate_unlocking_marker_goals(
    frame, step: Optional[int] = None, w: Optional[int] = None
) -> List[Tl]:
    """Marker TLs where parking enables find_mate_path (L3/L4)."""
    ms = color_blobs(frame, MARKER)
    if not ms:
        return []
    if w is None:
        w = ms[0][2] - ms[0][0] + 1
    if step is None:
        step = infer_params(frame).step
    start = (ms[0][0], ms[0][1])
    base = _grid_without_markers(frame, w)
    q = deque([start])
    seen = {start}
    deltas = ((0, -step), (0, step), (-step, 0), (step, 0))
    while q:
        x, y = q.popleft()
        for dx, dy in deltas:
            nxt = (x + dx, y + dy)
            if nxt in seen:
                continue
            if _marker_can_place(base, nxt, w):
                seen.add(nxt)
                q.append(nxt)
    unlocking: List[Tl] = []
    params = infer_params(frame)
    scored: List[Tuple[int, Tl]] = []
    for tl in seen:
        g2 = base.copy()
        g2[tl[1] : tl[1] + w, tl[0] : tl[0] + w] = MARKER
        path = find_mate_path([g2.tolist()], params)
        if path is not None:
            scored.append((len(path), tl))
    scored.sort()
    return [tl for _, tl in scored]


def safe_marker_goals(frame, step: Optional[int] = None, w: Optional[int] = None) -> List[Tl]:
    """Parking goals: unlocking TLs when a single marker; else bottom lattice."""
    ms = color_blobs(frame, MARKER)
    if w is None:
        w = infer_marker_size(frame)
    if step is None:
        step = infer_params(frame).step
    if len(ms) == 1:
        unlock = mate_unlocking_marker_goals(frame, step=step, w=w)
        if unlock:
            return unlock
    g = _grid_without_markers(frame, w)
    # Align lattice to an existing marker (L3 homes are x≡3 mod 4, not x≡2).
    ox = ms[0][0] % step if ms else 0
    oy = ms[0][1] % step if ms else 0
    goals: List[Tl] = []
    y0 = 47 if w <= 2 else 40
    # snap y0 up to lattice
    y_start = y0 if y0 % step == oy else y0 + (oy - y0 % step) % step
    for y in range(y_start, 56, step):
        for x in range(ox, 56, step):
            if _marker_can_place(g, (x, y), w):
                goals.append((x, y))
    if goals:
        return goals
    for y in range(oy, 56, step):
        for x in range(ox, 56, step):
            if _marker_can_place(g, (x, y), w):
                goals.append((x, y))
    return goals


def score_frame(frame) -> float:
    g = _plane(frame)
    pcs = locate_pieces(frame)
    if len(pcs) not in (1, 2):
        return 0.0
    has_l1 = bool(np.any(g == PAINT_L) and np.any(g == PAINT_R))
    has_l2 = bool(np.any(g == PAINT_L2_L) and np.any(g == PAINT_L2_R))
    if not (has_l1 or has_l2):
        return 0.0
    if has_l1:
        n_l, n_r = int((g == PAINT_L).sum()), int((g == PAINT_R).sum())
    else:
        n_l, n_r = int((g == PAINT_L2_L).sum()), int((g == PAINT_L2_R).sum())
    bal = 1.0 - abs(n_l - n_r) / max(n_l + n_r, 1)
    return float(min(1.0, 0.55 + 0.4 * bal))


STEP = L1.step
PIECE_W = L1.piece_w
MIRROR_SUM = L1.mirror_sum


__all__ = [
    "locate_pieces",
    "apply_action",
    "reachable",
    "find_mate_path",
    "mate_compress_actions",
    "hits_hazard",
    "score_frame",
    "synthesize_grid",
    "infer_params",
    "mirror_tl_x",
    "color_blobs",
    "markers_blocking_mate",
    "marker_steer_path",
    "safe_marker_goals",
    "mate_unlocking_marker_goals",
    "selected_marker_bbox",
    "infer_marker_size",
    "KinParams",
    "L1",
    "L2",
    "FLOOR",
    "HAZARD",
    "PIECE",
    "MARKER",
    "STEP",
    "WALKABLE",
]
