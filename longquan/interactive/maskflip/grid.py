"""Shared grid helpers for mask-flip transitions."""
from __future__ import annotations

from typing import Iterable, Sequence, Tuple

import numpy as np

BLOCK = 6
GAP = 8
GLYPH_COLORS = frozenset({0, 2})

ColorPair = Tuple[int, int]
BlockOrigin = Tuple[int, int]


def as_plane(frame) -> np.ndarray:
    a = np.asarray(frame, dtype=np.int16)
    return a[0] if a.ndim == 3 else a


def flip_colors_in_block(
    g: np.ndarray,
    ax: int,
    ay: int,
    color_a: int,
    color_b: int,
) -> np.ndarray:
    """Swap color_a ↔ color_b inside a BLOCK×BLOCK patch; other colors stay."""
    out = g.copy()
    patch = out[ay:ay + BLOCK, ax:ax + BLOCK]
    if patch.shape != (BLOCK, BLOCK):
        return out
    a_mask = patch == color_a
    b_mask = patch == color_b
    patch[a_mask] = color_b
    patch[b_mask] = color_a
    return out


def is_glyph_block(g: np.ndarray, ax: int, ay: int) -> bool:
    patch = g[ay:ay + BLOCK, ax:ax + BLOCK]
    if patch.shape != (BLOCK, BLOCK):
        return False
    return bool(np.any(np.isin(patch, list(GLYPH_COLORS))))


def is_solid_pair(g: np.ndarray, ax: int, ay: int, color_a: int, color_b: int) -> bool:
    patch = g[ay:ay + BLOCK, ax:ax + BLOCK]
    if patch.shape != (BLOCK, BLOCK):
        return False
    return bool(np.all(np.isin(patch, [color_a, color_b])) and (
        np.all(patch == color_a) or np.all(patch == color_b)
    ))


def is_checker_block(
    g: np.ndarray,
    ax: int,
    ay: int,
    color_a: int,
    color_b: int,
    deco: int = 6,
) -> bool:
    """Block uses only {color_a, color_b, deco} and contains deco (L5 checker)."""
    patch = g[ay:ay + BLOCK, ax:ax + BLOCK]
    if patch.shape != (BLOCK, BLOCK):
        return False
    if not np.any(patch == deco):
        return False
    return bool(np.all(np.isin(patch, [color_a, color_b, deco])))


def is_pip_block(
    g: np.ndarray,
    ax: int,
    ay: int,
    color_a: int,
    color_b: int,
    deco: int = 6,
) -> bool:
    """L6-style pip tile: exactly one 2×2 of deco, rest in {a,b}."""
    patch = g[ay:ay + BLOCK, ax:ax + BLOCK]
    if patch.shape != (BLOCK, BLOCK):
        return False
    if int(np.sum(patch == deco)) != 4:
        return False
    return bool(np.all(np.isin(patch, [color_a, color_b, deco])))


def block_phase(g: np.ndarray, ax: int, ay: int, color_a: int, color_b: int) -> int:
    patch = g[ay:ay + BLOCK, ax:ax + BLOCK]
    na = int(np.sum(patch == color_a))
    nb = int(np.sum(patch == color_b))
    return color_b if nb > na else color_a


def blocks_containing(x: int, y: int, g: np.ndarray | None = None) -> list[BlockOrigin]:
    """All even-origin BLOCK windows that contain pixel (x,y)."""
    out = []
    for ay in range(max(0, y - BLOCK + 1), y + 1):
        if ay % 2:
            continue
        for ax in range(max(0, x - BLOCK + 1), x + 1):
            if ax % 2:
                continue
            if ax <= x < ax + BLOCK and ay <= y < ay + BLOCK:
                if g is not None and (
                    ax + BLOCK > g.shape[1] or ay + BLOCK > g.shape[0]
                ):
                    continue
                out.append((ax, ay))
    return out


def resolve_click_block(
    g: np.ndarray,
    x: int,
    y: int,
    *,
    prefer: str = "any",
    color_a: int | None = None,
    color_b: int | None = None,
) -> BlockOrigin | None:
    """Pick the playable block under a click.

    prefer: 'solid' | 'checker' | 'pip' | 'any'
    """
    cands = blocks_containing(x, y, g)
    if not cands:
        return None
    if color_a is None or color_b is None:
        return cands[0]

    scored: list[tuple[int, BlockOrigin]] = []
    for ax, ay in cands:
        if prefer == "checker" and is_checker_block(g, ax, ay, color_a, color_b):
            scored.append((0, (ax, ay)))
        elif prefer == "pip" and is_pip_block(g, ax, ay, color_a, color_b):
            scored.append((0, (ax, ay)))
        elif prefer == "solid" and is_solid_pair(g, ax, ay, color_a, color_b):
            scored.append((0, (ax, ay)))
        elif prefer == "any":
            if is_checker_block(g, ax, ay, color_a, color_b):
                scored.append((0, (ax, ay)))
            elif is_pip_block(g, ax, ay, color_a, color_b):
                scored.append((1, (ax, ay)))
            elif is_solid_pair(g, ax, ay, color_a, color_b):
                scored.append((2, (ax, ay)))
            elif np.any(np.isin(g[ay:ay + BLOCK, ax:ax + BLOCK], [color_a, color_b])):
                scored.append((3, (ax, ay)))
    if not scored:
        return cands[0]
    scored.sort(key=lambda t: t[0])
    return scored[0][1]


def plus_arms(
    g: np.ndarray,
    cx: int,
    cy: int,
    gap: int = GAP,
) -> list[BlockOrigin]:
    arms = [(cx, cy)]
    for dx, dy in ((0, -gap), (0, gap), (-gap, 0), (gap, 0)):
        nx, ny = cx + dx, cy + dy
        if nx < 0 or ny < 0 or nx + BLOCK > g.shape[1] or ny + BLOCK > g.shape[0]:
            continue
        if is_glyph_block(g, nx, ny):
            continue
        arms.append((nx, ny))
    return arms


def playable_origins(
    g: np.ndarray,
    color_a: int,
    color_b: int,
    *,
    deco: int = 6,
) -> list[BlockOrigin]:
    """Even-origin blocks that look like solid / checker / pip for the pair."""
    out = []
    for ay in range(0, g.shape[0] - BLOCK + 1, 2):
        for ax in range(0, g.shape[1] - BLOCK + 1, 2):
            if (
                is_solid_pair(g, ax, ay, color_a, color_b)
                or is_checker_block(g, ax, ay, color_a, color_b, deco=deco)
                or is_pip_block(g, ax, ay, color_a, color_b, deco=deco)
            ):
                out.append((ax, ay))
    return out


def changed_blocks(
    before: np.ndarray,
    after: np.ndarray,
    origins: Iterable[BlockOrigin] | None = None,
) -> list[BlockOrigin]:
    if origins is None:
        origins = []
        for ay in range(0, before.shape[0] - BLOCK + 1, 2):
            for ax in range(0, before.shape[1] - BLOCK + 1, 2):
                origins.append((ax, ay))
    out = []
    for ax, ay in origins:
        if not np.array_equal(
            before[ay:ay + BLOCK, ax:ax + BLOCK],
            after[ay:ay + BLOCK, ax:ax + BLOCK],
        ):
            out.append((ax, ay))
    return out


def changed_playable(
    before: np.ndarray,
    after: np.ndarray,
    color_a: int,
    color_b: int,
) -> list[BlockOrigin]:
    """Changed blocks among playable origins only (avoids overlap phantoms)."""
    # Union of playable before/after so flipped solids still count.
    origins = set(playable_origins(before, color_a, color_b)) | set(
        playable_origins(after, color_a, color_b)
    )
    return changed_blocks(before, after, origins=origins)


def infer_color_pair(before: np.ndarray, after: np.ndarray) -> ColorPair | None:
    """Infer the unique swapped color pair from a full-frame diff."""
    mask = before != after
    if not np.any(mask):
        return None
    pairs = set()
    for b, a in zip(before[mask].tolist(), after[mask].tolist()):
        pairs.add(tuple(sorted((int(b), int(a)))))
    if len(pairs) != 1:
        return None
    lo, hi = next(iter(pairs))
    return (lo, hi)
