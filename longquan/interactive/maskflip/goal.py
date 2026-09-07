"""Goal-layer: L4-like target decode + GF(2) click planning (not transition)."""
from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, List, Sequence, Tuple

import numpy as np

from longquan.interactive.maskflip.grid import BLOCK, GAP, as_plane, plus_arms
from longquan.interactive.maskflip.xor_north import XorNorthParam, north_effect

Block = Tuple[int, int]
SKIP_LAB = 3


def find_instr_patches(
    g: np.ndarray,
    *,
    palette: Sequence[int],
) -> list[dict]:
    """6×6 macros with 0+2, uniform center in palette, no bg-4."""
    out = []
    seen = set()
    pal = set(palette)
    for y in range(0, g.shape[0] - 5, 2):
        for x in range(0, g.shape[1] - 5, 2):
            p = g[y:y + 6, x:x + 6]
            vals = {int(v) for v in p.flatten().tolist()}
            if 4 in vals or 0 not in vals or 2 not in vals:
                continue
            center = p[2:4, 2:4]
            if not np.all(center == center[0, 0]):
                continue
            fcol = int(center[0, 0])
            if fcol not in pal:
                continue
            macro = {}
            ok = True
            for r in range(3):
                for c in range(3):
                    cell = p[2 * r:2 * r + 2, 2 * c:2 * c + 2]
                    if not np.all(cell == cell[0, 0]):
                        ok = False
                        break
                    macro[(r, c)] = int(cell[0, 0])
                if not ok:
                    break
            if not ok or (x, y) in seen:
                continue
            seen.add((x, y))
            out.append({
                "origin": (x, y),
                "fixed_color": fcol,
                "macro": macro,
            })
    out.sort(key=lambda t: (t["origin"][1], t["origin"][0]))
    return out


def decode_l4_like_targets(
    patches: Sequence[dict],
    *,
    base_color: int,
    flip_to: int,
    skip_lab: int = SKIP_LAB,
    gap: int = GAP,
) -> Dict[Block, int]:
    """0→fixed, 2→other; require multi-patch agreement."""
    votes: dict[Block, list[int]] = defaultdict(list)
    for p in patches:
        ix, iy = p["origin"]
        ox, oy = ix - gap, iy - gap
        fixed = int(p["fixed_color"])
        other = base_color if fixed == flip_to else flip_to
        macro = p["macro"]
        for r in range(3):
            for c in range(3):
                if (r, c) == (1, 1):
                    continue
                if f"{r},{c}" in macro:
                    lab = macro[f"{r},{c}"]
                elif (r, c) in macro:
                    lab = macro[(r, c)]
                else:
                    continue
                if lab == skip_lab:
                    continue
                ax, ay = ox + gap * c, oy + gap * r
                des = fixed if lab == 0 else other
                votes[(ax, ay)].append(int(des))
    want: Dict[Block, int] = {}
    for cell, cols in votes.items():
        if len(set(cols)) != 1:
            raise RuntimeError(f"target conflict at {cell}: {cols}")
        want[cell] = cols[0]
    return want


def gf2_solve(A: np.ndarray, b: np.ndarray) -> np.ndarray | None:
    A = (A.copy() % 2).astype(int)
    b = (b.copy() % 2).astype(int)
    m, n = A.shape
    M = np.concatenate([A, b.reshape(-1, 1)], axis=1)
    row = 0
    pivots = [-1] * n
    for col in range(n):
        piv = None
        for i in range(row, m):
            if M[i, col] == 1:
                piv = i
                break
        if piv is None:
            continue
        M[[row, piv]] = M[[piv, row]]
        for i in range(m):
            if i != row and M[i, col] == 1:
                M[i] = (M[i] + M[row]) % 2
        pivots[col] = row
        row += 1
    for i in range(row, m):
        if M[i, -1] == 1 and not np.any(M[i, :-1]):
            return None
    x = np.zeros(n, dtype=int)
    for col in range(n):
        if pivots[col] >= 0:
            x[col] = M[pivots[col], -1]
    return x


def plan_clicks_gf2(
    g: np.ndarray,
    want: Dict[Block, int],
    *,
    flip_to: int,
    clickables: Sequence[Block],
    effect_fn: Callable[[Block], Sequence[Block]],
    initial_phase: Callable[[Block], int] | None = None,
) -> List[Block]:
    """Solve GF(2): which clickables to fire so each want cell reaches flip_to bit."""
    tile_set = list(clickables)
    idx = {c: i for i, c in enumerate(tile_set)}
    n = len(tile_set)
    # Only constrain cells that appear in want AND can be affected.
    rows = []
    bb = []
    for t, w in sorted(want.items()):
        row = [0] * n
        for src in tile_set:
            if t in effect_fn(src):
                row[idx[src]] = 1
        if not any(row):
            # unconstrained / unreachable — skip if already satisfied
            continue
        rows.append(row)
        cur = 0
        if initial_phase is not None:
            cur = 1 if initial_phase(t) == flip_to else 0
        target = 1 if w == flip_to else 0
        bb.append(target ^ cur)

    if not rows:
        return []
    x = gf2_solve(np.array(rows, dtype=int), np.array(bb, dtype=int))
    if x is None:
        raise RuntimeError("GF(2) inconsistent")
    return [c for c, bit in zip(tile_set, x) if bit]


def effect_xor_plus(g: np.ndarray, gap: int = GAP):
    def _eff(src: Block) -> list[Block]:
        return plus_arms(g, src[0], src[1], gap=gap)
    return _eff


def effect_xor_north(g: np.ndarray, color_a: int, color_b: int, gap: int = GAP, family: str = "pip"):
    param = XorNorthParam(color_a=color_a, color_b=color_b, gap=gap, family=family)

    def _eff(src: Block) -> list[Block]:
        return north_effect(g, src, param)
    return _eff


def effect_unit():
    def _eff(src: Block) -> list[Block]:
        return [src]
    return _eff


def effect_l5_solid_and_checker(
    g: np.ndarray,
    checkers: Sequence[Block],
    gap: int = GAP,
):
    """Solid click = unit; checker click = plus arms (as seated on L5)."""
    chk = set(checkers)

    def _eff(src: Block) -> list[Block]:
        if src in chk:
            return plus_arms(g, src[0], src[1], gap=gap)
        return [src]
    return _eff
