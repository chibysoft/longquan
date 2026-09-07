"""Infer L5 clear path from lingjingsolo recording via cursor deltas."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20

REC = Path(
    r"D:\Projects\ARC-AGI-3-Agents\recordings"
    r"\ls20-9607627b.lingjingsolo.800.5f1bf1fd-a88e-4c5f-8c63-3c85bc6f5f97.recording.jsonl"
)


def main():
    rows = []
    with open(REC, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            o = json.loads(line)["data"]
            frame = o.get("frame")
            cur = ui = stamp = None
            if frame is not None:
                try:
                    st = ls20.init(frame)
                    cur = st.cursor
                    ui = ls20.ui_energy(frame)
                    stamp = next(
                        (g.shape for g in st.goals if g.id == "ls20-stamp"), None
                    )
                except Exception as e:
                    cur = ("err", str(e)[:60])
            rows.append(
                {
                    "i": i,
                    "lv": o.get("levels_completed"),
                    "cur": cur,
                    "ui": ui,
                    "stamp": stamp,
                    "state": o.get("state"),
                }
            )

    idx5 = next(r["i"] for r in rows if (r["lv"] or 0) >= 5)
    idx4 = next(r["i"] for r in rows if (r["lv"] or 0) >= 4)
    print("first lv>=4", idx4, "first lv>=5", idx5, "state", rows[idx5]["state"])
    for r in rows[idx4 : idx5 + 1]:
        prev = rows[r["i"] - 1]["cur"] if r["i"] else None
        d = None
        if (
            prev
            and r["cur"]
            and isinstance(prev, tuple)
            and isinstance(r["cur"], tuple)
            and len(prev) == 2
            and len(r["cur"]) == 2
        ):
            d = (r["cur"][0] - prev[0], r["cur"][1] - prev[1])
        print(
            f"{r['i']:3d} lv={r['lv']} cur={r['cur']} d={d} "
            f"ui={r['ui']} stamp={r['stamp']}"
        )


if __name__ == "__main__":
    main()
