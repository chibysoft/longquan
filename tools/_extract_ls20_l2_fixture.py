"""Save L2 start frame from recording (design-time fixture) and probe init."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20, match

REC = Path(
    r"D:\Projects\ARC-AGI-3-Agents\recordings"
    r"\ls20-9607627b.lingjingsolo.800.5f1bf1fd-a88e-4c5f-8c63-3c85bc6f5f97.recording.jsonl"
)
OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "ls20_l2_frame_from_rec.json"


def plane(frame):
    a = np.asarray(frame, dtype=np.int8)
    return a[0] if a.ndim == 3 else a


def main():
    prev = -1
    rows = []
    with open(REC, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            o = json.loads(line)["data"]
            rows.append(o)
    # first frame of each new level = first row where lv == N and previous was N-1
    for i, o in enumerate(rows):
        lv = o["levels_completed"]
        if i > 0 and lv == rows[i - 1]["levels_completed"] + 1:
            # this row is clear-of-previous; next row is start of new level if exists
            if i + 1 < len(rows) and rows[i + 1]["levels_completed"] == lv:
                start = rows[i + 1]
                g = plane(start["frame"])
                s = ls20.init(start["frame"])
                print(f"L{lv+1} start at rec i={i+1}")
                print("  cursor", s.cursor, "armed", s.armed)
                print("  goals", [(g.id, g.shape) for g in s.goals])
                print("  walkable", len(s.walkable), "carrying", s.carrying)
                print("  c12", ls20.locate_mover(start["frame"]))
                if lv == 1:
                    OUT.write_text(json.dumps({
                        "game_id": start.get("game_id"),
                        "levels_completed": lv,
                        "frame": start["frame"],
                        "note": "design-time from recording; first frame after L1 clear",
                    }), encoding="utf-8")
                    print("  wrote", OUT)


if __name__ == "__main__":
    main()
