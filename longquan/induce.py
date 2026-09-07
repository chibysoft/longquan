"""Stage 3: shortest-first program induction over synthetic Grid->Grid examples.

Enumerate a bounded geometric program space ordered by Program.complexity(),
keep the first program that reproduces every (input, output) pair.
"""
from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np

from longquan.program import Op, Program, complexity

Example = Tuple[np.ndarray, np.ndarray]


def fits(program: Program, examples: Sequence[Example]) -> bool:
    for inp, out in examples:
        got = program.execute(inp)
        if got.shape != out.shape or not np.array_equal(got, out):
            return False
    return True


def _colors_in_examples(examples: Sequence[Example]) -> Set[int]:
    colors: Set[int] = set()
    for inp, out in examples:
        colors.update(int(c) for c in inp.ravel() if int(c) != 0)
        colors.update(int(c) for c in out.ravel() if int(c) != 0)
    return colors


def _grid_size(examples: Sequence[Example]) -> Tuple[int, int]:
    h, w = examples[0][0].shape
    return h, w


def _single_ops(examples: Sequence[Example]) -> List[Op]:
    """Bounded single-op pool derived only from example geometry/colors."""
    h, w = _grid_size(examples)
    colors = sorted(_colors_in_examples(examples))
    ops: List[Op] = []

    # reflect: axis x small coords near the board
    coords = sorted(set(range(0, max(w, h))) | {-1, max(w, h)})
    for axis in ("V", "H"):
        for coord in coords:
            ops.append({"op": "reflect", "axis": axis, "coord": int(coord)})

    # recolor: single-entry maps between observed colors + a few destinations
    dests = sorted(set(colors) | {7, 8, 9})
    for src in colors:
        for dst in dests:
            if src == dst:
                continue
            ops.append({"op": "recolor", "mapping": {int(src): int(dst)}})

    # translate: small Moore neighborhood excluding (0,0)
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            if dx == 0 and dy == 0:
                continue
            ops.append({"op": "translate", "dx": int(dx), "dy": int(dy)})

    # copy: a few cardinal / diagonal offsets
    for dx, dy in ((1, 0), (2, 0), (0, 1), (0, 2), (1, 1), (-1, 0), (0, -1), (2, 1)):
        ops.append({"op": "copy", "offsets": [(int(dx), int(dy))]})

    return ops


def candidate_programs(
    examples: Sequence[Example],
    *,
    max_ops: int = 2,
) -> List[Program]:
    """All programs with 1..max_ops steps from the bounded pool, sorted by MDL."""
    singles = _single_ops(examples)
    progs: List[Program] = [Program.from_ops([op]) for op in singles]
    if max_ops >= 2:
        for a in singles:
            for b in singles:
                progs.append(Program.from_ops([a, b]))
    # Stable tie-break: complexity, then JSON text
    progs.sort(key=lambda p: (p.complexity(), json_key(p)))
    return progs


def json_key(program: Program) -> str:
    import json

    return json.dumps(program.to_json(), sort_keys=True)


def induce(
    examples: Sequence[Example],
    *,
    max_ops: int = 2,
    max_complexity: Optional[int] = None,
) -> Optional[Program]:
    """Return the lowest-complexity program that fits all examples, or None."""
    if not examples:
        raise ValueError("induce: empty examples")
    for prog in candidate_programs(examples, max_ops=max_ops):
        c = prog.complexity()
        if max_complexity is not None and c > max_complexity:
            break
        if fits(prog, examples):
            return prog
    return None


__all__ = ["induce", "fits", "candidate_programs", "Example"]
