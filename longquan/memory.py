"""Longquan tabu memory: persisted failed-pattern record, hypothesis-space keyed.

JSONL storage; load on startup; malformed lines skipped. Keyed by hypothesis
space type so cross-game experience can be matched later. No level-id constants.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional


@dataclass
class TabuRecord:
    hypothesis_space_type: str
    failed_pattern: str
    feedback: str = ""


class Tabu:
    def __init__(self, path: Optional[str] = None):
        if path is None:
            path = os.environ.get("LONGQUAN_TABU_PATH", "tabu.jsonl")
        self.path = path
        self._records: Dict[str, TabuRecord] = {}

    def load(self) -> "Tabu":
        self._records.clear()
        if not os.path.exists(self.path):
            return self
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    self._records[self._key(d["hypothesis_space_type"],
                                            d["failed_pattern"])] = TabuRecord(
                        d["hypothesis_space_type"], d["failed_pattern"],
                        d.get("feedback", ""))
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
        return self

    def save(self) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for r in self._records.values():
                f.write(json.dumps(asdict(r), ensure_ascii=True) + "\n")
        os.replace(tmp, self.path)

    @staticmethod
    def _key(hs: str, pattern: str) -> str:
        return f"{hs}|{pattern}"

    def add(self, hs: str, pattern: str, feedback: str = "") -> bool:
        k = self._key(hs, pattern)
        if k in self._records:
            return False
        self._records[k] = TabuRecord(hs, pattern, feedback)
        return True

    def blocked(self, hs: str, pattern: str) -> bool:
        return self._key(hs, pattern) in self._records

    def __len__(self) -> int:
        return len(self._records)


__all__ = ["Tabu", "TabuRecord"]
