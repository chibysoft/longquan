"""State-space search for interactive primitives (BFS, minimal steps).

The geometric search in longquan/search.py searches CONFIG space (cover the
targets); interactive rules are state machines, so this searches STATE space:
nodes = WorldState, edges = actions, start = init, goal = done.

BFS gives the minimal-step path, which matters because RHAE scores (human/AI
steps)² — every wasted step is squared into the penalty.

The search is primitive-agnostic: it takes `actions_fn`, `step_fn`, `done_fn`
callbacks. A real game composes primitives (e.g. ls20 = move + match) into a
single composite step, and passes that composite's callbacks here.
"""
from __future__ import annotations

from collections import deque
from typing import Callable, List, Optional, Tuple

from .state import Action, WorldState

ActionsFn = Callable[[WorldState], List[Action]]
StepFn = Callable[[WorldState, Action], WorldState]
DoneFn = Callable[[WorldState], bool]


def bfs(
    init: WorldState,
    actions_fn: ActionsFn,
    step_fn: StepFn,
    done_fn: DoneFn,
    *,
    max_steps: Optional[int] = None,
) -> Tuple[bool, List[Action]]:
    """Minimal-step path from `init` to a state where `done_fn` is True.

    Returns (found, path). `path` is the list of actions; empty when init is
    already done. `max_steps` caps search depth (defaults to the state's step
    budget, else 64). BFS over a uniform-cost graph returns the shortest path.
    """
    limit = max_steps if max_steps is not None else (init.steps_limit or 64)
    if done_fn(init):
        return True, []

    queue = deque([(init, [])])
    visited = {init}
    while queue:
        state, path = queue.popleft()
        if len(path) >= limit:
            continue
        for action in actions_fn(state):
            nxt = step_fn(state, action)
            if nxt in visited:
                continue
            visited.add(nxt)
            if done_fn(nxt):
                return True, path + [action]
            queue.append((nxt, path + [action]))
    return False, []


__all__ = ["bfs"]
