"""Extract L2 trajectory from recording via frame diffs (action ids often 0)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from longquan.interactive import ls20


def mover(frame):
    return ls20.locate_mover(frame)


def marker(frame):
    g = ls20._plane(frame)
    return ls20._bbox(g, (0, 1))


def main():
    path = Path(r"D:/Projects/ARC-AGI-3-Agents/recordings") / (
        "ls20-9607627b.lingjingsolo.800.5f1bf1fd-a88e-4c5f-8c63-3c85bc6f5f97.recording.jsonl"
    )
    prev_lv = None
    prev_m = None
    in_l2 = False
    n = 0
    for line in path.open(encoding="utf-8"):
        n += 1
        data = json.loads(line)["data"]
        frame = data["frame"]
        lv = data.get("levels_completed", data.get("level", None))
        # some recordings nest differently
        if lv is None:
            lv = data.get("state", {}).get("levels_completed") if isinstance(data.get("state"), dict) else None
        m = mover(frame)
        mk = marker(frame)
        st = ls20.stamp_block(frame)
        layers = np.asarray(frame).shape
        if prev_lv is not None and lv is not None and lv != prev_lv:
            print(f"--- LEVEL {prev_lv}->{lv} at line {n} mover={m} marker={mk} stamp={st} layers={layers}")
            in_l2 = lv == 1
        if in_l2 and lv == 1:
            if m != prev_m or (isinstance(layers, tuple) and layers[0] > 1):
                print(f"L2 i={n} mover={m} marker={mk} stamp={st} layers={layers} keys={list(data)[:8]}")
        if lv is not None:
            prev_lv = lv
        prev_m = m
        if lv is not None and lv >= 2:
            print(f"reached lv2 at {n}")
            break
        if n > 800:
            print("stop 800")
            break


if __name__ == "__main__":
    main()
