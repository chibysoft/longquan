"""Design-time: dump ls20 recording frames at each level boundary."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

REC = Path(
    r"D:\Projects\ARC-AGI-3-Agents\recordings"
    r"\ls20-9607627b.lingjingsolo.800.5f1bf1fd-a88e-4c5f-8c63-3c85bc6f5f97.recording.jsonl"
)


def plane(frame):
    a = np.asarray(frame, dtype=np.int8)
    return a[0] if a.ndim == 3 else a


def bbox(g, colors):
    ys, xs = np.where(np.isin(g, colors))
    if len(xs) == 0:
        return None
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


prev = None
with open(REC, encoding="utf-8") as fh:
    for i, line in enumerate(fh):
        o = json.loads(line)["data"]
        lv = o["levels_completed"]
        if prev is None or lv != prev:
            g = plane(o["frame"])
            print(
                f"i={i} lv={lv} c12={bbox(g, [12])} c01={bbox(g, [0, 1])} "
                f"n01={int(np.count_nonzero(np.isin(g, [0, 1])))} "
                f"n5={int(np.count_nonzero(g == 5))} n9={int(np.count_nonzero(g == 9))}"
            )
            prev = lv
