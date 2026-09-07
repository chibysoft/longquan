"""1a family router: AR25-like / ft09 / ls20 frames pick the right family."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from longquan.selector import route, select_family, score_families

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_frame(name: str):
    path = os.path.join(FIX, name)
    data = json.loads(open(path, encoding="utf-8").read())
    if isinstance(data, dict) and "frame" in data:
        return data["frame"]
    return data


def _ar25_like_frame():
    f = np.full((64, 64), 9, dtype=np.int8)

    def put(cx, cy, color):
        for dy in range(3):
            for dx in range(3):
                f[cy * 3 + dy, cx * 3 + dx] = color

    for gy in range(21):
        put(10, gy, 10)
    for dx, dy in [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)]:
        put(6 + dx, 5 + dy, 5)
    for cell in [(19, 15), (17, 17), (17, 16), (17, 15), (18, 15)]:
        put(cell[0], cell[1], 11)
    return f


def test_ar25_routes_to_reflect():
    assert select_family(_ar25_like_frame()) == "reflect"
    assert route(_ar25_like_frame())["family"] == "reflect"


def test_ft09_routes_to_toggle():
    frame = _load_frame("ft09_frame_initial.json")
    fam = select_family(frame)
    scores = {name: score for score, name in score_families(frame)}
    assert fam == "toggle", scores
    assert scores["toggle"] > scores["reflect"]
    assert scores["toggle"] > scores["move"]


def test_ls20_routes_to_move():
    frame = _load_frame("ls20_l1_frame_live.json")
    fam = select_family(frame)
    scores = {name: score for score, name in score_families(frame)}
    assert fam == "move", scores
    assert scores["move"] > scores["toggle"]
    assert scores["move"] > scores["reflect"]


def test_m0r0_routes_to_mate():
    frame = _load_frame("m0r0_l1_frame_live.json")
    fam = select_family(frame)
    scores = {name: score for score, name in score_families(frame)}
    assert fam == "mate", scores
    assert scores["mate"] > scores["move"]


def test_solve_auto_rejects_non_reflect_frame():
    from longquan import perceive, solve_auto, ReplayResult

    frame = _load_frame("ls20_l1_frame_live.json")
    obs = perceive(_ar25_like_frame(), steps_left=64)
    result = solve_auto(obs, replay=lambda a: ReplayResult(True, 1), frame=frame)
    assert result.reason == "wrong_family:move"
