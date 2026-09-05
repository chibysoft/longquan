"""Longquan: a closed-book agent that learns game rules from frames.

Pipeline: perceive -> search -> motion -> replay -> tabu.
Game rules are hypothesis-space modules (see hypotheses/), not hardcoded here.
"""
from .obs import Obs, Obj, Line
from .perceive import perceive
from .memory import Tabu, TabuRecord
from .loop import solve, solve_auto, SolveResult, ReplayResult

__all__ = [
    "Obs",
    "Obj",
    "Line",
    "perceive",
    "Tabu",
    "TabuRecord",
    "solve",
    "solve_auto",
    "SolveResult",
    "ReplayResult",
]
