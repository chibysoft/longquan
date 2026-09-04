"""Longquan learner loop: orchestrate perceive -> search -> motion -> replay.

The closed-book loop: reduce a frame to Obs, search configs, turn configs into
actions, replay, record failures into tabu, try the next config.

This is the ONLY entry point a caller needs. It knows nothing about any game's
rule; the rule is the `cover`/`backproject` pair injected by the caller (from
hypotheses/mirror.py for the first game).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .memory import Tabu
from .motion import plan
from .obs import Obs
from .search import solve_configs

HYPOTHESIS_SPACE_TYPE = "mirror_reflection"


@dataclass
class ReplayResult:
    ok: bool
    levels_completed: int
    feedback: str = ""


@dataclass
class SolveResult:
    actions: List[int] = field(default_factory=list)
    config: Optional[Dict[str, Tuple[int, int]]] = None
    configs_tried: int = 0
    replay_ok: bool = False
    reason: str = ""
    hypothesis_space_type: str = HYPOTHESIS_SPACE_TYPE


def solve(
    obs: Obs,
    axes: List[int],
    cover,
    backproject,
    replay: Callable[[List[int]], ReplayResult],
    *,
    tabu: Optional[Tabu] = None,
    max_configs: int = 8,
) -> SolveResult:
    tabu = tabu if tabu is not None else Tabu()
    configs = solve_configs(obs, axes, cover, backproject, max_solutions=max_configs)

    if not configs:
        return SolveResult(reason="no_cover", configs_tried=0)

    tried = 0
    for cfg in configs:
        key = repr(sorted(cfg.items()))
        tried += 1
        if tabu.blocked(HYPOTHESIS_SPACE_TYPE, key):
            continue
        actions = plan(obs, cfg)
        result = replay(actions)
        if result.ok:
            return SolveResult(
                actions=actions, config=cfg, configs_tried=tried,
                replay_ok=True, reason="ok",
            )
        tabu.add(HYPOTHESIS_SPACE_TYPE, key, result.feedback or "replay failed")

    tabu.save()
    return SolveResult(configs_tried=tried, replay_ok=False,
                       reason="all_replay_failed")


__all__ = ["solve", "SolveResult", "ReplayResult", "HYPOTHESIS_SPACE_TYPE"]
