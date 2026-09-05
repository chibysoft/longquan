"""Longquan: a closed-book agent that learns game rules from frames.

Pipeline: perceive (frame -> Obs) -> search (config space) -> motion
(config -> actions) -> replay (engine truth) -> tabu (failed-pattern memory).

Game rules are hypothesis-space modules (see hypotheses/), not hardcoded here.
"""
from .obs import Obs, Obj, Line
from .perceive import perceive
from .memory import Tabu, TabuRecord
from .loop import solve, SolveResult, ReplayResult

__all__ = [
    "Obs", "Obj", "Line", "perceive",
    "Tabu", "TabuRecord",
    "solve", "SolveResult", "ReplayResult",
]
