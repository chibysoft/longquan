"""Stage 3: fixed synthetic gold set (inputs + outputs from known programs).

DO NOT regenerate ad-hoc during induction. Edit this module (or the JSON
fixture) deliberately when adding cases; then re-freeze outputs via
`python -m longquan.synth_gold --write`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

from longquan.program import Program

# ---------------------------------------------------------------------------
# Known programs + seed inputs (outputs derived, then frozen in JSON).
# ---------------------------------------------------------------------------

_GOLD_SPECS: List[Dict[str, Any]] = [
    {
        "id": "recolor_only",
        "program": [{"op": "recolor", "mapping": {1: 7}}],
        "inputs": [
            [[1, 0, 1], [0, 1, 0], [0, 0, 0]],
            [[1, 1, 0], [0, 0, 1], [0, 0, 0]],
        ],
    },
    {
        "id": "reflect_v",
        "program": [{"op": "reflect", "axis": "V", "coord": 2}],
        "inputs": [
            [
                [1, 1, 1, 0, 0],
                [0, 0, 1, 0, 0],
                [0, 0, 1, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
            ],
            [
                [2, 0, 0, 0, 0],
                [2, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
            ],
        ],
    },
    {
        "id": "translate_right",
        "program": [{"op": "translate", "dx": 1, "dy": 0}],
        "inputs": [
            [[3, 0, 0], [0, 0, 0], [0, 0, 0]],
            [[0, 4, 0], [4, 0, 0], [0, 0, 0]],
        ],
    },
    {
        "id": "copy_east",
        "program": [{"op": "copy", "offsets": [(2, 0)]}],
        "inputs": [
            [[5, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
            [[5, 5, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
        ],
    },
    {
        "id": "reflect_then_recolor",
        "program": [
            {"op": "reflect", "axis": "V", "coord": 2},
            {"op": "recolor", "mapping": {1: 7}},
        ],
        "inputs": [
            [
                [1, 1, 1, 0, 0],
                [0, 0, 1, 0, 0],
                [0, 0, 1, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
            ],
            [
                [1, 0, 0, 0, 0],
                [1, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
            ],
        ],
    },
    {
        "id": "translate_then_copy",
        "program": [
            {"op": "translate", "dx": 1, "dy": 0},
            {"op": "copy", "offsets": [(0, 2)]},
        ],
        "inputs": [
            [
                [6, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
            ],
            [
                [0, 0, 0, 0],
                [6, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
            ],
        ],
    },
]

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "synth_gold_v1.json"
)


def _build_case(spec: Dict[str, Any]) -> Dict[str, Any]:
    prog = Program.from_ops(spec["program"])
    examples = []
    for inp in spec["inputs"]:
        g = np.asarray(inp, dtype=int)
        out = prog.execute(g)
        examples.append({"input": g.tolist(), "output": out.tolist()})
    return {
        "id": spec["id"],
        "program": prog.to_json(),
        "complexity": prog.complexity(),
        "examples": examples,
    }


def build_gold() -> Dict[str, Any]:
    cases = [_build_case(s) for s in _GOLD_SPECS]
    return {"version": 1, "cases": cases}


def write_fixture(path: Path | None = None) -> Path:
    path = path or FIXTURE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    data = build_gold()
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _normalize(data: Dict[str, Any]) -> Dict[str, Any]:
    """JSON round-trip so int-keyed mappings match on-disk form."""
    return json.loads(json.dumps(data))


def load_gold(path: Path | None = None) -> Dict[str, Any]:
    path = path or FIXTURE_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def case_examples(case: Dict[str, Any]) -> List[Tuple[np.ndarray, np.ndarray]]:
    out = []
    for ex in case["examples"]:
        out.append(
            (np.asarray(ex["input"], dtype=int), np.asarray(ex["output"], dtype=int))
        )
    return out


def main(argv: List[str] | None = None) -> None:
    import argparse

    p = argparse.ArgumentParser(description="Freeze / verify synth gold fixture")
    p.add_argument("--write", action="store_true", help="rewrite fixture from specs")
    p.add_argument("--check", action="store_true", help="verify fixture matches specs")
    args = p.parse_args(argv)
    if args.write:
        path = write_fixture()
        print(f"wrote {path} cases={len(build_gold()['cases'])}")
        return
    if args.check:
        fresh = _normalize(build_gold())
        disk = load_gold()
        if fresh != disk:
            raise SystemExit("fixture DRIFT: re-run with --write after intentional edits")
        print(f"OK {FIXTURE_PATH} cases={len(disk['cases'])}")
        return
    p.print_help()


if __name__ == "__main__":
    main()
