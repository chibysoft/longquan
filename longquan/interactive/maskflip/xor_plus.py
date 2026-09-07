"""xor_plus: click flips plus neighborhood (center + NSEW); skip glyph arms."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from longquan.interactive.maskflip.grid import (
    BLOCK,
    GAP,
    as_plane,
    changed_playable,
    flip_colors_in_block,
    infer_color_pair,
    plus_arms,
    resolve_click_block,
)


@dataclass(frozen=True)
class XorPlusParam:
    color_a: int
    color_b: int
    gap: int = GAP
    origin: tuple[int, int] | None = None


def score(obs) -> float:
    return 0.5


def step(grid, action_xy, param: XorPlusParam) -> np.ndarray:
    g = as_plane(grid)
    x, y = int(action_xy[0]), int(action_xy[1])
    if param.origin is not None:
        cx, cy = param.origin
    else:
        hit = resolve_click_block(
            g, x, y, prefer="checker", color_a=param.color_a, color_b=param.color_b
        )
        if hit is None:
            hit = resolve_click_block(
                g, x, y, prefer="any", color_a=param.color_a, color_b=param.color_b
            )
        if hit is None:
            return g.copy()
        cx, cy = hit
    out = g.copy()
    for ax, ay in plus_arms(out, cx, cy, gap=param.gap):
        out = flip_colors_in_block(out, ax, ay, param.color_a, param.color_b)
    return out


def backproject(before, after) -> List[XorPlusParam]:
    b = as_plane(before)
    a = as_plane(after)
    pair = infer_color_pair(b, a)
    if pair is None:
        return []
    ca, cb = pair
    changed = changed_playable(b, a, ca, cb)
    if len(changed) < 2:
        return []
    out: List[XorPlusParam] = []
    # Candidate centers: checker-like among changed, or any changed that
    # reproduces the exact changed set via plus_arms.
    for cx, cy in changed:
        arms = set(plus_arms(b, cx, cy, gap=GAP))
        if set(changed) == arms or set(changed).issubset(arms):
            # Verify applying plus matches after.
            pred = b.copy()
            for ax, ay in plus_arms(pred, cx, cy, gap=GAP):
                pred = flip_colors_in_block(pred, ax, ay, ca, cb)
            if np.array_equal(pred, a):
                out.append(XorPlusParam(color_a=ca, color_b=cb, gap=GAP, origin=(cx, cy)))
    if out:
        out.append(XorPlusParam(color_a=ca, color_b=cb, gap=GAP, origin=None))
    return out


def matches_sample(before, action_xy, after, param: XorPlusParam) -> bool:
    return np.array_equal(as_plane(step(before, action_xy, param)), as_plane(after))
