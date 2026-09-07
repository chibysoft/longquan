"""flip_block: toggle one BLOCK between a color pair (decorative colors stay)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from longquan.interactive.maskflip.grid import (
    BLOCK,
    ColorPair,
    as_plane,
    changed_playable,
    flip_colors_in_block,
    infer_color_pair,
    is_solid_pair,
    resolve_click_block,
)


@dataclass(frozen=True)
class FlipBlockParam:
    color_a: int
    color_b: int
    # Optional fixed origin; if None, resolved from click.
    origin: tuple[int, int] | None = None

    def as_pair(self) -> ColorPair:
        return (self.color_a, self.color_b)


def score(obs) -> float:
    """Prior: two dominant non-bg play colors suggest binary flip."""
    g = as_plane(getattr(obs, "grid", obs))
    vals, cnts = np.unique(g, return_counts=True)
    # Ignore bg 4 and UI 12 roughly.
    play = [(int(v), int(c)) for v, c in zip(vals, cnts) if int(v) not in (4, 12)]
    play.sort(key=lambda t: -t[1])
    if len(play) < 2:
        return 0.1
    return 0.55


def step(grid, action_xy, param: FlipBlockParam) -> np.ndarray:
    g = as_plane(grid)
    x, y = int(action_xy[0]), int(action_xy[1])
    if param.origin is not None:
        ax, ay = param.origin
    else:
        hit = resolve_click_block(
            g, x, y, prefer="solid", color_a=param.color_a, color_b=param.color_b
        )
        if hit is None:
            hit = resolve_click_block(
                g, x, y, prefer="any", color_a=param.color_a, color_b=param.color_b
            )
        if hit is None:
            return g.copy()
        ax, ay = hit
    return flip_colors_in_block(g, ax, ay, param.color_a, param.color_b)


def backproject(before, after) -> List[FlipBlockParam]:
    """Infer flip_block params from a single-block color swap."""
    b = as_plane(before)
    a = as_plane(after)
    pair = infer_color_pair(b, a)
    if pair is None:
        return []
    ca, cb = pair
    changed = changed_playable(b, a, ca, cb)
    # Prefer exactly one solid-like block change.
    solids = [
        (ax, ay) for ax, ay in changed
        if is_solid_pair(b, ax, ay, ca, cb) or is_solid_pair(a, ax, ay, ca, cb)
    ]
    out: List[FlipBlockParam] = []
    for ax, ay in (solids if solids else changed):
        # Must be a pure swap of the pair inside the block.
        pb = b[ay:ay + BLOCK, ax:ax + BLOCK]
        pa = a[ay:ay + BLOCK, ax:ax + BLOCK]
        if pb.shape != (BLOCK, BLOCK):
            continue
        ok = True
        for yy in range(BLOCK):
            for xx in range(BLOCK):
                vb, va = int(pb[yy, xx]), int(pa[yy, xx])
                if vb == va:
                    continue
                if {vb, va} != {ca, cb}:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            out.append(FlipBlockParam(color_a=ca, color_b=cb, origin=(ax, ay)))
    # Also offer unbound origin (resolve from click).
    if out:
        out.append(FlipBlockParam(color_a=ca, color_b=cb, origin=None))
    return out


def matches_sample(before, action_xy, after, param: FlipBlockParam) -> bool:
    pred = step(before, action_xy, param)
    return np.array_equal(as_plane(pred), as_plane(after))
