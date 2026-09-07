"""Probe E1: is ACTION5 (interact) the L3 arming mechanism?

CONTEXT (docs/ls20_l3_arming_deadlock.md)
  L3 = H19(arm) + H20(stamp) unchanged, but the ARMING criterion changed.
  C1/C2 proved "carrying overlaps plus -> (10,10)" does NOT arm on L3. The one
  primitive never tested on L3 is ACTION5 (interact) — on L1/L2 it is only a
  marker-clear side-effect (H5), never required for the clear.

  This probe tests the cheapest untested primitive: contact plus -> INTERACT ->
  observe. If interact arms (opens the color-9 gate), the mover should then be
  able to enter the stamp gate (10,10) and levels should go 2->3.

USAGE
  python tools/ls20_l3_interact_probe.py --plan-only   # offline, zero budget
  python tools/ls20_l3_interact_probe.py               # online (reach L3 + run)
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
from longquan.interactive.match import carrying_bbox_from_cursor
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import (
    MAX_FUEL, _energy_bfs, _ov, _ov_stamp, _pickup_mask, _step_cell,
)
from tools.ls20_l3_armed_controller import reach_l3
from tools.ls20_second_block_probe import main_mover_and_second

FIXTURE = ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json"
REPORT = ROOT / "docs" / "ls20_l3_interact_probe.md"

INTERACT = 5  # ACTION5, live-probed on L1/L2 as marker-clear side-effect


def _snapshot(frame) -> dict:
    """Key-structure digest of an L3 frame (no canned answers, all located)."""
    g = ls20._plane(frame)
    mover = ls20.locate_mover(frame)
    _, seconds = main_mover_and_second(frame)
    second = seconds[0] if seconds else None
    # color-9 gate pixels at the stamp block interior (the armed-only obstacle)
    c9 = int((g == 9).sum())
    c14 = int((g == 14).sum())
    c11 = int((g == 11).sum())
    layers = np.asarray(frame).shape[0] if np.asarray(frame).ndim == 3 else 1
    return {
        "mover": mover, "second": second, "c9": c9, "c14": c14, "c11": c11,
        "layers": layers,
    }


def plan_e1(frame):
    """Energy-aware plan: start -> plus contact -> INTERACT -> stamp gate (10,10).

    Returns (path_before_interact, contact_cell, stamp_gate, info). The stamp
    gate phase is planned on ARMED walkable (hypothesizing interact arms us).
    """
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    marker = next((g.shape for g in state.goals if g.id == "ls20-marker"), None)
    stamp = next((g.shape for g in state.goals if g.id == "ls20-stamp"), None)
    if marker is None or stamp is None:
        raise RuntimeError("missing marker/stamp goal")

    # contact cells (carrying overlaps marker) — the L2 arming gesture
    contacts = [
        c for c in walk_u
        if _ov(carrying_bbox_from_cursor(c, offset), marker) > 0
    ]
    if not contacts:
        raise RuntimeError("no plus contact cell")
    contact = contacts[0]

    # stamp gate = armed cell where mover footprint fully enters the color-5 block
    gates = sorted(
        c for c in walk_a if _ov_stamp(c, offset, stamp) >= 10
    )
    if not gates:
        raise RuntimeError("no stamp gate (ov>=10) on armed walkable")
    gate = gates[0]

    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))

    def at_contact(cell, _f, _p):
        return _ov(carrying_bbox_from_cursor(cell, offset), marker) > 0

    p1, c1, f1, pm1 = _energy_bfs(
        state.cursor, fuel0, 0, walk_u, pickups, offset, at_contact, warps,
    )
    if p1 is None:
        raise RuntimeError("no energy-aware path to plus contact")

    # post-interact: reach gate on armed walkable from the contact cell
    p2, c2, f2, pm2 = _energy_bfs(
        c1, f1, pm1, walk_a, pickups, offset,
        lambda c, _f, _p: _ov_stamp(c, offset, stamp) >= 10, warps,
    )
    if p2 is None:
        raise RuntimeError(f"stamp gate {gate} unreachable on armed walkable")

    return (
        list(p1), contact, gate,
        {
            "marker": marker, "stamp": stamp, "path1_len": len(p1),
            "path2_len": len(p2), "contact": c1, "gate": gate,
            "fuel0": fuel0, "fuel_after_contact": f1, "fuel_after_gate": f2,
            "pickups": pickups, "cursor0": state.cursor, "offset": offset,
        },
    )


def plan_only() -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    frame = data["frame"]
    p1, contact, gate, info = plan_e1(frame)
    print(f"contact = {contact}  gate = {gate}")
    print(f"marker = {info['marker']}  stamp = {info['stamp']}")
    print(f"path1_len = {info['path1_len']}  (to contact)")
    print(f"path2_len = {info['path2_len']}  (contact -> gate, armed)")
    print(f"fuel0={info['fuel0']}  after_contact={info['fuel_after_contact']}  "
          f"after_gate={info['fuel_after_gate']}")
    print(f"move actions (to contact) = {[DIR_TO_ACTION[a] for a in p1]}")
    print(f"then INTERACT at {contact}, then armed path to {gate}")
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
        p1, contact, gate, info = plan_e1(frame)
        print(f"contact={contact} gate={gate} path1_len={len(p1)} "
              f"path2_len={info['path2_len']}")
        print(f"move actions (to contact) = {[DIR_TO_ACTION[a] for a in p1]}")

        log = []
        lv = int(meta.get("levels_completed") or 0)
        log.append({"step": 0, "action": "RESET", "levels": lv,
                    **_snapshot(frame)})

        # phase 1: move to contact
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
                _write_report(log, "MOVES_ALONE_CLEARED", contact, gate, info)
                return 0
        lv = int(meta.get("levels_completed") or 0)

        # phase 2: INTERACT at the contact cell
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
            _write_report(log, "INTERACT_CLEARED", contact, gate, info)
            return 0

        # phase 3: attempt armed path to stamp gate (did interact arm us?)
        lv = int(meta.get("levels_completed") or 0)
        state = ls20.init(frame)
        offset = ls20.grid_offset(frame)
        walk_a = ls20.build_walkable(frame, offset, armed=True)
        stamp = info["stamp"]
        pickups = ls20.energy_pickups(frame)
        cur = state.cursor
        # recompute shortest armed path from current position to gate
        p2, c2, f2, pm2 = _energy_bfs(
            cur, MAX_FUEL, 0, walk_a, pickups, offset,
            lambda c, _f, _p: _ov_stamp(c, offset, stamp) >= 10,
            ls20.detect_warps(frame, offset, walk_a),
        )
        if p2 is None:
            print("  post-interact: no armed path to gate from current pos")
            _write_report(log, "BLOCKED_NO_ARMED_PATH", contact, gate, info)
            return 1
        for i, a in enumerate(p2, 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            new_lv = int(meta.get("levels_completed") or 0)
            log.append({"step": f"post{i}", "action": DIR_TO_ACTION[a],
                        "levels": new_lv, **_snapshot(frame)})
            print(f"  post{i:02d} A{DIR_TO_ACTION[a]} "
                  f"mover={ls20.locate_mover(frame)} lv={new_lv}")
            if new_lv > lv:
                print(f"  >>> LEVEL UP {lv}->{new_lv} after interact+move")
                _write_report(log, "INTERACT_ARMED_CLEARED", contact, gate, info)
                return 0
        _write_report(log, "BLOCKED", contact, gate, info)
        return 1
    finally:
        sess.close()


def _write_report(log, verdict, contact, gate, info) -> None:
    lines = [
        "# ls20 L3 interact 探针（E1）报告",
        "",
        "> 脚本：`tools/ls20_l3_interact_probe.py`",
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
        f"| contact | `{contact}` |",
        f"| stamp gate | `{gate}` |",
        f"| marker | `{info['marker']}` |",
        f"| stamp | `{info['stamp']}` |",
        f"| fuel0 | {info['fuel0']} |",
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
        "- `MOVES_ALONE_CLEARED`：移动本身触发，interact 冗余。",
        "- `INTERACT_CLEARED`：interact 直接触发 levels+1（interact 是 L3 武装/过关机制）。",
        "- `INTERACT_ARMED_CLEARED`：interact 打开色9门，随后盖印触发（interact=武装）。",
        "- `BLOCKED`：interact 无效果，候选1 证伪，转候选2/3。",
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
