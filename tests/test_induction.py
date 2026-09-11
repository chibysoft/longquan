"""Reverse-validation of the induction engine against a known rule.

The L3 "通用解锁规则" (armed-only cell exists -> gate can unlock) is a rule we
already reverse-engineered by hand. If the engine can re-derive it from
structured evidence — while ignoring decoy features — the abstraction is
sufficient to attack L4 (where the rule is still unknown). If it can't, the gap
is exactly why L4 is stuck.

Run:  python -m pytest tests/test_induction.py -v
      or python tests/test_induction.py  (prints the auditable trail)
"""
from __future__ import annotations

from longquan.induction import Inducer, Transition, make_transition


def _state(armed: bool, stamp: bool, plus: bool, ui: int, gate_u: bool) -> dict:
    return {
        "armed_only_nonempty": armed,
        "unlocked_stamp": stamp,
        "has_plus": plus,
        "ui": ui,
        "gate_u": gate_u,
    }


def build_l3_evidence() -> list[Transition]:
    """L3 observations: gate flips iff armed-only cells exist (decoy features vary)."""
    ts = []
    # Positive: armed-only exists -> gate flips (decoy features vary, don't matter)
    for stamp, plus, ui in [(False, False, 40), (True, False, 52), (False, True, 38),
                            (True, True, 60), (False, False, 44)]:
        ts.append(make_transition(
            _state(True, stamp, plus, ui, gate_u=False),
            "WALK",
            _state(True, stamp, plus, ui, gate_u=True),
        ))
    # Negative: no armed-only -> gate stays shut (decoy features vary)
    for stamp, plus, ui in [(False, False, 41), (True, False, 55), (False, True, 37),
                            (True, True, 61), (False, False, 46)]:
        ts.append(make_transition(
            _state(False, stamp, plus, ui, gate_u=False),
            "WALK",
            _state(False, stamp, plus, ui, gate_u=False),
        ))
    return ts


def main() -> int:
    ts = build_l3_evidence()
    inducer = Inducer(ts)
    result = inducer.induce()

    print(f"证据条数: {len(ts)}")
    print(f"尝试规则数: {result.rule_count_tried}  (一致: {result.rule_count_consistent})")
    print("-" * 72)
    if result.consistent:
        print(f"归纳出的最短一致规则:  {result.rule.describe()}  (复杂度 {result.complexity:.2f})")
    else:
        print("未找到一致规则 —— 特征/规则空间有缺口")
    print("-" * 72)
    print("可审计轨迹（按枚举顺序，MDL 最短优先）:")
    for e in result.trail:
        mark = "✓" if e.verdict == "consistent" else "✗"
        print(f"  {mark} [{e.complexity:>4.1f}] {e.rule_desc}")
        if e.verdict == "refuted":
            print(f"        否证: {e.detail}")
    print("-" * 72)

    # Assertion: engine must re-derive the L3 rule (armed-only nonempty -> flip).
    expected = "armed_only_nonempty == True"
    ok = result.consistent and result.rule.describe() == expected
    print(f"反向验证: {'PASS' if ok else 'FAIL'}  (期望: {expected})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())


def test_induces_l3_unlock_rule():
    """The engine re-derives the L3 rule from evidence, ignoring decoys."""
    ts = build_l3_evidence()
    result = Inducer(ts).induce()
    assert result.consistent, "induction found no consistent rule"
    assert result.rule.describe() == "armed_only_nonempty == True", \
        f"got {result.rule.describe()!r}"
    # The shortest rule should be found before considering multi-condition rules.
    assert result.rule.complexity() < 2.0


def test_true_rule_is_shortest_but_always_tried_first():
    """The empty TRUE rule is enumerated but refuted by a negative example."""
    ts = build_l3_evidence()
    result = Inducer(ts).induce()
    first = result.trail[0]
    assert first.rule_desc == "TRUE (always flips)"
    assert first.verdict == "refuted"
