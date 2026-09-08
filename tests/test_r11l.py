"""Unit tests for r11l perception (fixture-backed, offline)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from longquan.interactive import r11l

FIX = Path(__file__).resolve().parent / "fixtures" / "r11l_l1_enter.json"


def _frame():
    return json.loads(FIX.read_text(encoding="utf-8"))["frame"]


def test_l1_ship_waypoints_goal():
    frame = _frame()
    assert r11l.ship_center(frame) == (17, 47)
    wps = r11l.waypoints(frame)
    assert len(wps) == 2
    sel = [w for w in wps if w["selected"]]
    idle = [w for w in wps if not w["selected"]]
    assert len(sel) == 1 and sel[0]["c"] == (7, 36)
    assert len(idle) == 1 and idle[0]["c"] == (27, 59)
    gs = r11l.goals(frame)
    assert len(gs) == 1
    assert gs[0]["c"] == (39, 21)


def test_l2_ships_chrome_goals_assign():
    path = Path(__file__).resolve().parent / "fixtures" / "r11l_l2_enter.json"
    frame = json.loads(path.read_text(encoding="utf-8"))["frame"]
    sh = r11l.ships(frame)
    assert len(sh) == 2
    chromes = {s["chrome"] for s in sh}
    assert chromes == {12, 15}
    gs = r11l.goals(frame)
    assert {g["chrome"] for g in gs} == {12, 15}
    asg = r11l.assign_waypoints(frame)
    assert asg is not None
    assert len(asg) == 2
    # centroids roughly match ships
    for s, wps in asg:
        cx = sum(w["c"][0] for w in wps) / len(wps)
        cy = sum(w["c"][1] for w in wps) / len(wps)
        assert abs(cx - s["c"][0]) + abs(cy - s["c"][1]) < 3


def test_l1_plan_has_select_and_double_moves():
    clicks = r11l.plan_l1_clicks(_frame())
    assert len(clicks) >= 5
    assert (27, 59) in clicks


def test_score_positive():
    assert r11l.score_frame(_frame()) >= 0.5
