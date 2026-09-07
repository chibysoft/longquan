"""Infer L4 path from recording cursor deltas (actions not stored)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.state import DIRS
from tools.ls20_seated_clear_full import _step_cell

REC = Path(
    r"D:\Projects\ARC-AGI-3-Agents\recordings"
    r"\ls20-9607627b.lingjingsolo.800.5f1bf1fd-a88e-4c5f-8c63-3c85bc6f5f97.recording.jsonl"
)
OUT = ROOT / "docs" / "ls20_l4_recording_path.md"


def main() -> int:
    rows = [json.loads(l).get("data", {}) for l in open(REC, encoding="utf-8")]
    # true L4 start = first frame with stamp (8,4,14,10) at lv==3
    start = None
    end = None
    for i, d in enumerate(rows):
        st = ls20.init(d["frame"])
        stamp = next((g.shape for g in st.goals if g.id == "ls20-stamp"), None)
        lv = int(d.get("levels_completed") or 0)
        if start is None and lv == 3 and stamp == (8, 4, 14, 10):
            start = i
        if start is not None and lv == 4:
            end = i
            break
    print("start", start, "end", end)

    lines = [
        "# L4 path inferred from lingjingsolo cursors",
        "",
        f"> rows {start}..{end}",
        "",
    ]
    prev_c = None
    prev_f = None
    for i in range(start, end + 1):
        d = rows[i]
        f = d["frame"]
        st = ls20.init(f)
        off = ls20.grid_offset(f)
        wu = ls20.build_walkable(f, off, armed=False)
        wa = ls20.build_walkable(f, off, armed=True)
        warps = ls20.detect_warps(f, off, wu)
        cur = st.cursor
        armed_only = sorted(wa - wu)
        # gate_u
        stamp = next(g.shape for g in st.goals if g.id == "ls20-stamp")
        from longquan.interactive.match import mover_bbox_from_cursor

        gate = None
        for c in sorted(wa):
            mb = mover_bbox_from_cursor(c, off)
            x0 = max(mb[0], stamp[0]); y0 = max(mb[1], stamp[1])
            x1 = min(mb[2], stamp[2]); y1 = min(mb[3], stamp[3])
            if max(0, x1 - x0 + 1) * max(0, y1 - y0 + 1) >= 10:
                gate = c
                break
        gate_u = gate in wu if gate is not None else None

        # infer action from prev
        inferred = None
        if prev_c is not None:
            for dname, dxy in zip("UDLR", DIRS):
                pred = _step_cell(prev_c, dxy, wu_prev, warps_prev)
                if pred == cur:
                    inferred = dname
                    break
            if inferred is None:
                # maybe model mismatch
                inferred = f"MISMATCH from {prev_c}"

        row = {
            "i": i,
            "lv": d.get("levels_completed"),
            "cursor": cur,
            "ui": ls20.ui_energy(f),
            "gate_u": gate_u,
            "armed_only": armed_only,
            "inferred": inferred,
            "n_warps": len(warps),
            # portal (6,4) DOWN pred
            "w64D": warps.get(((6, 4), (0, 1))),
            "w75U": warps.get(((7, 5), (0, -1))),
        }
        lines.append(f"- `{row}`")
        print(row)
        prev_c = cur
        wu_prev, warps_prev = wu, warps
        prev_f = f

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
