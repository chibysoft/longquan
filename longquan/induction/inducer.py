"""MDL inducer: enumerate rules shortest-first, eliminate with evidence.

The inducer searches the rule space in order of complexity (Occam's razor),
tests each rule against every transition, and returns the shortest rule that
is consistent with all evidence. It also produces an auditable trail — the
proof that "学习" (convergence) happened, not "猜测" (guessing).

A rule is *refuted* by a transition if:
  - the rule predicts the target flips, but it did not (false positive), or
  - the rule predicts it does not flip, but it did (false negative).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Iterator, List, Sequence

from .evidence import FEATURES, TARGET, Transition
from .rule import Condition, Rule


@dataclass
class AuditEntry:
    rule_desc: str
    complexity: float
    verdict: str                 # "consistent" | "refuted"
    refuted_by: int = -1         # index of the refuting transition, if refuted
    detail: str = ""


@dataclass
class InduceResult:
    rule: Rule
    complexity: float
    consistent: bool
    trail: List[AuditEntry] = field(default_factory=list)
    rule_count_tried: int = 0
    rule_count_consistent: int = 0

    @property
    def none_found(self) -> bool:
        return self.rule is None or not self.consistent


def _int_domain(transitions: Sequence[Transition], feature: str) -> List[int]:
    """Distinct int values observed for a feature, for threshold generation."""
    vals = set()
    for t in transitions:
        for s in (t.before, t.after):
            v = s.get(feature)
            if isinstance(v, (int, float)):
                vals.add(int(v))
    return sorted(vals)


def _condition_pool(transitions: Sequence[Transition]) -> List[Condition]:
    """All candidate single conditions, grouped by feature kind."""
    pool: List[Condition] = []
    for feature, kind in FEATURES.items():
        if kind == "bool":
            pool.append(Condition(feature, "==", True))
            pool.append(Condition(feature, "==", False))
        elif kind == "int":
            for v in _int_domain(transitions, feature):
                pool.append(Condition(feature, ">", v))
                pool.append(Condition(feature, "<", v))
    return pool


def _rules_by_complexity(
    transitions: Sequence[Transition], max_conditions: int = 3
) -> Iterator[Rule]:
    """Yield rules in non-decreasing MDL complexity order."""
    pool = _condition_pool(transitions)
    # TRUE rule (always flips) is the absolute shortest non-empty hypothesis.
    yield Rule(conditions=())

    for k in range(1, max_conditions + 1):
        combos = []
        for combo in itertools.combinations(pool, k):
            # drop redundant combos: same feature twice is meaningless-ish but
            # kept simple — dedupe by sorted condition descriptors.
            rule = Rule(conditions=tuple(sorted(combo, key=lambda c: c.describe())))
            combos.append(rule)
        combos.sort(key=lambda r: r.complexity())
        for rule in combos:
            yield rule


def _refutation(rule: Rule, t: Transition) -> bool:
    pred = rule.predicts_flip(t.before)
    return pred != t.target_flipped


def _refute_detail(rule: Rule, t: Transition, idx: int) -> str:
    pred = rule.predicts_flip(t.before)
    actual = t.target_flipped
    if pred and not actual:
        return (
            f"预测 flip，实际未 flip（false positive）@evidence[{idx}] "
            f"action={t.action} before={t.before} after_target={t.after.get(t.target)}"
        )
    return (
        f"预测不 flip，实际 flip（false negative）@evidence[{idx}] "
        f"action={t.action} before={t.before} after_target={t.after.get(t.target)}"
    )


class Inducer:
    def __init__(self, transitions: Sequence[Transition], *, max_conditions: int = 3):
        if not transitions:
            raise ValueError("need at least one transition")
        self.transitions = list(transitions)
        self.max_conditions = max_conditions

    def induce(self) -> InduceResult:
        trail: List[AuditEntry] = []
        tried = 0
        n_consistent = 0
        best: Rule = None
        best_complexity = float("inf")

        for rule in _rules_by_complexity(self.transitions, self.max_conditions):
            tried += 1
            refuted_by = -1
            for i, t in enumerate(self.transitions):
                if _refutation(rule, t):
                    refuted_by = i
                    break
            if refuted_by >= 0:
                trail.append(AuditEntry(
                    rule_desc=rule.describe(),
                    complexity=rule.complexity(),
                    verdict="refuted",
                    refuted_by=refuted_by,
                    detail=_refute_detail(rule, self.transitions[refuted_by], refuted_by),
                ))
            else:
                n_consistent += 1
                trail.append(AuditEntry(
                    rule_desc=rule.describe(),
                    complexity=rule.complexity(),
                    verdict="consistent",
                ))
                # first consistent rule encountered = shortest (enumerator is ordered)
                if rule.complexity() < best_complexity:
                    best = rule
                    best_complexity = rule.complexity()
                break  # shortest-first: stop at the first consistent rule

        return InduceResult(
            rule=best,
            complexity=best_complexity if best is not None else float("inf"),
            consistent=best is not None,
            trail=trail,
            rule_count_tried=tried,
            rule_count_consistent=n_consistent,
        )


__all__ = ["Inducer", "InduceResult", "AuditEntry"]
