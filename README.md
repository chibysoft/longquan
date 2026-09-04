# Longquan (龙泉)

A closed-book agent that learns game rules from frames.

Given a game it has never seen, Longquan reduces the rendered frame to objects,
searches the *configuration space* (where objects should end up), turns configs
into actions, and lets the engine replay be the source of truth. It does not
read engine source, does not import canned answers, does not reference level ids.

## Pipeline

```
frame -> perceive -> Obs -> search (config space) -> motion (config -> actions)
                            ^                              |
                            |                              v
                        tabu (memory) <-- replay (engine truth)
```

## Architecture: generic engine + swappable hypotheses

The key design choice: the **search / motion / loop layers are game-agnostic**.
All game knowledge lives in a *hypothesis module* under `hypotheses/`, exposed
as two callbacks:

- `cover(obj_cells, pos, axes) -> set of covered cells`
- `backproject(obj_cells, targets, axes, w, h) -> candidate positions`

To port Longquan to a new game, write a new hypothesis module with the same
interface. The generic layers never change.

| Module | Role | Game-specific? |
|--------|------|----------------|
| `obs.py` | unified observation (objects, targets, lines) | no |
| `perceive.py` | frame -> Obs (closed-book) | color semantics only |
| `search.py` | config-space search + target decomposition | no |
| `motion.py` | config -> action sequence | no |
| `memory.py` | tabu (failed-pattern memory, JSONL) | no |
| `loop.py` | orchestration, the only entry point | no |
| `hypotheses/mirror.py` | mirror-reflection rule (AR25) | yes |

## Run the offline test

```bash
python -c "from tests.test_loop import *; test_perceive_recognizes_objects(); test_search_finds_known_optimum(); test_loop_replays_ok(); test_loop_tabu_on_replay_failure()"
```

## License

MIT-0. Copyright (c) 2026 Chiby (赤壁).
