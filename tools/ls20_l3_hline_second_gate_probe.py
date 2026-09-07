"""Probe E2: does ADJACENCY to hline arm L3, then does the second gate clear?

CONTEXT (docs/ls20_l3_energy_review.md + ls20_l3_arming_deadlock.md)
  Every L3 arming experiment only tested "mover/carrying OVERLAP the plus
  marker". Never tested ADJACENCY to the hline (color-1 bar at (54,4)-(58,4)).
  The mover at (9,1)/(10,1) has its 5x2 footprint directly below the hline y=4 —
  touching but not overlapping. Both cells are in the UPPER half (energy-cheap).

  If adjacency arms, the color-9 gates open and the mover can then reach the
  second gate (5,9) — which the energy review showed is reachable WITHOUT the
  H23 ritual via "detour to pickup1 (3,6)" (17 steps, fuel_end=16).

  Composite path (one online run, two hypotheses):
    (1) mover -> (10,1)  [hline adjacency]  -> snapshot (did anything arm?)
    (2) armed path (10,1) -> pickup1 -> second gate (5,9) -> levels 2->3?

USAGE
  python tools/ls20_l3_hline_second_gate_probe.py --plan-only
  python tools/ls20_l3_hline_second_gate_probe.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import carrying_bbox_from_cursor, mover_bbox_from_cursor
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import (
    MAX_FUEL, _energy_bfs, _ov, _pickup_mask, _step_cell,
)
from tools.ls20_l3_armed_controller import reach_l3
from tools.ls20_second_block_probe import main_mover_and_second
from tools.ls20_second_gate_probe import second_block, second_gate_cells

FIXTURE = ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json"
REPORT = ROOT / "docs" / "ls20_l3_hline_second_gate_probe.md"

HLINE_ADJ_CELL = (10, 1)  # mover footprint y5-6 directly below hline y4


def _plane(frame):
    a = np.asarray(frame, dtype=np.int8)
    if a.ndim == 2:
        return a
    for i in range(a.shape[0]):
        if np.any(a[i] == ls20.MOVE_COLOR):
            return a[i]
    return a[0]


def _color1_comps(frame):
    """bboxes of every playfield color-1 component (hline/vline/plus)."""
    g = _plane(frame)
    H, W = g.shape
    vis = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(H):
        for x in range(W):
            if g[y, x] != 1 or vis[y, x] or y >= 54:
                continue
            q = [(x, y)]
            vis[y, x] = True
            cells = []
            while q:
                cx, cy = q.pop()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 0 <= ny < H and not vis[ny, nx] and g[ny, nx] == 1:
                        vis[ny, nx] = True
                        q.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            out.append((min(xs), min(ys), max(xs), max(ys)))
    return sorted(out)


def _snapshot(frame) -> dict:
    g = _plane(frame)
    mover = ls20.locate_mover(frame)
    _, seconds = main_mover_and_second(frame)
    second = seconds[0] if seconds else None
    c1 = _color1_comps(frame)
    return {
        "mover": mover, "second": second, "c1_comps": c1,
        "c9": int((g == 9).sum()), "c14": int((g == 14).sum()),
        "c11": int((g == 11).sum()),
        "layers": np.asarray(frame).shape[0] if np.asarray(frame).ndim == 3 else 1,
    }


def plan_composite(frame):
    """(path_to_hline, hline_cell, path_to_second_gate, info)."""
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    stamp = next((g.shape for g in state.goals if g.id == "ls20-stamp"), None)
    if stamp is None:
        raise RuntimeError("no stamp goal")
    gates = second_gate_cells(frame, offset, walk_a, walk_u)
    if not gates:
        raise RuntimeError("no second gate cell")
    gate = gates[0]

    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))

    # path A: start -> hline adjacency cell (unarmed walkable)
    pA = _energy_bfs(
        state.cursor, fuel0, 0, walk_u, pickups, offset,
        lambda c, _f, _p: c == HLINE_ADJ_CELL, warps,
    )
    if pA[0] is None:
        raise RuntimeError(f"hline adj cell {HLINE_ADJ_CELL} unreachable")

    # path B: hline cell -> second gate (armed walkable, may grab pickup1 en route)
    pB = _energy_bfs(
        HLINE_ADJ_CELL, pA[2], pA[3], walk_a, pickups, offset,
        lambda c, _f, _p: c == gate, warps,
    )
    if pB[0] is None:
        raise RuntimeError(f"second gate {gate} unreachable on armed walkable from hline")

    return (
        list(pA[0]), HLINE_ADJ_CELL, list(pB[0]), gate,
        {
            "offset": offset, "stamp": stamp, "pickups": pickups,
            "fuel0": fuel0, "fuel_at_hline": pA[2], "pmask_at_hline": pA[3],
            "fuel_at_gate": pB[2], "pathA_len": len(pA[0]), "pathB_len": len(pB[0]),
        },
    )


def plan_only() -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    pA, hline_cell, pB, gate, info = plan_composite(data["frame"])
    print(f"hline adj cell = {hline_cell}")
    print(f"second gate   = {gate}")
    print(f"pathA (start->hline) len={info['pathA_len']} fuel_at={info['fuel_at_hline']}")
    print(f"  actions = {[DIR_TO_ACTION[a] for a in pA]}")
    print(f"pathB (hline->gate)  len={info['pathB_len']} fuel_at={info['fuel_at_gate']}")
    print(f"  actions = {[DIR_TO_ACTION[a] for a in pB]}")
    return 0


def run_online() -> int:
    key = _api_key()
    if not key:
        raise RuntimeError("no ARC_API_KEY")
    sess = OnlineSession(key)
    try:
        frame, meta = reach_l3(sess)
        print(f"reached L3 levels={meta.get('levels_completed')} "
              f"mover={ls20.locate_mover(frame)}")
        pA, hline_cell, pB, gate, info = plan_composite(frame)
        print(f"hline={hline_cell} gate={gate} pathA={len(pA)} pathB={len(pB)}")
        print(f"pathA actions = {[DIR_TO_ACTION[a] for a in pA]}")
        print(f"pathB actions = {[DIR_TO_ACTION[a] for a in pB]}")

        base = _snapshot(frame)
        log = [{"step": 0, "action": "RESET", "levels": 2, **base}]
        lv = 2

        # phase A: to hline adjacency
        for i, a in enumerate(pA, 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            new_lv = int(meta.get("levels_completed") or 0)
            log.append({"step": f"A{i}", "action": DIR_TO_ACTION[a],
                        "levels": new_lv, **_snapshot(frame)})
            print(f"  A{i:02d} A{DIR_TO_ACTION[a]} mover={ls20.locate_mover(frame)} "
                  f"lv={new_lv}")
            if new_lv > lv:
                print(f"  >>> LEVEL UP {lv}->{new_lv} during hline approach")
                _report(log, "MOVES_CLEARED", hline_cell, gate, info)
                return 0
        at_hline = _snapshot(frame)
        # did arriving at hline adjacency change anything vs base?
        changed = {k: (base[k], at_hline[k]) for k in base if base[k] != at_hline[k]}
        print(f"  AT HLINE: changed_keys={sorted(changed)}")
        print(f"    base c1={base['c1_comps']}  now c1={at_hline['c1_comps']}")

        # phase B: armed path to second gate
        lv = int(meta.get("levels_completed") or 0)
        blocked_at = None
        for i, a in enumerate(pB, 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            new_lv = int(meta.get("levels_completed") or 0)
            snap = _snapshot(frame)
            log.append({"step": f"B{i}", "action": DIR_TO_ACTION[a],
                        "levels": new_lv, **snap})
            print(f"  B{i:02d} A{DIR_TO_ACTION[a]} mover={snap['mover']} lv={new_lv}")
            if new_lv > lv:
                print(f"  >>> LEVEL UP {lv}->{new_lv} at second gate")
                _report(log, "HLINE_ARMED_CLEARED", hline_cell, gate, info)
                return 0
            # detect wall-hit: mover bbox unchanged despite a move action
            if i >= 2 and snap["mover"] == log[-2]["mover"] and \
                    log[-2]["action"] in (1, 2, 3, 4):
                blocked_at = i
                print(f"  BLOCKED at B{i} (mover stalled on color-9 gate)")
                break
        if blocked_at is not None:
            _report(log, "HLINE_NOT_ARMED_BLOCKED", hline_cell, gate, info)
        else:
            _report(log, "BLOCKED", hline_cell, gate, info)
        return 1
    finally:
        sess.close()


def _report(log, verdict, hline_cell, gate, info) -> None:
    lines = [
        "# ls20 L3 hline 相邻 + 第二块门 合成探针（E2）报告",
        "",
        "> 脚本：`tools/ls20_l3_hline_second_gate_probe.py`",
        "> 性质：设计期探路（最小动作 + 比对 levels），非运行时求解器",
        "",
        "---",
        "",
        "## 结论",
        "",
        f"**{verdict}**",
        "",
        "| 项 | 值 |",
        "|----|----|",
        f"| hline 相邻格 | `{hline_cell}` |",
        f"| 第二块门 | `{gate}` |",
        f"| pathA_len / pathB_len | {info['pathA_len']} / {info['pathB_len']} |",
        f"| fuel_at_hline | {info['fuel_at_hline']} |",
        f"| fuel_at_gate | {info['fuel_at_gate']} |",
        "",
        "## 逐步",
        "",
    ]
    for r in log:
        lines.append(f"- `{r}`")
    lines += [
        "",
        "## 判读",
        "",
        "- `MOVES_CLEARED`：hlive 接近过程中就过关（hlive 相邻直接触发）。",
        "- `HLINE_ARMED_CLEARED`：hlive 相邻武装 + 第二块门通关。",
        "- `HLINE_NOT_ARMED_BLOCKED`：hlive 相邻没武装，第二块门色9未开（撞墙）。",
        "- `BLOCKED`：其它。",
        "",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-only", action="store_true")
    args = ap.parse_args()
    if args.plan_only:
        return plan_only()
    return run_online()


if __name__ == "__main__":
    raise SystemExit(main())
