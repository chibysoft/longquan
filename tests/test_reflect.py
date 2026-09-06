"""Reflect primitive tests: cover/backproject geometry, offline.

Only geometric semantics are tested (no network, no arcengine):
  cover = source cells + reflections over the given mirror lines
  backproject = in-board source origins that hit a target directly or through
  one reflection.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from longquan.hypotheses import reflect

# L shape as seen in tests/test_loop.py (relative to bbox origin).
L_SHAPE = [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)]


def test_cover_no_lines_is_source_only():
    covered = reflect.cover(L_SHAPE, (0, 0), [])
    assert covered == set(L_SHAPE)


def test_cover_single_vertical_line():
    covered = reflect.cover(L_SHAPE, (0, 0), [("V", 5)])
    expected = {
        (0, 0), (1, 0), (2, 0), (2, 1), (2, 2),    # source
        (10, 0), (9, 0), (8, 0), (8, 1), (8, 2),   # mirror x -> 10 - x
    }
    assert covered == expected


def test_cover_single_horizontal_line():
    covered = reflect.cover(L_SHAPE, (1, 1), [("H", 4)])
    expected = {
        (1, 1), (2, 1), (3, 1), (3, 2), (3, 3),    # source
        (1, 7), (2, 7), (3, 7), (3, 6), (3, 5),    # mirror y -> 8 - y
    }
    assert covered == expected


def test_cover_supports_line_outside_board():
    # Mirror lines may sit outside the board; geometry still applies.
    covered = reflect.cover([(0, 0)], (0, 0), [("V", -1)])
    assert covered == {(0, 0), (-2, 0)}


def test_backproject_direct_and_single_reflection():
    # AR25 L1 geometry (known solution, offline): line V x=10, piece to (1,15).
    targets = [(19, 15), (17, 17), (17, 16), (17, 15), (18, 15)]
    cands = reflect.backproject(L_SHAPE, targets, [("V", 10)], 21, 21)
    assert (1, 15) in cands
    assert set(targets) <= reflect.cover(L_SHAPE, (1, 15), [("V", 10)])


def test_backproject_clips_off_board_origins():
    # Mirror of the target lands at x=-19 for a line at x=0: origin off board.
    cands = reflect.backproject([(0, 0)], [(19, 0)], [("V", 0)], 21, 21)
    assert cands == [(19, 0)]


def test_backproject_without_lines_is_direct_only():
    cands = reflect.backproject([(1, 1)], [(5, 5)], [], 21, 21)
    assert cands == [(4, 4)]


def test_line_candidates_include_outside_board_values():
    cands = reflect.line_candidates(21, 21)
    assert cands[0] < 0
    assert cands[-1] > 20
    assert 0 in cands and 20 in cands
