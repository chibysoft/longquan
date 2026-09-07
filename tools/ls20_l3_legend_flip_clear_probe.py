"""Probe E8: legend flip (ring dissolve) -> full L1/L2 clear flow.

WHY
  E7's full-plane diff proved the ring dissolve is a REAL state change: entering
  (5,9) turns the 24px color12 legend (x3-8,y55-60) into color9 (c12 36->10,
  c9 23->45) while the carrying (15px color9) is preserved under the mover.
  E6 proved the stamp column is HARD-blocked from above: the mover cannot DOWN
  from (10,9) into (10,10) — color5 solid, not color9, blocks it.

  Those two facts have never been COMBINED. The open hypothesis this probe
  tests: the legend flip IS the "arming" step, and after it the ordinary
  L1/L2 clear flow (contact marker -> H23 ritual -> armed walk to stamp gate)
  will clear L3 (levels 2 -> 3). Even a FAILURE is decisive: it eliminates
  "legend flip is the missing prerequisite" as an explanation.

FLOW
  1. reach_l3  (clears L1+L2, stops at L3)
  2. walk to (4,9) (ring-left), RIGHT into (5,9) -> ring dissolves, legend flips
  3. plan_two_phase on the DISSOLVED frame (contact -> ritual -> stamp)
  4. execute, watching levels every step

USAGE
  python tools/ls20_l3_legend_flip_clear_probe.py --plan-only
  python tools/ls20_l3_legend_flip_clear_probe.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, plan_two_phase
from tools.ls20_l3_armed_controller import reach_l3

REPORT = ROOT / "docs" / "ls20_l3_legend_flip_clear_probe.md"

POINT = (4, 9)      # ring-left adjacent (walkable)
RING_GATE = (5, 9)  # RIGHT from (4,9) enters and dissolves the ring


def _plan_path(frame, target):
    """Energy-aware path from current cursor to `target` (reuse E7's helper)."""
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))
    return _energy_bfs(
        state.cursor, fuel0, 0, walk_u, pickups, offset,
        lambda c, _f, _p: c == target, warps,
    )[0]


def _snap(frame, tag, levels):
    g = ls20._plane(frame)
    arr = np.asarray(frame)
    return {
        "tag": tag,
        "levels": levels,
        "mover": ls20.locate_mover(frame),
        "layers": arr.shape[0] if arr.ndim == 3 else 1,
        "c9": int((g == 9).sum()),
        "c11": int((g == 11).sum()),
        "c12": int((g == 12).sum()),
    }


def plan_only() -> int:
    import json
    data = json.loads((ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json")
                      .read_text(encoding="utf-8"))
    frame = data["frame"]
    p = _plan_path(frame, POINT)
    print(f"POINT={POINT} RING_GATE={RING_GATE}")
    print(f"path to (4,9) len={None if p is None else len(p)}")
    if p:
        print(f"  actions={[DIR_TO_ACTION[a] for a in p]}")
    # plan_two_phase on the PRE-dissolve frame (offline: dissolve itself needs engine)
    try:
        path, info = plan_two_phase(frame)
        print(f"plan_two_phase(pre-dissolve) len={len(path)} ritual={info['ritual']}")
        print(f"  t1={info['t1']} t2={info['t2']} stamp={info['stamp']} "
              f"marker={info['marker']}")
    except RuntimeError as ex:
        print(f"plan_two_phase(pre-dissolve) FAIL: {ex}")
    return 0


def run_online() -> int:
    key = _api_key()
    if not key:
        raise RuntimeError("ARC_API_KEY not found")
    sess = OnlineSession(key)
    try:
        # --- Phase 1: reach L3 ---
        frame, meta = reach_l3(sess)
        lv = int(meta.get("levels_completed") or 0)
        print(f"reached L3 levels={lv} mover={ls20.locate_mover(frame)}")
        log = [_snap(frame, "l3_start", lv)]

        # --- Phase 2: dissolve ring -> legend flip ---
        p = _plan_path(frame, POINT)
        if p is None:
            raise RuntimeError(f"no path to {POINT}")
        print(f"walking {len(p)} steps to {POINT}")
        for a in p:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            new_lv = int(meta.get("levels_completed") or 0)
            if new_lv > lv:
                log.append(_snap(frame, "CLEARED_DURING_WALK", new_lv))
                _write_report(log, "CLEARED_DURING_WALK")
                return 0
        log.append(_snap(frame, "at_point", int(meta.get("levels_completed") or 0)))

        resp = sess.action(DIR_TO_ACTION[(1, 0)])  # RIGHT -> dissolve
        frame, meta = resp["frame"], resp
        new_lv = int(meta.get("levels_completed") or 0)
        log.append(_snap(frame, "post_dissolve", new_lv))
        print(f"post-dissolve: mover={ls20.locate_mover(frame)} lv={new_lv}")
        if new_lv > lv:
            _write_report(log, "CLEARED_BY_DISSOLVE")
            return 0

        # --- Phase 3: plan_two_phase on dissolved frame ---
        try:
            path, info = plan_two_phase(frame)
        except RuntimeError as ex:
            log.append({"tag": "plan_fail_after_dissolve", "error": str(ex),
                        "levels": new_lv})
            _write_report(log, "PLAN_FAIL_AFTER_DISSOLVE")
            print(f"plan_two_phase(dissolved) FAIL: {ex}")
            return 1
        print(f"plan_two_phase(dissolved): len={len(path)} ritual={info['ritual']} "
              f"t1={info['t1']} t2={info['t2']} stamp={info['stamp']}")
        log.append({"tag": "plan", "info": info,
                    "actions": [DIR_TO_ACTION[a] for a in path]})

        # --- Phase 4: execute, watch levels ---
        for i, a in enumerate(path, 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            new_lv = int(meta.get("levels_completed") or 0)
            log.append(_snap(frame, f"step_{i}", new_lv))
            if new_lv > lv:
                log.append({"tag": "CLEARED", "step": i, "levels": new_lv})
                _write_report(log, "CLEARED")
                print(f">>> CLEARED at step {i}: levels {lv} -> {new_lv}")
                return 0
        log.append({"tag": "not_cleared", "levels": int(meta.get("levels_completed") or 0)})
        _write_report(log, "NOT_CLEARED")
        print(">>> NOT cleared after full L1/L2 flow post-dissolve")
        return 1
    finally:
        sess.close()


def _write_report(log, verdict) -> None:
    lines = [
        "# ls20 L3 legend flip -> L1/L2 clear 流程（E8）报告",
        "",
        "> 脚本：`tools/ls20_l3_legend_flip_clear_probe.py`",
        "> 性质：设计期探路（最小动作 + 比对 levels），非运行时求解器",
        "",
        "---",
        "",
        "## 结论",
        "",
        f"**{verdict}**",
        "",
        "## 逐步",
        "",
    ]
    for d in log:
        lines.append(f"- `{d}`")
    lines += [
        "",
        "## 判读",
        "",
        "- `CLEARED`：legend flip（环溶解）后，L1/L2 流程使 levels 2→3 →",
        "  机制锁定：环溶解 = 前置「武装」步骤。",
        "- `NOT_CLEARED`：legend flip 后 L1/L2 流程仍不过 → 排除「legend flip",
        "  是缺失前置」假设，机制另找。",
        "- `PLAN_FAIL_AFTER_DISSOLVE`：溶解后 planner 找不到 contact/stamp 路径",
        "  （能量/可达性），本身即负结果。",
        "- `CLEARED_BY_DISSOLVE` / `CLEARED_DURING_WALK`：溶解或途中即过关。",
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
