"""m0r0 offline kinematics vs frozen L1 fixture."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from longquan.interactive import m0r0

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "m0r0_l1_frame_live.json")


def _frame():
    data = json.loads(open(FIX, encoding="utf-8").read())
    return data["frame"]


def test_locate_two_5x5_pieces():
    pcs = m0r0.locate_pieces(_frame())
    assert len(pcs) == 2
    assert pcs[0] == (19, 49, 23, 53)
    assert pcs[1] == (39, 49, 43, 53)
    assert m0r0.mirror_tl_x(pcs[0][0]) == pcs[1][0]


def test_reachable_more_than_lockstep_13():
    reach = m0r0.reachable(_frame())
    # Independent motion expands beyond the old strict-lockstep 13.
    assert len(reach) > 13
    start = tuple(m0r0.locate_pieces(_frame()))
    assert start in reach
    assert reach[start] == []


def test_up_then_left_matches_model():
    fr = _frame()
    a = m0r0.apply_action(fr, aid=1)
    assert a == ((19, 44, 23, 48), (39, 44, 43, 48))
    b = m0r0.apply_action(fr, pieces=a, aid=3)
    assert b == ((14, 44, 18, 48), (44, 44, 48, 48))


def test_second_up_moves_only_left():
    """Right is blocked by paint-12; left can still climb (live-corrected)."""
    fr = _frame()
    after_up = m0r0.apply_action(fr, aid=1)
    again = m0r0.apply_action(fr, pieces=after_up, aid=1)
    assert again is not None
    assert again[0] == (19, 39, 23, 43)  # left climbed
    assert again[1] == (39, 44, 43, 48)  # right stayed


def test_score_frame_high_on_m0r0():
    assert m0r0.score_frame(_frame()) >= 0.7


def test_find_mate_path_ends_with_compress():
    path = m0r0.find_mate_path(_frame())
    assert path is not None
    assert path[-1] in (1, 2, 4)
    assert len(path) <= 20
