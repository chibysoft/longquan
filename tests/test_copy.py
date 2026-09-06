"""Copy primitive tests: cover/backproject geometry + LS20 fixture, offline.

Only the geometric contract is tested (no network, no arcengine):
  cover(rel_cells, pos, param) = source itself + one copy per offset
  backproject(...) returns in-board source origins that can hit a target,
  either with the source itself or with one of the copies.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from longquan.hypotheses import copy

GRID = 21

# Example L shape (relative to bbox origin) from tests/fixtures/README.md.
L_SHAPE = [(0, 0), (0, 1), (0, 2), (1, 2), (2, 2)]


def _fixture_frame():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "ls20_l1_frame.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return np.array(data["l1_reset"], dtype=np.int8)


def _target_cells(frame):
    """Board cells whose 3x3 block is dominated by color 11 (targets)."""
    cropped = frame[:63, :63]
    cells = set()
    for gy in range(GRID):
        for gx in range(GRID):
            block = cropped[gy * 3:gy * 3 + 3, gx * 3:gx * 3 + 3]
            if int((block == 11).sum()) >= 5:
                cells.add((gx, gy))
    return cells


def test_cover_returns_source_plus_all_copies():
    pos = (3, 4)
    param = [(5, 0), (0, 7)]
    expected = {
        (3, 4), (3, 5), (3, 6), (4, 6), (5, 6),          # source
        (8, 4), (8, 5), (8, 6), (9, 6), (10, 6),        # copy at +5x
        (3, 11), (3, 12), (3, 13), (4, 13), (5, 13),    # copy at +7y
    }
    assert copy.cover(L_SHAPE, pos, param) == expected


def test_cover_with_no_offsets_is_source_only():
    pos = (2, 2)
    covered = copy.cover(L_SHAPE, pos, [])
    assert covered == {(2, 2), (2, 3), (2, 4), (3, 4), (4, 4)}


def test_cover_deduplicates_overlapping_copies():
    covered = copy.cover([(0, 0)], (0, 0), [(1, 1), (1, 1), (0, 0)])
    assert covered == {(0, 0), (1, 1)}


def test_backproject_direct_and_copy_positions():
    rel = [(0, 0), (0, 1)]
    targets = [(5, 7), (8, 9)]
    param = [(1, 2)]
    cands = copy.backproject(rel, targets, param, GRID, GRID)
    # Source itself on a target.
    assert (5, 7) in cands and (5, 6) in cands
    assert (8, 9) in cands and (8, 8) in cands
    # One of the copies (+1x,+2y) on a target.
    assert (4, 5) in cands and (4, 4) in cands
    assert (7, 7) in cands and (7, 6) in cands
    assert all(0 <= x < GRID and 0 <= y < GRID for x, y in cands)


def test_backproject_filters_off_grid_origins():
    # Copy origins that would fall off the board are not candidates.
    cands = copy.backproject([(0, 0)], [(0, 0), (1, 0)], [(1, 0), (0, 1)], 2, 2)
    assert cands == [(0, 0), (1, 0)]


def test_backproject_without_targets_is_empty():
    assert copy.backproject(L_SHAPE, [], [(1, 1)], GRID, GRID) == []


def test_ls20_fixture_targets_and_cover_backproject():
    """LS20 integration: frame-driven targets + documented offset semantics."""
    frame = _fixture_frame()
    targets = sorted(_target_cells(frame))
    # Bottom row slots (5,20)..(17,20) as documented in fixtures/README.md.
    assert targets == [(gx, 20) for gx in range(5, 18)]

    pos = (0, 0)
    param = [(tx - pos[0], ty - pos[1]) for tx, ty in targets]

    covered = copy.cover(L_SHAPE, pos, param)
    assert set(targets) <= covered

    cands = copy.backproject(L_SHAPE, targets, param, GRID, GRID)
    assert cands
    assert pos in cands
    assert all(0 <= x < GRID and 0 <= y < GRID for x, y in cands)
    # At least one candidate covers every target when cover() is applied.
    assert any(set(targets) <= copy.cover(L_SHAPE, p, param) for p in cands)
