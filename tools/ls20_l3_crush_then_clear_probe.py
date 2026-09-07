"""Probe E10b: crush ring (legend flip) -> full L1/L2 clear, with pre-crush fuel.

WHY
  E10 (crush -> gate) failed on a FUEL confound, not a mechanism result: the
  17-step crush path to (5,9) avoided both pickups, leaving the mover at
  fuel=1. plan_two_phase on the dissolved frame then had no energy to even
  reach a pickup, so it raised "no path to marker contact".

  Offline reachability from the dissolved fixture (ls20_l3_frame_dissolved.json)
  with high fuel PROVES the full flow is geometrically reachable:
    contact (9,2)  = 13 steps
    UDD ritual     = ok, ends (9,3)
    armed to (10,10) = 4 steps
  So the ONLY blocker was fuel. E10b removes it by collecting a pickup FIRST
  (refill to full), THEN crushing the ring, THEN running the full flow.

  This is the decisive test of the user's E8 hypothesis: legend flip is the
  arming step that opens the stamp gate (10,10). CLEARED -> hypothesis locked;
  NOT_CLEARED -> legend flip eliminated as the missing prerequisite.

FLOW
  1. reach_l3 (clears L1+L2, stops at L3, mover (1,8))
  2. collect a pickup (energy-aware BFS to nearest pickup cell)
  3. crush ring (BFS to (4,9), then RIGHT into (5,9))
  4. plan_two_phase on the dissolved frame (contact -> ritual -> armed walk)
  5. execute, watching levels 2 -> 3

USAGE
  python tools/ls20_l3_crush_then_clear_probe.py --plan-only
  python tools/ls20_l3_crush_then_clear_probe.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import carrying_bbox_from_cursor, mover_bbox_from_cursor
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import (
    MAX_FUEL, _energy_bfs, _ov, _ov_stamp, _step_cell, plan_two_phase,
)
from tools.ls20_l3_armed_controller import reach_l3

REPORT = ROOT / "docs" / "ls20_l3_crush_then_clear_probe.md"
FIXTURE_LIVE = ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json"

RING_LEFT = (4, 9)   # walkable cell immediately left of the ring
RING = (5, 9)        # RIGHT from (4,9) enters and crushes the ring


def _fuel0(frame):
    ui = ls20.ui_energy(frame)
    return MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))


def _plan_to_pickup(frame):
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    fuel0 = _fuel0(frame)

    def at_pickup(cell, _f, _p):
        return any(_ov(mover_bbox_from_cursor(cell, offset), pb) > 0 for pb in pickups)

    p, c, f, pm = _energy_bfs(state.cursor, fuel0, 0, walk_u, pickups, offset,
                              at_pickup, warps)
    return p, c


def _plan_to_ring(frame):
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    fuel0 = _fuel0(frame)

    def at_point(cell, _f, _p):
        return cell == RING_LEFT

    p, c, f, pm = _energy_bfs(state.cursor, fuel0, 0, walk_u, pickups, offset,
                              at_point, warps)
    return p, c


def _snap(frame, tag, levels):
    g = ls20._plane(frame)
    arr = np.asarray(frame)
    return {
        "tag": tag, "levels": levels, "mover": ls20.locate_mover(frame),
        "layers": arr.shape[0] if arr.ndim == 3 else 1,
        "c9": int((g == 9).sum()), "c12": int((g == 12).sum()),
        "c11": int((g == 11).sum()), "ui": ls20.ui_energy(frame),
    }


def _execute(sess, path, lv, log, tag):
    """Send `path`; record each step; return (frame, cleared)."""
    frame = None
    for i, a in enumerate(path, 1):
        resp = sess.action(DIR_TO_ACTION[a])
        frame = resp["frame"]
        nl = int(resp.get("levels_completed") or 0)
        log.append({
            "tag": tag, "step": i, "action": DIR_TO_ACTION[a],
            "mover": ls20.locate_mover(frame), "levels": nl,
            "ui": ls20.ui_energy(frame),
        })
        if nl > lv:
            return frame, True
    return frame, False


def plan_only() -> int:
    data = json.loads(FIXTURE_LIVE.read_text(encoding="utf-8"))
    frame = np.asarray(data["frame"], dtype=np.int8)
    p, c = _plan_to_pickup(frame)
    print(f"pickup plan: len={None if p is None else len(p)} end={c}")
    if p:
        print(f"  actions={[DIR_TO_ACTION[a] for a in p]}")
    p2, c2 = _plan_to_ring(frame)
    print(f"ring plan:   len={None if p2 is None else len(p2)} end={c2}")
    if p2:
        print(f"  actions={[DIR_TO_ACTION[a] for a in p2]}")
    return 0


def run_online() -> int:
    key = _api_key()
    if not key:
        raise RuntimeError("ARC_API_KEY not found")
    sess = OnlineSession(key)
    try:
        frame, meta = reach_l3(sess)
        lv = int(meta.get("levels_completed") or 0)
        log = [_snap(frame, "l3_start", lv)]
        print(f"L3 start: levels={lv} mover={ls20.locate_mover(frame)} "
              f"ui={ls20.ui_energy(frame)}")

        # --- Phase 2: collect a pickup (refill to full) ---
        p, c = _plan_to_pickup(frame)
        if p is None:
            raise RuntimeError("no path to pickup")
        print(f"pickup plan: len={len(p)} end={c}")
        frame, cleared = _execute(sess, p, lv, log, "pickup")
        if cleared:
            _write_report(log, "CLEARED")
            return 0
        log.append(_snap(frame, "post_pickup", lv))
        print(f"post-pickup: mover={ls20.locate_mover(frame)} ui={ls20.ui_energy(frame)}")

        # --- Phase 3: crush the ring ---
        p2, c2 = _plan_to_ring(frame)
        if p2 is None:
            raise RuntimeError(f"no path to ring-left {RING_LEFT}")
        print(f"ring plan: len={len(p2)} end={c2}")
        frame, cleared = _execute(sess, p2, lv, log, "to_ring")
        if cleared:
            _write_report(log, "CLEARED")
            return 0
        resp = sess.action(DIR_TO_ACTION[(1, 0)])  # RIGHT into (5,9) -> crush
        frame = resp["frame"]
        nl = int(resp.get("levels_completed") or 0)
        log.append(_snap(frame, "post_crush", nl))
        print(f"post-crush: mover={ls20.locate_mover(frame)} "
              f"ui={ls20.ui_energy(frame)} c9={log[-1]['c9']} c12={log[-1]['c12']}")
        if nl > lv:
            _write_report(log, "CLEARED_BY_CRUSH")
            return 0

        # --- Phase 4: full L1/L2 clear flow on the dissolved frame ---
        try:
            path, info = plan_two_phase(frame)
        except RuntimeError as ex:
            log.append({"tag": "plan_fail_after_crush", "error": str(ex),
                        "levels": nl})
            _write_report(log, "PLAN_FAIL_AFTER_CRUSH")
            print(f"plan_two_phase FAIL: {ex}")
            return 1
        print(f"plan_two_phase: len={len(path)} ritual={info.get('ritual')} "
              f"fuel0={info.get('fuel0')} fuel_end={info.get('fuel_end')} "
              f"t2={info.get('t2')}")
        log.append({"tag": "plan", "info": info,
                    "actions": [DIR_TO_ACTION[a] for a in path]})

        frame, cleared = _execute(sess, path, lv, log, "clear")
        if cleared:
            _write_report(log, "CLEARED")
            print(">>> CLEARED: legend flip + full flow -> levels 2->3")
            return 0
        log.append({"tag": "not_cleared", "levels": lv})
        _write_report(log, "NOT_CLEARED")
        print(">>> NOT cleared after crush + full flow")
        return 1
    finally:
        sess.close()


def _write_report(log, verdict) -> None:
    lines = [
        "# ls20 L3 压环后完整流程（E10b）报告",
        "",
        "> 脚本：`tools/ls20_l3_crush_then_clear_probe.py`",
        "> 性质：设计期探路（先吃补给 → 压环 → 完整 L1/L2 流程 → 比对 levels）",
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
        "- `CLEARED`：legend flip（环溶解）+ 完整流程使 levels 2→3 → 机制锁定：",
        "  环溶解 = 前置「武装」步骤。",
        "- `NOT_CLEARED`：压环 + 完整流程仍不过 → 排除「legend flip 是缺失前置」",
        "  假设，机制转向字形族（rot180 仪式）或其它。",
        "- `PLAN_FAIL_AFTER_CRUSH`：压环后 planner 仍找不到完整路径（能量/可达性），",
        "  本身即负结果。",
        "- `CLEARED_BY_CRUSH`：压环本身即过关。",
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
