"""ls20 induction: feed the engine REAL recording data (first real battle).

This is route 1 -> route 2 of the induction plan. The engine's reverse-validation
(tests/test_induction.py) used hand-written evidence; this tool replays a WIN
recording, extracts a structured State from every frame via
longquan/induction/ls20_extract.py, builds Transitions, and runs Inducer against
the REAL signal — under TWO targets:

  gate_u            : the completion proxy (DEGENERATE — flips only at level-up)
  legend_unlocked   : the TRUE unlock event (legend glyph color12 -> color9)

Measured 2026-09-11 on the lingjingsolo recording:
  - `gate_u` flips False->True only at the frame levels_completed increments.
    The engine cannot learn a meaningful rule from it (no distinguishing
    before-state), as documented in docs/induction-engine-real-evidence.md.
  - `legend_unlocked` flips False->True mid-level at the *unlock* event
    (ring crush), and this is the signal route 1 proved was missing. It is now
    a first-class feature (legend_locked) + target (legend_unlocked).

The remaining gap (route 2's next step) is positional: the crush rule is
"armed mover enters the armed-only cell", which needs a cursor/adjacency
feature the current schema does not yet expose. The engine correctly reports
"no consistent rule" — the diagnosis is now precise.

USAGE
  python tools/ls20_induct_l4.py --recording <path.jsonl>
  python tools/ls20_induct_l4.py            # default lingjingsolo WIN recording
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_REC = (
    r"D:\Projects\ARC-AGI-3-Agents\recordings"
    r"\ls20-9607627b.lingjingsolo.800.5f1bf1fd-a88e-4c5f-8c63-3c85bc6f5f97.recording.jsonl"
)

from longquan.induction import Inducer, Transition, make_transition
from longquan.induction.ls20_extract import extract_state


def load_recording(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            rows.append(json.loads(line)["data"])
    return rows


def build_transitions(rows: list[dict], target: str) -> list[Transition]:
    states = []
    for d in rows:
        try:
            states.append(extract_state(d["frame"]))
        except Exception:
            states.append(None)
    out = []
    for i in range(len(rows) - 1):
        before, after = states[i], states[i + 1]
        if before is None or after is None:
            continue
        if before.get(target) is None or after.get(target) is None:
            continue
        out.append(make_transition(
            before, str(rows[i + 1].get("action_input")), after, target=target,
        ))
    return out


def report_flips(rows: list[dict], target: str, label: str) -> None:
    """Print every falsy->truthy flip of `target` with its before-state."""
    states = [extract_state(d["frame"]) for d in rows]
    print(f"\n=== {label} ({target}) flips ===")
    n = 0
    for i in range(len(rows) - 1):
        b, a = states[i], states[i + 1]
        if b is None or a is None:
            continue
        if b.get(target) is None or a.get(target) is None:
            continue
        if not bool(b[target]) and bool(a[target]):
            n += 1
            print(f"idx={i+1} levels={rows[i+1].get('levels_completed')} "
                  f"action={rows[i+1].get('action_input')} "
                  f"armed_only={b['armed_only_nonempty']} legend_locked={b['legend_locked']} "
                  f"ui={b['ui']} total_c9={b['total_c9']} stamp_c9={b['stamp_c9']}")
    print(f"total {target} flips: {n}")


def run_induce(transitions: list[Transition], label: str) -> None:
    print(f"\n=== induction on {label} ({len(transitions)} transitions) ===")
    result = Inducer(transitions).induce()
    if result.consistent:
        print(f"最短一致规则: {result.rule.describe()}  (复杂度 {result.complexity:.2f})")
    else:
        print(f"未找到一致规则（尝试 {result.rule_count_tried} 条，一致 0 条）")
        print("—— 特征/规则空间有缺口（预期，见文件头）。")
    print(f"尝试规则 {result.rule_count_tried}，一致 {result.rule_count_consistent}。")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recording", default=DEFAULT_REC)
    args = ap.parse_args()

    rows = load_recording(args.recording)
    print(f"recording frames={len(rows)}")

    report_flips(rows, "gate_u", "completion proxy")
    report_flips(rows, "legend_unlocked", "unlock event")

    run_induce(build_transitions(rows, "gate_u"), "gate_u (completion)")
    run_induce(build_transitions(rows, "legend_unlocked"), "legend_unlocked (unlock)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
