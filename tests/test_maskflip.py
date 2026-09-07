"""Offline tests for mask-flip transition primitives + induction + goal GF2."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from longquan.interactive.maskflip import (
    flip_block,
    xor_north,
    xor_plus,
    induce_transition,
    decode_l4_like_targets,
    plan_clicks_gf2,
)
from longquan.interactive.maskflip.flip_block import FlipBlockParam
from longquan.interactive.maskflip.xor_plus import XorPlusParam
from longquan.interactive.maskflip.xor_north import XorNorthParam
from longquan.interactive.maskflip.grid import (
    BLOCK,
    as_plane,
    flip_colors_in_block,
    is_checker_block,
    is_pip_block,
    is_solid_pair,
)
from longquan.interactive.maskflip.goal import (
    effect_l5_solid_and_checker,
    effect_xor_north,
    find_instr_patches,
)
from tools.ft09_l5_click_flip_probe import (
    find_checker_blocks,
    find_l5_instr_patches,
    plan_l5_gf2,
)
from tools.ft09_l6_click_flip_probe import find_pip_tiles, plan_l6_gf2

ROOT = Path(__file__).resolve().parents[1]
L5 = ROOT / "tests" / "fixtures" / "ft09_l5_frame_live.json"
L6 = ROOT / "tests" / "fixtures" / "ft09_l6_frame_live.json"


def _load(path: Path) -> np.ndarray:
    raw = json.loads(path.read_text(encoding="utf-8"))
    frame = raw["frame"] if isinstance(raw, dict) and "frame" in raw else raw
    return as_plane(frame)


@pytest.fixture(scope="module")
def g5():
    return _load(L5)


@pytest.fixture(scope="module")
def g6():
    return _load(L6)


def test_flip_block_solid_l5(g5):
    ax, ay = 14, 12
    assert is_solid_pair(g5, ax, ay, 14, 15)
    param = FlipBlockParam(color_a=14, color_b=15, origin=(ax, ay))
    after = flip_block.step(g5, (ax + 3, ay + 3), param)
    assert np.all(after[ay:ay + BLOCK, ax:ax + BLOCK] == 15)
    # neighbors unchanged
    assert np.array_equal(
        after[ay:ay + BLOCK, ax + 8:ax + 8 + BLOCK],
        g5[ay:ay + BLOCK, ax + 8:ax + 8 + BLOCK],
    )


def test_xor_plus_checker_l5(g5):
    cx, cy = 22, 12
    assert is_checker_block(g5, cx, cy, 14, 15)
    param = XorPlusParam(color_a=14, color_b=15, origin=(cx, cy))
    after = xor_plus.step(g5, (cx + 3, cy + 3), param)
    # self phase 14→15 (deco 6 stays)
    assert int(np.sum(after[cy:cy + BLOCK, cx:cx + BLOCK] == 15)) == 20
    assert int(np.sum(after[cy:cy + BLOCK, cx:cx + BLOCK] == 6)) == 16
    # north solid becomes 15
    assert np.all(after[4:10, 22:28] == 15)
    # east/west solids
    assert np.all(after[12:18, 14:20] == 15)
    assert np.all(after[12:18, 30:36] == 15)


def test_xor_plus_skips_glyph_arm(g5):
    # (22,28) south arm is glyph — should not change glyph block
    cx, cy = 22, 28
    param = XorPlusParam(color_a=14, color_b=15, origin=(cx, cy))
    before_glyph = g5[36:42, 22:28].copy()
    after = xor_plus.step(g5, (cx + 3, cy + 3), param)
    assert np.array_equal(after[36:42, 22:28], before_glyph)
    assert np.all(after[28:34, 14:20] == 15)  # west flipped


def test_xor_north_l6_with_and_without_north(g6):
    # (4,6) has no north pip → only self
    p = XorNorthParam(color_a=11, color_b=14, origin=(4, 6), family="pip")
    after = xor_north.step(g6, (7, 9), p)
    assert int(np.sum(after[6:12, 4:10] == 14)) == 32
    assert int(np.sum(after[14:20, 4:10] == 11)) == 32  # south unchanged

    # (4,14) has north pip → flips both
    p2 = XorNorthParam(color_a=11, color_b=14, origin=(4, 14), family="pip")
    after2 = xor_north.step(g6, (7, 17), p2)
    assert int(np.sum(after2[6:12, 4:10] == 14)) == 32
    assert int(np.sum(after2[14:20, 4:10] == 14)) == 32


def test_backproject_flip_and_plus(g5):
    ax, ay = 30, 4
    after = flip_colors_in_block(g5, ax, ay, 14, 15)
    params = flip_block.backproject(g5, after)
    assert any(p.origin is None and {p.color_a, p.color_b} == {14, 15} for p in params)

    cx, cy = 22, 12
    pred = g5.copy()
    for ox, oy in ((22, 12), (22, 4), (14, 12), (30, 12), (22, 20)):
        pred = flip_colors_in_block(pred, ox, oy, 14, 15)
    params2 = xor_plus.backproject(g5, pred)
    assert any(p.origin is None for p in params2)


def test_induce_transition_l5_branch(g5):
    # Build synthetic samples: solid flip + checker plus
    s_before = g5
    s_after = flip_block.step(
        s_before, (17, 15), FlipBlockParam(14, 15, origin=(14, 12))
    )
    c_after = xor_plus.step(
        s_before, (25, 15), XorPlusParam(14, 15, origin=(22, 12))
    )
    train = [
        (s_before, (17, 15), s_after),
        (s_before, (25, 15), c_after),
    ]
    # holdout: another solid
    h_after = flip_block.step(
        s_before, (33, 7), FlipBlockParam(14, 15, origin=(30, 4))
    )
    holdout = [(s_before, (33, 7), h_after)]
    prog = induce_transition(train, max_complexity=2, holdout=holdout)
    assert prog is not None
    assert prog.kind == "branch_appearance"
    assert prog.satisfies(train + holdout)


def test_induce_transition_l6_north(g6):
    a1 = xor_north.step(g6, (7, 9), XorNorthParam(11, 14, origin=(4, 6)))
    a2 = xor_north.step(g6, (7, 17), XorNorthParam(11, 14, origin=(4, 14)))
    train = [(g6, (7, 9), a1), (g6, (7, 17), a2)]
    prog = induce_transition(train, max_complexity=2)
    assert prog is not None
    assert prog.satisfies(train)


def test_goal_l5_decode_and_gf2_matches_probe(g5):
    seated = plan_l5_gf2(g5)
    patches = find_instr_patches(g5, palette=(14, 15))
    for p in patches:
        p["macro"] = {
            f"{r},{c}": p["macro"][(r, c)] for r in range(3) for c in range(3)
        }
    want = decode_l4_like_targets(patches, base_color=14, flip_to=15)
    assert want == {
        tuple(map(int, k.split(","))): v for k, v in seated["want"].items()
    }
    checkers = [tuple(c) for c in seated["checkers"]]
    # Variables = solids ∪ checkers from seated plan vars
    clickables = []
    for ax, ay in sorted(want):
        if (ax, ay) not in checkers:
            clickables.append((ax, ay))
    # include all solids that appear in plus arms / seated solids list
    for a, b in seated["plan_solids"]:
        if (a, b) not in clickables:
            clickables.append((a, b))
    for c in checkers:
        if c not in clickables:
            clickables.append(c)
    # Also include any solid in seated plan vars: use affected from plus
    from longquan.interactive.maskflip.grid import plus_arms
    affected = set(want)
    for c in checkers:
        affected.update(plus_arms(g5, c[0], c[1]))
    solids = sorted(c for c in affected if c not in set(checkers))
    clickables = solids + checkers
    plan = plan_clicks_gf2(
        g5,
        want,
        flip_to=15,
        clickables=clickables,
        effect_fn=effect_l5_solid_and_checker(g5, checkers),
    )
    expected = {(a, b) for a, b in seated["plan_solids"]} | {
        (a, b) for a, b in seated["plan_checkers"]
    }
    assert set(plan) == expected


def test_goal_l6_plan_matches_probe(g6):
    seated = plan_l6_gf2(g6)
    tiles = [tuple(t) for t in seated["tiles"]]
    patches = find_instr_patches(g6, palette=(11, 14))
    for p in patches:
        p["macro"] = {
            f"{r},{c}": p["macro"][(r, c)] for r in range(3) for c in range(3)
        }
    want = decode_l4_like_targets(patches, base_color=11, flip_to=14)
    want_tiles = {c: w for c, w in want.items() if c in set(tiles)}
    plan = plan_clicks_gf2(
        g6,
        want_tiles,
        flip_to=14,
        clickables=tiles,
        effect_fn=effect_xor_north(g6, 11, 14),
    )
    assert set(plan) == {tuple(x) for x in seated["plan"]}
