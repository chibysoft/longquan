"""Evidence: structured observations extracted from the rendered plane.

A probe run produces a sequence of frames. Each frame is encoded into a State
(dict of observable features -> value). A Transition is (before, action, after).

The point: probe output must be *data* (a Transition), not a debug string.
That is the divide between "打地鼠" and "会学".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

State = Dict[str, Any]

FEATURES: Dict[str, str] = {
    "armed_only_nonempty": "bool",
    "unlocked_stamp": "bool",
    "has_plus": "bool",
    "legend_locked": "bool",
    "ui": "int",
    "total_c9": "int",
    "stamp_c9": "int",
}

TARGET = "gate_u"


@dataclass
class Transition:
    before: State
    action: str
    after: State
    target: str = TARGET

    @property
    def target_flipped(self) -> bool:
        return bool(self.after.get(self.target)) and not bool(self.before.get(self.target))

    @property
    def target_unchanged(self) -> bool:
        return not self.target_flipped


def make_transition(before, action, after, target=TARGET):
    return Transition(before=before, action=action, after=after, target=target)
