"""Interactive primitives (E family): state-machine interface.

Distinct from the geometric primitives in `longquan/hypotheses/` (which expose
cover/backproject for config-space search). Interactive primitives expose the
state-machine contract described in docs/primitive-interface-interactive.md:

    score(obs) -> float
    init(...)  -> WorldState
    actions(state) -> [Action]
    step(state, action) -> WorldState
    done(state) -> bool

The search here is STATE-SPACE search (BFS / A*), not config-space search.
"""
