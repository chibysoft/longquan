"""Probe E3: does ACTION5 (interact) at the SECOND BLOCK ring arm L3?

CONTEXT (docs/ls20_l3_hline_second_gate_probe.md + ls20_l3_arming_deadlock.md)
  E1 tested interact at the PLUS marker (mover OVERLAP) -> pure no-op. But the
  second block ring (30,46)-(32,48) is the one L3-unique structure whose
  interact was NEVER tested, and it is the only structure the mover can ADJOIN
  (not overlap) while unarmed:

        9  14 14
        9   0  8      <- ring, center color-0 at (31,47)
       12  12  8

  The mover's 5px grid puts its footprint rows at ..45-46, 50-51.., so it can
  never sit ON the ring (y47). But unarmed it CAN stand 1px beside the ring at
  dist-2 cells (4,9) [left], (6,9) [right], (5,10) [below]. From any of these,
  the armed-only second gate (5,9) is exactly ONE step toward the ring:

        (4,9) ->RIGHT-> (5,9)      (6,9) ->LEFT-> (5,9)      (5,10) ->UP-> (5,9)

  So E3 = stand beside the ring -> INTERACT -> observe. If interact opens the
  color-9 gate, the one-step probe into (5,9) succeeds and levels may go 2->3.

USAGE
  python tools/ls20_l3_ring_interact_probe.py --plan-only
  python tools/ls20_l3_ring_interact_probe.py                 # default point (4,9)
  python tools/ls20_l3_ring_interact_probe.py --point 6,9     # ring right
  python tools/ls20_l3_ring_interact_probe.py --point 5,10    # ring below
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
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, _ov
from tools.ls20_l3_armed_controller import reach_l3
from tools.ls20_second_block_probe import main_mover_and_second
from tools.ls20_second_gate_probe import second_gate_cells

FIXTURE = ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json"
REPORT = ROOT / "docs" / "ls20_l3_ring_interact_probe.md"

INTERACT = 5  # ACTION5

# unarmed-reachable cells 1px beside the ring, with the direction to the gate.
# (each verified offline: dist=2 to ring, unarmed walkable, energy-feasible)
RING_POINTS = {
    (4, 9): (1, 0),     # ring-left   -> second gate (5,9) is RIGHT
    (6, 9): (-1, 0),    # ring-right  -> second gate (5,9) is LEFT
    (5, 10): (0, -1),   # ring-below  -> second gate (5,9) is UP
}


def _ring_bbox(frame):
    """Full 3x3 second-block ring bbox (30,46)-(32,48), from the non-mover
    color-12 blob's bottom-left anchor. (second_block() returns only x<=31.)"""
    _, seconds = main_mover_and_second(frame)
    if not seconds:
        return None
    x0, y0, x1, y1 = seconds[0]
    return (x0, y0 - 2, x0 + 2, y1)


def _ring_colors(frame, ring):
    """The ring's 9 pixel colors, row-major — the structural fingerprint."""
    g = ls20._plane(frame)
    x0, y0, x1, y1 = ring
    return [int(g[y, x]) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]


def _snapshot(frame) -> dict:
    g = ls20._plane(frame)
    mover = ls20.locate_mover(frame)
    _, seconds = main_mover_and_second(frame)
    second = seconds[0] if seconds else None
    ring = _ring_bbox(frame)
    return {
        "mover": mover, "second": second, "ring": ring,
        "ring_colors": _ring_colors(frame, ring) if ring else None,
        "c9": int((g == 9).sum()), "c14": int((g == 14).sum()),
        "c11": int((g == 11).sum()), "c0": int((g == 0).sum()),
        "c8": int((g == 8).sum()), "c12": int((g == 12).sum()),
        "layers": np.asarray(frame).shape[0] if np.asarray(frame).ndim == 3 else 1,
    }


def plan_e3(frame, point):
    """Energy-aware plan: start -> ring-adjacent point -> (gate = one step to ring)."""
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    ring = _ring_bbox(frame)
    if ring is None:
        raise RuntimeError("no second-block ring")
    gates = second_gate_cells(frame, offset, walk_a, walk_u)
    if not gates:
        raise RuntimeError("no second gate cell")
    gate = gates[0]
    if point not in walk_u:
        raise RuntimeError(f"interact point {point} not unarmed-walkable")

    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))

    p1, c1, f1, pm1 = _energy_bfs(
        state.cursor, fuel0, 0, walk_u, pickups, offset,
        lambda c, _f, _p: c == point, warps,
    )
    if p1 is None:
        raise RuntimeError(f"interact point {point} energy-unreachable")

    return (
        list(p1), point, gate,
        {
            "ring": ring, "gate": gate, "offset": offset,
            "fuel0": fuel0, "fuel_at_point": f1,
            "ring_colors0": _ring_colors(frame, ring),
            "dir_to_gate": RING_POINTS[point],
        },
    )


def plan_only(point) -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    frame = data["frame"]
    p1, point, gate, info = plan_e3(frame, point)
    print(f"interact point = {point}")
    print(f"second gate    = {gate}  (one step {info['dir_to_gate']} from point)")
    print(f"ring           = {info['ring']}")
    print(f"ring colors    = {info['ring_colors0']}")
    print(f"path len       = {len(p1)}  fuel_at_point={info['fuel_at_point']}")
    print(f"move actions   = {[DIR_TO_ACTION[a] for a in p1]}")
    print(f"then INTERACT at {point}, then step {info['dir_to_gate']} into gate")
    return 0


def run_online(point) -> int:
    key = _api_key()
    if not key:
        raise RuntimeError("no ARC_API_KEY")
    sess = OnlineSession(key)
    try:
        frame, meta = reach_l3(sess)
        print(f"reached L3 levels={meta.get('levels_completed')} "
              f"mover={ls20.locate_mover(frame)}")
        p1, point, gate, info = plan_e3(frame, point)
        print(f"point={point} gate={gate} dir={info['dir_to_gate']} "
              f"path_len={len(p1)}")
        print(f"move actions = {[DIR_TO_ACTION[a] for a in p1]}")

        log = []
        lv = int(meta.get("levels_completed") or 0)
        log.append({"step": 0, "action": "RESET", "levels": lv, **_snapshot(frame)})

        # phase 1: move to the ring-adjacent point
        for i, a in enumerate(p1, 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            new_lv = int(meta.get("levels_completed") or 0)
            log.append({"step": i, "action": DIR_TO_ACTION[a], "levels": new_lv,
                        **_snapshot(frame)})
            print(f"  {i:02d} A{DIR_TO_ACTION[a]} mover={ls20.locate_mover(frame)} "
                  f"lv={new_lv}")
            if new_lv > lv:
                print(f"  >>> LEVEL UP {lv}->{new_lv} during move phase")
                _write_report(log, "MOVES_ALONE_CLEARED", point, gate, info)
                return 0
        lv = int(meta.get("levels_completed") or 0)

        # phase 2: INTERACT beside the ring
        before = _snapshot(frame)
        resp = sess.action(INTERACT)
        frame, meta = resp["frame"], resp
        new_lv = int(meta.get("levels_completed") or 0)
        after = _snapshot(frame)
        log.append({"step": "INTERACT", "action": 5, "levels": new_lv, **after})
        changed = {k: (before[k], after[k]) for k in before if before[k] != after[k]}
        print(f"  INTERACT: lv={lv}->{new_lv}  frame_changed_keys={sorted(changed)}")
        if new_lv > lv:
            print(f"  >>> LEVEL UP {lv}->{new_lv} ON INTERACT")
            _write_report(log, "INTERACT_CLEARED", point, gate, info)
            return 0

        # phase 3: one step toward the ring (into second gate (5,9))
        #   if interact armed us (color-9 gate open), this step succeeds.
        dir_a = DIR_TO_ACTION[info["dir_to_gate"]]
        resp = sess.action(dir_a)
        frame, meta = resp["frame"], resp
        new_lv = int(meta.get("levels_completed") or 0)
        step_snap = _snapshot(frame)
        log.append({"step": "INTO_GATE", "action": dir_a, "levels": new_lv,
                    **step_snap})
        moved = step_snap["mover"] != before["mover"]
        print(f"  INTO_GATE A{dir_a}: moved={moved} mover={step_snap['mover']} "
              f"lv={lv}->{new_lv}")
        if new_lv > lv:
            print(f"  >>> LEVEL UP {lv}->{new_lv} on gate entry")
            _write_report(log, "INTERACT_ARMED_CLEARED", point, gate, info)
            return 0
        if moved:
            _write_report(log, "INTERACT_OPENED_GATE", point, gate, info)
            return 0
        _write_report(log, "INTERACT_NOOP_BLOCKED", point, gate, info)
        return 1
    finally:
        sess.close()


def _write_report(log, verdict, point, gate, info) -> None:
    lines = [
        "# ls20 L3 第二块环 interact 探针（E3）报告",
        "",
        "> 脚本：`tools/ls20_l3_ring_interact_probe.py`",
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
        f"| interact 点 | `{point}` |",
        f"| 第二块门 | `{gate}` |",
        f"| 环 | `{info['ring']}` |",
        f"| 环初始指纹 | `{info['ring_colors0']}` |",
        f"| 向门方向 | `{info['dir_to_gate']}` |",
        f"| fuel_at_point | {info['fuel_at_point']} |",
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
        "- `MOVES_ALONE_CLEARED`：移动到环旁本身触发过关。",
        "- `INTERACT_CLEARED`：interact 直接 levels+1（环处 interact 是过关机制）。",
        "- `INTERACT_ARMED_CLEARED`：interact 开门且进 `(5,9)` 后过关（interact=武装）。",
        "- `INTERACT_OPENED_GATE`：interact 打开了色9 门（能进 `(5,9)`）但未立即过关。",
        "- `INTERACT_NOOP_BLOCKED`：interact 无效果，门未开，候选1 证伪。",
        "",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--point", default="4,9", help="ring-adjacent cell x,y")
    args = ap.parse_args()
    point = tuple(int(v) for v in args.point.split(","))
    if point not in RING_POINTS:
        raise SystemExit(f"--point must be one of {sorted(RING_POINTS)}")
    if args.plan_only:
        return plan_only(point)
    return run_online(point)


if __name__ == "__main__":
    raise SystemExit(main())
