"""Longquan learner loop: perceive -> search -> motion -> replay -> tabu.

Two entry points:
- solve(): explicit primitive (cover/backproject passed by caller)
- solve_auto(): select the best primitive from the registry by score, then solve

The closed-book loop: reduce a frame to Obs, pick a primitive, search configs,
turn configs into actions, replay, record failures into tabu, try the next
config. This is the ONLY entry point a caller needs.
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
    config: Optional[Dict] = None
    configs_tried: int = 0
    replay_ok: bool = False
    reason: str = ""
    hypothesis_space_type: str = HYPOTHESIS_SPACE_TYPE
    primitive: str = ""


def solve(
    obs: Obs,
    lines: List[Tuple[str, int]],
    cover,
    backproject,
    replay: Callable[[List[int]], ReplayResult],
    *,
    line_candidates=None,
    tabu: Optional[Tabu] = None,
    max_configs: int = 8,
    primitive: str = "",
) -> SolveResult:
    """Solve with an explicit primitive (cover/backproject supplied by caller)."""
    tabu = tabu if tabu is not None else Tabu()
    configs = solve_configs(obs, lines, cover, backproject,
                            line_candidates=line_candidates,
                            max_solutions=max_configs)

    if not configs:
        return SolveResult(reason="no_cover", configs_tried=0, primitive=primitive)

    tried = 0
    for cfg in configs:
        key = repr(sorted((k, v) for k, v in cfg.items() if k != "_lines"))
        tried += 1
        if tabu.blocked(HYPOTHESIS_SPACE_TYPE, key):
            continue
        actions = plan(obs, cfg)
        result = replay(actions)
        if result.ok:
            return SolveResult(
                actions=actions, config=cfg, configs_tried=tried,
                replay_ok=True, reason="ok", primitive=primitive,
            )
        tabu.add(HYPOTHESIS_SPACE_TYPE, key, result.feedback or "replay failed")

    tabu.save()
    return SolveResult(configs_tried=tried, replay_ok=False,
                       reason="all_replay_failed", primitive=primitive)


def solve_auto(
    obs: Obs,
    replay: Callable[[List[int]], ReplayResult],
    *,
    tabu: Optional[Tabu] = None,
    max_configs: int = 8,
    max_primitives: int = 3,
    frame=None,
) -> SolveResult:
    """Select the best primitive from the registry by score, then solve.

    Workflow (per primitives.md selector):
      1. score every primitive in the registry against obs
      2. sort by score desc
      3. try each primitive in order (reflect first for line games)
      4. first primitive whose solve() replays ok wins

    For primitives with a line_candidates function (movable lines), pass it
    through so the search can iterate line positions.

    If ``frame`` is provided, ``selector.select_family`` must return
    ``\"reflect\"`` (geometric cover/backproject path). Other families
    (toggle/move) are interactive pipelines — callers should dispatch via
    ``selector.route(frame)`` instead of this function.
    """
    if frame is not None:
        from .selector import select_family

        family = select_family(frame)
        if family != "reflect":
            return SolveResult(
                reason=f"wrong_family:{family}",
                primitive="",
            )

    from .hypotheses.registry import PRIMITIVES

    scored = []
    for name, mod in PRIMITIVES.items():
        try:
            s = mod.score(obs)
        except Exception:
            s = 0.0
        scored.append((s, name, mod))
    scored.sort(key=lambda t: -t[0])

    tried_primitives = 0
    for s, name, mod in scored:
        if tried_primitives >= max_primitives:
            break
        tried_primitives += 1

        # Only primitives with a usable cover/backproject are tried.
        if not hasattr(mod, "cover") or not hasattr(mod, "backproject"):
            continue
        # Skip primitives whose cover is a NotImplementedError stub.
        try:
            mod.cover([(0, 0)], (0, 0), [("V", 0)])
        except NotImplementedError:
            continue
        except Exception:
            pass

        lines = [(ln.kind, ln.coord) for ln in obs.lines]
        if not lines:
            continue
        lc = getattr(mod, "line_candidates", None)
        result = solve(
            obs, lines, mod.cover, mod.backproject,
            replay=replay, tabu=tabu, max_configs=max_configs,
            line_candidates=lc, primitive=name,
        )
        if result.replay_ok:
            return result

    return SolveResult(reason="no_primitive", primitive="")


__all__ = ["solve", "solve_auto", "SolveResult", "ReplayResult", "HYPOTHESIS_SPACE_TYPE"]
