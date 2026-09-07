"""Mask-flip transition primitives (ft09 click → next frame).

Interactive `step(grid, action_xy, param)` family — NOT geometric cover.
Two layers live elsewhere: goal decode + GF(2) planning (see goal.py).
"""
from __future__ import annotations

from longquan.interactive.maskflip import flip_block, xor_north, xor_plus
from longquan.interactive.maskflip.grid import BLOCK, GAP, as_plane
from longquan.interactive.maskflip.induce import TransitionProgram, induce_transition
from longquan.interactive.maskflip.goal import decode_l4_like_targets, plan_clicks_gf2

__all__ = [
    "BLOCK",
    "GAP",
    "as_plane",
    "flip_block",
    "xor_plus",
    "xor_north",
    "induce_transition",
    "TransitionProgram",
    "decode_l4_like_targets",
    "plan_clicks_gf2",
]
