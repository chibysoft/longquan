"""xor_north: flip self; if north neighbor is same-family tile, flip it too."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

import numpy as np

from longquan.interactive.maskflip.grid import (
    BLOCK,
    GAP,
    as_plane,
    changed_playable,
    flip_colors_in_block,
    infer_color_pair,
    is_pip_block,
    resolve_click_block,
)


@dataclass(frozen=True)
class XorNorthParam:
    color_a: int
    color_b: int
    gap: int = GAP
    origin: tuple[int, int] | None = None
    # 'pip' = L6 pip tiles; 'pair' = any block using only {a,b} (+optional deco)
    family: str = "pip"


def score(obs) -> float:
    return 0.45


def _in_family(g, ax, ay, param: XorNorthParam) -> bool:
    if param.family == "pip":
        return is_pip_block(g, ax, ay, param.color_a, param.color_b)
    patch = g[ay:ay + BLOCK, ax:ax + BLOCK]
    if patch.shape != (BLOCK, BLOCK):
        return False
    return bool(np.any(np.isin(patch, [param.color_a, param.color_b])))


def north_effect(g, origin, param: XorNorthParam) -> list[tuple[int, int]]:
    ax, ay = origin
    eff = [(ax, ay)]
    nx, ny = ax, ay - param.gap
    if nx >= 0 and ny >= 0 and nx + BLOCK <= g.shape[1] and ny + BLOCK <= g.shape[0]:
        if _in_family(g, nx, ny, param):
            eff.append((nx, ny))
    return eff


def step(grid, action_xy, param: XorNorthParam) -> np.ndarray:
    g = as_plane(grid)
    x, y = int(action_xy[0]), int(action_xy[1])
    if param.origin is not None:
        cx, cy = param.origin
    else:
        hit = resolve_click_block(
            g, x, y, prefer="pip", color_a=param.color_a, color_b=param.color_b
        )
        if hit is None:
            hit = resolve_click_block(
                g, x, y, prefer="any", color_a=param.color_a, color_b=param.color_b
            )
        if hit is None:
            return g.copy()
        cx, cy = hit
    out = g.copy()
    for ax, ay in north_effect(out, (cx, cy), param):
        out = flip_colors_in_block(out, ax, ay, param.color_a, param.color_b)
    return out


def backproject(before, after) -> List[XorNorthParam]:
    b = as_plane(before)
    a = as_plane(after)
    pair = infer_color_pair(b, a)
    if pair is None:
        return []
    ca, cb = pair
    changed = changed_playable(b, a, ca, cb)
    out: List[XorNorthParam] = []
    for family in ("pip", "pair"):
        for cx, cy in changed:
            param = XorNorthParam(color_a=ca, color_b=cb, gap=GAP, origin=(cx, cy), family=family)
            if set(north_effect(b, (cx, cy), param)) != set(changed):
                continue
            pred = b.copy()
            for ax, ay in north_effect(pred, (cx, cy), param):
                pred = flip_colors_in_block(pred, ax, ay, ca, cb)
            if np.array_equal(pred, a):
                out.append(param)
        if any(p.family == family for p in out):
            out.append(XorNorthParam(color_a=ca, color_b=cb, gap=GAP, origin=None, family=family))
    return out


def matches_sample(before, action_xy, after, param: XorNorthParam) -> bool:
    return np.array_equal(as_plane(step(before, action_xy, param)), as_plane(after))
