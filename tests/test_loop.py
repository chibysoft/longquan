"""Longquan loop test: perceive -> search -> motion -> (fake) replay, offline."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from longquan import perceive, solve, Tabu, ReplayResult
from longquan.hypotheses import mirror
from longquan.search import solve_configs


def _build_l1_frame():
    f = np.full((64, 64), 9, dtype=np.int8)

    def put(cx, cy, color):
        for dy in range(3):
            for dx in range(3):
                f[cy * 3 + dy, cx * 3 + dx] = color

    for gy in range(21):
        put(10, gy, 10)  # vertical mirror line x=10
    for (dx, dy) in [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)]:
        put(6 + dx, 5 + dy, 5)  # L-shaped piece
    for cell in [(19, 15), (17, 17), (17, 16), (17, 15), (18, 15)]:
        put(cell[0], cell[1], 11)  # targets
    return f


def test_perceive_recognizes_objects():
    obs = perceive(_build_l1_frame(), steps_left=64)
    assert len(obs.targets) == 5
    assert [(ln.kind, ln.coord) for ln in obs.lines] == [("V", 10)]
    assert len(obs.objects) == 1
    assert obs.objects[0].color == 5
    assert obs.objects[0].bbox[:2] == (6, 5)


def test_search_finds_known_optimum():
    obs = perceive(_build_l1_frame(), steps_left=64)
    lines = [(ln.kind, ln.coord) for ln in obs.lines]
    configs = solve_configs(obs, lines, mirror.cover, mirror.backproject)
    assert configs, "no config found"
    assert configs[0]["obj_0"] == (1, 15)


def test_loop_replays_ok():
    obs = perceive(_build_l1_frame(), steps_left=64)
    lines = [(ln.kind, ln.coord) for ln in obs.lines]
    tabu = Tabu("/tmp/longquan_test_tabu.jsonl")
    result = solve(obs, lines, mirror.cover, mirror.backproject,
                   replay=lambda a: ReplayResult(True, 1), tabu=tabu)
    assert result.replay_ok
    assert result.reason == "ok"
    assert result.config["obj_0"] == (1, 15)


def test_loop_tabu_on_replay_failure():
    obs = perceive(_build_l1_frame(), steps_left=64)
    lines = [(ln.kind, ln.coord) for ln in obs.lines]
    tabu = Tabu("/tmp/longquan_test_tabu2.jsonl")
    result = solve(obs, lines, mirror.cover, mirror.backproject,
                   replay=lambda a: ReplayResult(False, 0, "hit wall"), tabu=tabu)
    assert not result.replay_ok
    assert result.reason == "all_replay_failed"
    assert len(tabu) >= 1
