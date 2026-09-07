"""Probe E4: after entering (5,9) dissolves the ring, what opens / how to clear?

CONTEXT (docs/ls20_l3_ring_interact_probe.md, E3)
  E3 found: (1) interact beside the ring is a no-op; (2) the "second gate" (5,9)
  is NOT armed-only — entering it succeeds unarmed; (3) entering (5,9) DISSOLVES
  the ring: second block -> None, color14 -> 0, color9 23->45 (the mover appears
  to absorb the ring).  Levels stayed 2.

  The ring dissolve looks like a PICKUP, not a clear. This probe continues from
  (5,9) after the dissolve and asks: did the stamp gate (10,10) open? is there
  now a path to the stamp block (H20)? does interact now do something?

USAGE
  python tools/ls20_l3_ring_entry_probe.py --plan-only
  python tools/ls20_l3_ring_entry_probe.py
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
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, _ov, _ov_stamp
from tools.ls20_l3_armed_controller import reach_l3
from tools.ls20_second_block_probe import main_mover_and_second
from tools.ls20_l3_ring_interact_probe import _ring_bbox, _ring_colors, _snapshot

FIXTURE = ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json"
REPORT = ROOT / "docs" / "ls20_l3_ring_entry_probe.md"

INTERACT = 5
POINT = (4, 9)      # ring-left adjacent
GATE = (5, 9)       # enter this to dissolve the ring (one RIGHT from POINT)


def _stamp_gate_cells(frame, offset, walk_a, stamp):
    return sorted(
        c for c in walk_a if _ov_stamp(c, offset, stamp) >= 10
    )


def plan_e4(frame):
    """Offline plan for the PRE-dissolve legs (to POINT then GATE)."""
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    stamp = next((g.shape for g in state.goals if g.id == "ls20-stamp"), None)
    if stamp is None:
        raise RuntimeError("no stamp goal")
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))
    p1, c1, f1, pm1 = _energy_bfs(
        state.cursor, fuel0, 0, walk_u, pickups, offset,
        lambda c, _f, _p: c == POINT, warps,
    )
    if p1 is None:
        raise RuntimeError("no path to POINT")
    return list(p1), stamp, offset, f1


def plan_only() -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    p1, stamp, offset, fuel = plan_e4(data["frame"])
    print(f"POINT={POINT} GATE={GATE}")
    print(f"stamp block = {stamp}")
    print(f"pre-dissolve path len = {len(p1)}  fuel_at_point={fuel}")
    print(f"actions = {[DIR_TO_ACTION[a] for a in p1]}")
    print("then RIGHT into (5,9) [dissolve], then re-init and explore")
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
        p1, stamp, offset, fuel = plan_e4(frame)
        print(f"POINT={POINT} GATE={GATE} path={len(p1)} fuel={fuel}")
        print(f"actions = {[DIR_TO_ACTION[a] for a in p1]}")

        log = []
        lv = int(meta.get("levels_completed") or 0)
        log.append({"step": 0, "action": "RESET", "levels": lv, **_snapshot(frame)})

        # phase 1: to POINT
        for i, a in enumerate(p1, 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            new_lv = int(meta.get("levels_completed") or 0)
            log.append({"step": i, "action": DIR_TO_ACTION[a], "levels": new_lv,
                        **_snapshot(frame)})
            if new_lv > lv:
                print(f"  >>> LEVEL UP during move")
                _write_report(log, "MOVES_CLEARED")
                return 0
        lv = int(meta.get("levels_completed") or 0)

        # phase 2: enter (5,9) -> dissolve ring
        resp = sess.action(DIR_TO_ACTION[(1, 0)])  # RIGHT
        frame, meta = resp["frame"], resp
        new_lv = int(meta.get("levels_completed") or 0)
        post = _snapshot(frame)
        log.append({"step": "DISSOLVE", "action": 4, "levels": new_lv, **post})
        print(f"  DISSOLVE: mover={post['mover']} ring={post['ring']} "
              f"c9={post['c9']} c14={post['c14']} lv={lv}->{new_lv}")
        if new_lv > lv:
            _write_report(log, "DISSOLVE_CLEARED")
            return 0

        # phase 3: re-init post-dissolve state and inspect what changed
        st = ls20.init(frame)
        off2 = ls20.grid_offset(frame)
        walk_u = ls20.build_walkable(frame, off2, armed=False)
        walk_a = ls20.build_walkable(frame, off2, armed=True)
        warps = ls20.detect_warps(frame, off2, walk_u)
        pickups = ls20.energy_pickups(frame)
        armed_only = sorted(walk_a - walk_u)
        stamp_now = next((g.shape for g in st.goals if g.id == "ls20-stamp"), None)
        stamp_gates = _stamp_gate_cells(frame, off2, walk_a, stamp_now) if stamp_now else []
        print(f"  POST-DISSOLVE: cursor={st.cursor} armed_only={armed_only}")
        print(f"    stamp_now={stamp_now} stamp_gates(armed)={stamp_gates}")
        print(f"    (10,10) in walk_u={ (10,10) in walk_u }  in walk_a={ (10,10) in walk_a }")

        # phase 4: can we now reach the stamp gate on armed walkable?
        cur = st.cursor
        ui = ls20.ui_energy(frame)
        fuel = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))
        if stamp_gates:
            p3, c3, f3, pm3 = _energy_bfs(
                cur, fuel, 0, walk_a, pickups, off2,
                lambda c, _f, _p: c in stamp_gates, warps,
            )
            print(f"    armed path cur->stamp_gate: "
                  f"{'len=' + str(len(p3)) + ' fuel=' + str(f3) if p3 else 'UNREACHABLE'}")
            if p3:
                for i, a in enumerate(p3, 1):
                    resp = sess.action(DIR_TO_ACTION[a])
                    frame, meta = resp["frame"], resp
                    new_lv = int(meta.get("levels_completed") or 0)
                    snap = _snapshot(frame)
                    log.append({"step": f"post{i}", "action": DIR_TO_ACTION[a],
                                "levels": new_lv, **snap})
                    print(f"    post{i:02d} A{DIR_TO_ACTION[a]} "
                          f"mover={snap['mover']} lv={new_lv}")
                    if new_lv > lv:
                        print(f"  >>> LEVEL UP {lv}->{new_lv}")
                        _write_report(log, "RING_THEN_STAMP_CLEARED")
                        return 0
        # phase 5: try interact at the dissolved spot
        before = _snapshot(frame)
        resp = sess.action(INTERACT)
        frame, meta = resp["frame"], resp
        new_lv = int(meta.get("levels_completed") or 0)
        after = _snapshot(frame)
        log.append({"step": "INTERACT", "action": 5, "levels": new_lv, **after})
        changed = {k: (before[k], after[k]) for k in before if before[k] != after[k]}
        print(f"  INTERACT@dissolved: lv={lv}->{new_lv} changed={sorted(changed)}")
        if new_lv > lv:
            _write_report(log, "INTERACT_CLEARED")
            return 0
        _write_report(log, "STILL_BLOCKED")
        return 1
    finally:
        sess.close()


def _write_report(log, verdict) -> None:
    lines = [
        "# ls20 L3 进入环后探索（E4）报告",
        "",
        "> 脚本：`tools/ls20_l3_ring_entry_probe.py`",
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
    for r in log:
        lines.append(f"- `{r}`")
    lines += [
        "",
        "## 判读",
        "",
        "- `MOVES_CLEARED`：移动本身过关。",
        "- `DISSOLVE_CLEARED`：进入 `(5,9)` 溶解环即过关。",
        "- `RING_THEN_STAMP_CLEARED`：溶解环后 stamp 门开，进 stamp 过关。",
        "- `INTERACT_CLEARED`：溶解环后 interact 过关。",
        "- `STILL_BLOCKED`：溶解环后仍未过关，需要继续探测。",
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
