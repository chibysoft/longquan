"""L3 arming controlled experiments (offline plan + minimal online actions).

WHY THIS EXISTS
  L1+L2 seated clear PASS, L3 is stuck: the mover reaches the stamp gate
  (armed-only cell), but the engine still treats it as UNARMED and the color-9
  gate blocks entry. This script replaces "blind ritual tweaking" with THREE
  falsifiable experiments, each = one BFS-generated path + one arming check.

GEOMETRIC FINDING (offline, from tests/fixtures/ls20_l3_frame_live.json)
  L3 has THREE 5-pixel color-0/1 components: vline(8,5,8,9), plus(50,11,52,13),
  hline(54,4,58,4). Only `plus` has any contact cell (carrying or mover bbox
  overlaps it). vline/hline are physically unreachable by either footprint, so
  they cannot be carrying-overlap arming markers. `ls20.init` picks `plus` —
  which is geometrically the only viable choice.

EXPERIMENTS (the single variable is "what makes arming stick on L3")
  C1  contact plus only (H19)                      -> stamp gate
  C2  contact plus + H23 ritual UP-DOWN-DOWN       -> stamp gate  (L2 baseline)
  (C3 "eat pickups first" was DROPPED as redundant: C2's log shows a pickup is
   already eaten en route before contact, yet arming still fails — see docs.)

  Arming check = can the mover actually enter the armed-only stamp gate (a cell
  whose 5x2 footprint overlaps the color-5 stamp block and contains color 9)?
  If it enters / levels+1 -> arming happened. If blocked -> that hypothesis is
  refuted for this experiment's preconditions.

Usage:
  python tools/ls20_l3_armed_controller.py --plan-only            # offline plan
  python tools/ls20_l3_armed_controller.py --experiment C1        # reach L3 + run C1
  python tools/ls20_l3_armed_controller.py --experiment C1 --experiment C2 ...
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import carrying_bbox_from_cursor, mover_bbox_from_cursor
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import (
    MAX_FUEL, _energy_bfs, _ov, _ov_stamp, _pickup_mask, _step_cell, plan_two_phase,
)

FIXTURE = ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json"
REPORT = ROOT / "docs" / "ls20_l3_armed_results.md"

# H23 live-probed minimal vertical sweep after contact (seated on L2).
RITUAL = ((0, -1), (0, 1), (0, 1))  # UP, DOWN, DOWN

EXPERIMENTS = ("C1", "C2")


def analyze_frame(frame):
    """Extract everything an experiment needs from an L3 frame (no canned coords)."""
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)

    stamp = next((g.shape for g in state.goals if g.id == "ls20-stamp"), None)
    if stamp is None:
        raise RuntimeError("no stamp goal")

    # contact cells for the 'plus' marker = carrying overlaps marker
    marker = next((g.shape for g in state.goals if g.id == "ls20-marker"), None)
    plus_contacts = [
        c for c in walk_u
        if marker is not None and _ov(carrying_bbox_from_cursor(c, offset), marker) > 0
    ]
    if not plus_contacts:
        raise RuntimeError(f"no plus contact cell; marker={marker}")

    # armed-only cells whose mover footprint overlaps the stamp block (the gate)
    gate_cells = sorted(
        c for c in (walk_a - walk_u)
        if _ov(mover_bbox_from_cursor(c, offset), stamp) > 0
    )

    # pickup cells = walkable cells whose mover footprint overlaps a pickup
    pickup_cells = sorted(
        c for c in walk_u
        if any(_ov(mover_bbox_from_cursor(c, offset), pb) > 0 for pb in pickups)
    )

    return {
        "state": state, "offset": offset, "walk_u": walk_u, "walk_a": walk_a,
        "warps": warps, "pickups": pickups, "stamp": stamp, "marker": marker,
        "plus_contacts": plus_contacts, "gate_cells": gate_cells,
        "pickup_cells": pickup_cells,
    }


def plan_experiment(frame, exp_id: str) -> Tuple[List[Tuple[int, int]], dict]:
    """Energy-aware plan for one experiment; raise on unreachable.

    Uses the same fuel model as seated_clear (_energy_bfs) so the mover reaches
    the gate WITH energy — otherwise L3's ~21-step soft-reset confounds the
    "was the gate blocked by color-9 (arming) or by soft-reset?" question.
    """
    a = analyze_frame(frame)
    start = a["state"].cursor
    offset = a["offset"]
    walk_u, walk_a = a["walk_u"], a["walk_a"]
    warps = a["warps"]
    pickups = a["pickups"]
    stamp = a["stamp"]
    marker = a["marker"]
    plus_contact = a["plus_contacts"][0]
    gate = a["gate_cells"][0] if a["gate_cells"] else None
    if gate is None:
        raise RuntimeError("no stamp gate cell (armed-only overlapping stamp)")

    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))

    def at_contact(cell, _fuel, _pm):
        return _ov(carrying_bbox_from_cursor(cell, offset), marker) > 0

    def at_gate(cell, _fuel, _pm):
        return _ov_stamp(cell, offset, stamp) >= 10

    path: List[Tuple[int, int]] = []
    notes = {"contact": plus_contact, "gate": gate}

    # phase 1: reach contact, energy-aware
    p1, c1, f1, pm1 = _energy_bfs(
        start, fuel0, 0, walk_u, pickups, offset, at_contact, warps,
    )
    if p1 is None:
        raise RuntimeError(f"{exp_id}: contact {plus_contact} unreachable")
    path.extend(p1)
    cur, fuel, pmask = c1, f1, pm1

    # ritual (C2): UP-DOWN-DOWN at the contact cell, fuel-tracked
    if exp_id == "C2":
        for d in RITUAL:
            nxt = _step_cell(cur, d, walk_u, warps)
            if nxt is None:
                raise RuntimeError(f"{exp_id}: ritual {d} blocked at {cur}")
            n_mask, refilled = _pickup_mask(nxt, offset, pickups, pmask)
            if fuel <= 0 and not refilled:
                raise RuntimeError(f"{exp_id}: ritual out of fuel at {cur}")
            fuel = MAX_FUEL if refilled else fuel - 1
            cur, pmask = nxt, n_mask
            path.append(d)
        notes["ritual"] = list(RITUAL)

    # phase 2: reach gate on ARMED walkable (assumes the hypothesis arms it)
    p2, _c2, _f2, _pm2 = _energy_bfs(
        cur, fuel, pmask, walk_a, pickups, offset, at_gate, warps,
    )
    if p2 is None:
        raise RuntimeError(f"{exp_id}: gate {gate} unreachable from {cur}")
    path.extend(p2)

    return path, notes


def reach_l3(sess: OnlineSession):
    """open + RESET, then clear L1 and L2 with the seated planner, stop at L3."""
    sess.open(tags=["ls20_l3_armed_controller"])
    reset = sess.reset()
    frame, meta = reset["frame"], reset
    while int(meta.get("levels_completed") or 0) < 2:
        lv = int(meta.get("levels_completed") or 0)
        path, _ = plan_two_phase(frame)
        leveled = False
        for a in path:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            if int(meta.get("levels_completed") or 0) > lv:
                leveled = True
                break
        if not leveled:
            raise RuntimeError(f"failed to clear level {lv} (reaching L3)")
        sync = sess.action(1)  # stale-frame fix: next action yields true frame
        frame, meta = sync["frame"], sync
    return frame, meta


def run_experiment(sess: OnlineSession, exp_id: str, l3_frame) -> dict:
    # l3_frame is the LIVE L3 frame; plan against it (no canned coords).
    path, notes = plan_experiment(l3_frame, exp_id)
    result = {
        "experiment": exp_id,
        "notes": notes,
        "actions": [DIR_TO_ACTION[a] for a in path],
        "path_len": len(path),
    }
    log = []
    for i, a in enumerate(path, 1):
        resp = sess.action(DIR_TO_ACTION[a])
        frame, meta = resp["frame"], resp
        new_lv = int(meta.get("levels_completed") or 0)
        mover = ls20.locate_mover(frame)
        arr = np.asarray(frame)
        layers = arr.shape[0] if arr.ndim == 3 else 1
        c11 = int((ls20._plane(frame) == 11).sum())
        print(f"  {i:02d} A{DIR_TO_ACTION[a]} bbox={mover} lv={new_lv} "
              f"layers={layers} c11={c11}")
        log.append({
            "step": i, "action": DIR_TO_ACTION[a], "mover": mover, "levels": new_lv,
            "layers": layers, "c11": c11,
        })
        if new_lv > 2:  # L3 cleared (armed + stamped)
            result["levels_after"] = new_lv
            result["steps_used"] = i
            result["verdict"] = "ARMED+CLEARED"
            result["log"] = log
            return result
    # no level-up: the gate stayed color-9-blocked -> arming did not stick
    result["levels_after"] = 2
    result["verdict"] = "BLOCKED (no level-up)"
    result["log"] = log
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="ls20 L3 arming controlled experiments")
    ap.add_argument("--plan-only", action="store_true",
                    help="offline-plan all experiments from the L3 fixture; no API")
    ap.add_argument("--experiment", action="append", choices=EXPERIMENTS,
                    help="run this experiment online (repeatable); default all")
    args = ap.parse_args()

    if args.plan_only:
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        frame = data["frame"]
        for e in EXPERIMENTS:
            try:
                path, notes = plan_experiment(frame, e)
                print(f"{e}: len={len(path)} contact={notes.get('contact')} "
                      f"gate={notes.get('gate')} pickup={notes.get('pickup')} "
                      f"ritual={notes.get('ritual')}")
                print(f"    actions={[DIR_TO_ACTION[a] for a in path]}")
            except RuntimeError as ex:
                print(f"{e}: PLAN FAIL: {ex}")
        return 0

    key = _api_key()
    if not key:
        raise RuntimeError("ARC_API_KEY not found (check ARC-AGI-3-Agents/.env)")

    exps = args.experiment or list(EXPERIMENTS)
    results = []
    # Each experiment gets a FRESH scorecard (RESET semantics are ambiguous; an
    # isolated open->reach-L3->run isolates the variable under test).
    for e in exps:
        sess = OnlineSession(key)
        try:
            l3_frame, l3_meta = reach_l3(sess)
            print(f"{e}: reached L3 levels={l3_meta.get('levels_completed')} "
                  f"mover={ls20.locate_mover(l3_frame)}")
            r = run_experiment(sess, e, l3_frame)
            results.append(r)
            print(f"{e}: {r['verdict']} len={r['path_len']} "
                  f"levels_after={r.get('levels_after')}")
        finally:
            sess.close()

    # append results to the report
    write_report(results)
    return 0


def write_report(results: List[dict]) -> Path:
    lines = [
        "# ls20 L3 武装对照实验报告",
        "",
        "> 脚本：`tools/ls20_l3_armed_controller.py`",
        "> 性质：设计期探路（发最小动作序列 + 比对 levels），非运行时求解器",
        "",
        "---",
        "",
        "## 几何前提（离线已证）",
        "",
        "L3 三个 color-0/1 连通域中，只有 `plus`(50,11,52,13) 有接触点",
        "（carrying/mover footprint 能重叠）；`vline`/`hline` 物理上接触不到，",
        "故不可能是 carrying-overlap 型武装 marker。`ls20.init` 选 `plus` 是几何上",
        "唯一可选。",
        "",
        "## 三个对照实验",
        "",
        "| 实验 | 假设 | 前置 | 预期 |",
        "|------|------|------|------|",
        "| C1 | H19：接触 plus 即武装 | 无 | 盖印门放开 |",
        "| C2 | H19+H23：接触 plus + UDD 仪式 | 无 | 盖印门放开（L2 基线） |",
        "| C3 | _降级_：先吃补给再武装 | 已由 C2 证伪 | 不跑 |",
        "",
        "---",
        "",
        "## 执行结果",
        "",
    ]
    if not results:
        lines.append("_尚未执行线上（可先 `--plan-only` 看路径）。_")
    else:
        for r in results:
            lines.append(f"### {r['experiment']} — {r['verdict']}")
            lines.append("")
            lines.append(f"- 路径长：{r['path_len']}")
            lines.append(f"- 动作：`{r['actions']}`")
            lines.append(f"- notes：`{r['notes']}`")
            if "levels_after" in r:
                lines.append(f"- levels_after：{r['levels_after']}")
            lines.append("")
    lines += [
        "---",
        "",
        "## 判读",
        "",
        "- C1/C2 任一 `CLEARED` → L3 武装判据 = L2 的 H19（±H23），init 选对，",
        "  阻塞在别处（去查 planner 的路径/仪式执行）。",
        "- 两者全 `BLOCKED` → L3 武装判据 ≠ L2 的 carrying-overlap 族，",
        "  需另开假设轮（双标记 / 顺序 / 其它几何触发）。",
        "  （C3 已被 C2 的失败证伪：C2 吃补给后才接触，仍不武装。）",
        "",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT


if __name__ == "__main__":
    raise SystemExit(main())
