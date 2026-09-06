"""Probe: is L3's real goal the SECOND 3x3 block (via armed-only cell (5,9)),
not the stamp block (via (10,10))?

CONTEXT (see docs/ls20_l3_armed_controller.md, L3 arming experiments):
  L3 has TWO armed-only cells (walk_a - walk_u):
    (10,10) pixel(54,50): the color-9 it clears sits INSIDE the color-5 stamp
            block (55,51)/(57,51); stamp_ov=10 (exactly the seated threshold).
    (5,9)   pixel(29,45): the color-9 it clears is (30,46) — the top-left pixel
            of a SECOND 3x3 structure, NOT the stamp block; stamp_ov=0.

  That second 3x3 block (30,46)-(32,48) is:
       9  14 14
       9   0  8      <- color 0 at center (31,47), unknown colors 14 and 8
      12  12  8
  It is NOT the stamp (color 5), NOT the marker (init drops its lone color-0 as
  area=1 < 3), NOT the main mover (it's a 2px color-12 blob). Yet a mover
  standing at (5,9) covers it ENTIRELY: mover(29..33,45..46) + carrying
  (29..33,47..49) vs block (30..32,46..48).

  The prior probes (C1/C2) only ever tried "contact plus -> (10,10) stamp gate".
  This probe tests the OTHER armed-only gate: "contact plus -> (5,9) -> cover the
  second block". If levels 2->3, L3's real goal is the second block, not stamp.

Usage:
  python tools/ls20_second_gate_probe.py --plan-only
  python tools/ls20_second_gate_probe.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
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
    MAX_FUEL, _energy_bfs, _ov, _step_cell,
)
from tools.ls20_l3_armed_controller import reach_l3
from tools.ls20_second_block_probe import all_color12, main_mover_and_second

FIXTURE = ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json"
RITUAL = ((0, -1), (0, 1), (0, 1))  # H23 UP, DOWN, DOWN


def second_block(frame):
    """The non-mover color-12 blob's 3x3 neighborhood, as a pixel bbox.

    The second blob is 2px at (30,48)-(31,48); its parent structure is the 3x3
    block (30,46)-(32,48). Return that 3x3 bbox for overlap checks.
    """
    main, seconds = main_mover_and_second(frame)
    if not seconds:
        return None
    x0, y0, x1, y1 = seconds[0]
    # the color-9 sits ABOVE the 12, so the structure spans y0-2 .. y1
    return (x0 - 0, y0 - 2, x0 + 1, y1)


def second_gate_cells(frame, offset, walk_a, walk_u):
    """Armed-only cells whose mover+carrying footprint overlaps the second block."""
    blk = second_block(frame)
    if blk is None:
        return []
    out = []
    for c in (walk_a - walk_u):
        mb = mover_bbox_from_cursor(c, offset)
        cb = carrying_bbox_from_cursor(c, offset)
        if _ov(mb, blk) > 0 or _ov(cb, blk) > 0:
            out.append(c)
    return sorted(out)


def plan_second_gate(frame):
    """Energy-aware path: start -> contact plus -> UDD -> cover second block."""
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    marker = next((g.shape for g in state.goals if g.id == "ls20-marker"), None)
    if marker is None:
        raise RuntimeError("no marker")
    blk = second_block(frame)
    gates = second_gate_cells(frame, offset, walk_a, walk_u)
    if not gates:
        raise RuntimeError(f"no second-gate cell; second block={blk}")

    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))

    def at_contact(cell, _f, _p):
        return _ov(carrying_bbox_from_cursor(cell, offset), marker) > 0

    p1, c1, f1, pm1 = _energy_bfs(
        state.cursor, fuel0, 0, walk_u, pickups, offset, at_contact, warps,
    )
    if p1 is None:
        raise RuntimeError("no path to plus contact")
    path: List[Tuple[int, int]] = list(p1)
    cur, fuel, pmask = c1, f1, pm1

    # H23 ritual at contact (matches C2 baseline)
    for d in RITUAL:
        nxt = _step_cell(cur, d, walk_u, warps)
        if nxt is None:
            raise RuntimeError(f"ritual {d} blocked at {cur}")
        from tools.ls20_seated_clear import _pickup_mask
        n_mask, refilled = _pickup_mask(nxt, offset, pickups, pmask)
        if fuel <= 0 and not refilled:
            raise RuntimeError("ritual out of fuel")
        fuel = MAX_FUEL if refilled else fuel - 1
        cur, pmask = nxt, n_mask
        path.append(d)

    # go cover the second block via its armed-only gate
    gate = gates[0]
    p2, _c2, _f2, _pm2 = _energy_bfs(
        cur, fuel, pmask, walk_a, pickups, offset, lambda c, _f, _p: c == gate, warps,
    )
    if p2 is None:
        raise RuntimeError(f"second gate {gate} unreachable from {cur}")
    path.extend(p2)

    return path, {"gate": gate, "second_block": blk, "contact": c1, "marker": marker}


def plan_only() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    frame = data["frame"]
    offset = ls20.grid_offset(frame)
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    blk = second_block(frame)
    gates = second_gate_cells(frame, offset, walk_a, walk_u)
    print(f"second block   = {blk}")
    print(f"second gates   = {gates}")
    try:
        path, info = plan_second_gate(frame)
        print(f"gate           = {info['gate']}  second_block={info['second_block']}")
        print(f"contact        = {info['contact']}")
        print(f"path len       = {len(path)}")
        print(f"actions        = {[DIR_TO_ACTION[a] for a in path]}")
    except RuntimeError as e:
        print(f"PLAN RESULT: second gate UNREACHABLE under energy budget: {e}")
        print("=> second-block gate (5,9) is energy-infeasible from the plus-contact")
        print("   ritual: pickups all sit in the UPPER half, both gates in the LOWER")


def probe_online() -> dict:
    key = _api_key()
    if not key:
        raise RuntimeError("no ARC_API_KEY")
    sess = OnlineSession(key)
    try:
        frame, meta = reach_l3(sess)
        print(f"reached L3 levels={meta.get('levels_completed')}")
        path, info = plan_second_gate(frame)
        print(f"gate={info['gate']} second={info['second_block']} len={len(path)}")
        print(f"actions={[DIR_TO_ACTION[a] for a in path]}")

        log = []
        leveled = False
        for i, a in enumerate(path, 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            lv = int(meta.get("levels_completed") or 0)
            mover = ls20.locate_mover(frame)
            _, seconds = main_mover_and_second(frame)
            arr = np.asarray(frame)
            layers = arr.shape[0] if arr.ndim == 3 else 1
            print(f"  {i:02d} A{DIR_TO_ACTION[a]} mover={mover} second={seconds} "
                  f"layers={layers} lv={lv}")
            log.append({"step": i, "action": DIR_TO_ACTION[a], "mover": mover,
                        "second": seconds, "layers": layers, "levels": lv})
            if lv > 2:
                leveled = True
                print(f"  >>> LEVEL UP 2->{lv} at step {i}")
                break
        verdict = "CLEARED" if leveled else "BLOCKED"
        print(f"VERDICT: second-gate {verdict}")
        return {"verdict": verdict, "gate": info["gate"],
                "second_block": info["second_block"], "log": log}
    finally:
        sess.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-only", action="store_true")
    args = ap.parse_args()
    if args.plan_only:
        plan_only()
        return 0
    probe_online()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
