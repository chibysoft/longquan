"""Rule representation: a conjunctive hypothesis for the target transition.

A Rule is a conjunction of Conditions. Its MDL complexity is the sum of its
conditions' complexities — shorter is preferred (Occam's razor). Each condition
is one interpretable predicate (≈ a primitive), so a rule ≈ a composition of
primitives — the same "原语 + 组合" idea, transposed from geometric transforms
to state predicates.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple

from .evidence import State


@dataclass(frozen=True)
class Condition:
    """feature OP value, e.g. armed_only_nonempty == True, or ui > 10."""

    feature: str
    op: str          # "==" | "!=" | ">" | "<" | ">=" | "<="
    value: Any

    def test(self, state: State) -> bool:
        v = state.get(self.feature)
        try:
            if self.op == "==":
                return v == self.value
            if self.op == "!=":
                return v != self.value
            if self.op == ">":
                return v > self.value
            if self.op == "<":
                return v < self.value
            if self.op == ">=":
                return v >= self.value
            if self.op == "<=":
                return v <= self.value
        except TypeError:
            return False
        raise ValueError(f"unknown op {self.op}")

    def complexity(self) -> float:
        # bool predicates are simplest; numeric comparisons carry a threshold.
        return 1.0 if isinstance(self.value, bool) else 2.0

    def describe(self) -> str:
        return f"{self.feature} {self.op} {self.value}"


@dataclass(frozen=True)
class Rule:
    conditions: Tuple[Condition, ...]

    def complexity(self) -> float:
        # +0.1 per condition so a 1-condition rule beats 2 conditions even if
        # thresholds differ; keeps "shortest" well-ordered.
        return sum(c.complexity() for c in self.conditions) + 0.1 * len(self.conditions)

    def predicts_flip(self, state: State) -> bool:
        return all(c.test(state) for c in self.conditions)

    def describe(self) -> str:
        if not self.conditions:
            return "TRUE (always flips)"
        return " AND ".join(c.describe() for c in self.conditions)
