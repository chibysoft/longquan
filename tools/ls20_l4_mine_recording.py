"""Mine lingjingsolo recording for L3->L4 clear (design-time mechanism)."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20

REC = Path(
    r"D:\Projects\ARC-AGI-3-Agents\recordings"
    r"\ls20-9607627b.lingjingsolo.800.5f1bf1fd-a88e-4c5f-8c63-3c85bc6f5f97.recording.jsonl"
)
OUT = ROOT / "docs" / "ls20_l4_recording_mine.md"
AID = {1: "U", 2: "D", 3: "L", 4: "R", 5: "A5", 6: "A6", 0: "RESET?"}


def main() -> int:
    rows = []
    with open(REC, encoding="utf-8") as fh:
        for line in fh:
            rows.append(json.loads(line).get("data", {}))

    bounds = []
    prev = None
    for i, d in enumerate(rows):
        lv = int(d.get("levels_completed") or 0)
        if prev is None or lv != prev:
            ai = d.get("action_input") or {}
            bounds.append((i, lv, ai.get("id"), ai.get("data"), d.get("state")))
            prev = lv
    print("bounds", bounds)

    start = next(i for i, lv, *_ in bounds if lv == 3)
    end = next(i for i, lv, *_ in bounds if lv == 4)
    seg = rows[start : end + 1]
    print(f"L4 segment {start}..{end} n={len(seg)}")

    lines = [
        "# L4 clear mined from lingjingsolo recording",
        "",
        f"> `{REC.name}` rows {start}..{end} (design-time; not a canned solver table)",
        "",
        "## Level bounds",
        "",
    ]
    for b in bounds:
        lines.append(f"- `{b}`")

    lines += ["", "## Frame-by-frame (lv 3→4)", ""]
    cursors = []
    acts = []
    gate_opens_at = None
    for i, d in enumerate(seg):
        ai = d.get("action_input") or {}
        aid = ai.get("id")
        adata = ai.get("data") or {}
        frame = d.get("frame")
        lv = int(d.get("levels_completed") or 0)
        cur = ui = gate_u = stamp9 = None
        unlock = None
        try:
            st = ls20.init(frame)
            cur = st.cursor
            ui = ls20.ui_energy(frame)
            off = ls20.grid_offset(frame)
            wu = ls20.build_walkable(frame, off, armed=False)
            wa = ls20.build_walkable(frame, off, armed=True)
            from longquan.interactive.match import mover_bbox_from_cursor

            stamp = next((g.shape for g in st.goals if g.id == "ls20-stamp"), None)
            gate = None
            if stamp is not None:
                for c in sorted(wa):
                    mb = mover_bbox_from_cursor(c, off)
                    x0 = max(mb[0], stamp[0]); y0 = max(mb[1], stamp[1])
                    x1 = min(mb[2], stamp[2]); y1 = min(mb[3], stamp[3])
                    ov = max(0, x1 - x0 + 1) * max(0, y1 - y0 + 1)
                    if ov >= 10:
                        gate = c
                        break
            gate_u = gate in wu if gate is not None else None
            if stamp is not None:
                g = ls20._plane(frame)
                x0, y0, x1, y1 = stamp
                stamp9 = int((g[y0 : y1 + 1, x0 : x1 + 1] == 9).sum())
            unlock = sorted(wa - wu)
        except Exception as e:
            cur = f"err:{e}"
        row = {
            "i": start + i,
            "lv": lv,
            "act": AID.get(aid, aid),
            "aid": aid,
            "xy": (adata.get("x"), adata.get("y")) if adata else None,
            "cursor": cur,
            "ui": ui,
            "gate_u": gate_u,
            "stamp9": stamp9,
            "unlock": unlock,
        }
        if isinstance(cur, tuple):
            cursors.append(cur)
        acts.append(aid)
        if gate_u and gate_opens_at is None and lv == 3:
            gate_opens_at = row
        # print all for short segment; else sparse
        if len(seg) <= 120 or i < 40 or i >= len(seg) - 15 or (
            gate_u and i > 0 and not (
                (ls20.init(seg[i - 1]["frame"]).cursor if False else None)
            )
        ):
            lines.append(f"- `{row}`")
        elif i == 40:
            lines.append(f"- ... ({len(seg) - 55} middle rows omitted in summary; see acts) ...")

    lines += ["", "## Action sequence (ids while arriving at lv3 frames until lv4)", ""]
    # action that produced frame i is in frame i's action_input
    seq = [AID.get(a, a) for a in acts]
    lines.append(f"- len={len(seq)}")
    lines.append(f"- `{seq}`")
    lines.append(f"- hist `{Counter(seq)}`")
    lines += ["", f"## Unique cursors ({len(set(cursors))})", ""]
    lines.append(f"- `{sorted(set(cursors))}`")
    if gate_opens_at:
        lines += ["", "## First gate_u True", "", f"- `{gate_opens_at}`"]
    else:
        lines += ["", "## First gate_u True", "", "- (never observed before lv4 — clear may be stamp entry)"]

    # compare first lv3 frame vs frame before lv4 for plane diffs of interest
    f0 = seg[0]["frame"]
    f1 = seg[-2]["frame"] if len(seg) >= 2 else seg[-1]["frame"]
    try:
        from tools.ls20_l4_h5e_diff_probe import _plane_diff, _snap
        dlt = _plane_diff(f0, f1, limit=40)
        lines += ["", "## Plane diff start→pre-clear", ""]
        lines.append(f"- start `{_snap(f0)}`")
        lines.append(f"- preclear `{_snap(f1)}`")
        lines.append(f"- n={dlt['n']} trans={dlt['transitions']}")
    except Exception as e:
        lines.append(f"- diff err {e}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print("seq", seq)
    print("gate_open", gate_opens_at)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
