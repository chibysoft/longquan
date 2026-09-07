"""Probe E6: walk through L3's stamp column and sweep actions at each cell.

WHY
  E4 proved the mover enters (5,9) OVER color9 while "unarmed" — so color9 is
  NOT a hard obstacle, and neither is color5 (L1 clears by walking over both).
  The real obstacle set is likely just {color4 walls}. That collapses the
  "arming opens a color9 gate" framework: (10,10) is not a gate, the mover can
  walk straight through the stamp block. C1/C2 "BLOCKED" only meant "no
  level-up", never checked whether the mover physically entered (10,10).

  This probe walks the stamp column (10,9)->(10,10)->(10,11)->(10,12) and, at
  each cell, snapshots the stamp block's color5 mask + levels + mover bbox to
  answer: which action (if any) changes the color5 solid or clears the level?

USAGE
  python tools/ls20_l3_stamp_sweep_probe.py --plan-only
  python tools/ls20_l3_stamp_sweep_probe.py
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
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs
from tools.ls20_l3_armed_controller import reach_l3

FIXTURE = ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json"
REPORT = ROOT / "docs" / "ls20_l3_stamp_sweep_probe.md"

ABOVE = (10, 9)      # unarmed-walkable cell just above the stamp block
COLUMN = [(10, 10), (10, 11), (10, 12)]  # stamp interior, below, below-that

# stamp window to fingerprint (a little larger than the 7x7 block to catch growth)
WIN = (50, 47, 61, 56)


def _stamp5_mask(frame):
    """Sorted list of color5 pixel coords inside the stamp window."""
    g = ls20._plane(frame)
    x0, y0, x1, y1 = WIN
    ys, xs = np.where(g[y0:y1 + 1, x0:x1 + 1] == 5)
    return sorted(zip((xs + x0).tolist(), (ys + y0).tolist()))


def _snapshot(frame, tag):
    g = ls20._plane(frame)
    arr = np.asarray(frame)
    hist = {int(v): int(c) for v, c in zip(*np.unique(g, return_counts=True))}
    return {
        "tag": tag,
        "levels": None,  # filled by caller
        "mover": ls20.locate_mover(frame),
        "carrying": ls20.carrying_near_mover(frame, ls20.locate_mover(frame)),
        "layers": arr.shape[0] if arr.ndim == 3 else 1,
        "c11": hist.get(11, 0),
        "stamp5": _stamp5_mask(frame),
        "stamp5_count": len(_stamp5_mask(frame)),
        "hist": hist,
    }


def _path_to(frame, target):
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


def plan_only() -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    frame = data["frame"]
    p = _path_to(frame, ABOVE)
    print(f"ABOVE={ABOVE} COLUMN={COLUMN}")
    print(f"path to ABOVE len={None if p is None else len(p)}")
    if p:
        print(f"actions = {[DIR_TO_ACTION[a] for a in p]}")
    snap = _snapshot(frame, "start")
    snap["levels"] = 2
    print(f"start stamp5_count={snap['stamp5_count']}")
    print(f"start stamp5 mask={snap['stamp5']}")
    return 0


def run_online() -> int:
    key = _api_key()
    if not key:
        raise RuntimeError("no ARC_API_KEY")
    sess = OnlineSession(key)
    try:
        frame, meta = reach_l3(sess)
        lv = int(meta.get("levels_completed") or 0)
        print(f"reached L3 levels={lv}")
        p = _path_to(frame, ABOVE)
        if p is None:
            raise RuntimeError(f"no path to {ABOVE}")

        log = []
        snap = _snapshot(frame, "start")
        snap["levels"] = lv
        log.append(snap)
        print(f"start: mover={snap['mover']} stamp5_count={snap['stamp5_count']}")

        # walk to ABOVE
        for i, a in enumerate(p, 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            new_lv = int(meta.get("levels_completed") or 0)
            if new_lv > lv:
                snap = _snapshot(frame, "LEVEL_UP_DURING_MOVE")
                snap["levels"] = new_lv
                log.append(snap)
                print(f"  >>> LEVEL UP during move step {i}")
                _write_report(log, "MOVES_CLEARED")
                return 0
        snap = _snapshot(frame, "at_ABOVE")
        snap["levels"] = int(meta.get("levels_completed") or 0)
        log.append(snap)
        print(f"at ABOVE: mover={snap['mover']} stamp5_count={snap['stamp5_count']}")

        # sweep: step DOWN through the stamp column, snapshot each
        for cell in COLUMN:
            before_mover = ls20.locate_mover(frame)
            resp = sess.action(DIR_TO_ACTION[(0, 1)])  # DOWN
            frame, meta = resp["frame"], resp
            new_lv = int(meta.get("levels_completed") or 0)
            after_mover = ls20.locate_mover(frame)
            entered = after_mover != before_mover
            snap = _snapshot(frame, f"after_DOWN_to_{cell}")
            snap["levels"] = new_lv
            log.append(snap)
            print(f"  DOWN->{cell}: entered={entered} mover={after_mover} "
                  f"lv={new_lv} stamp5_count={snap['stamp5_count']} "
                  f"c11={snap['c11']}")
            if new_lv > lv:
                _write_report(log, "STAMP_WALK_CLEARED")
                return 0

            # INTERACT at this cell
            resp = sess.action(5)  # INTERACT
            frame, meta = resp["frame"], resp
            new_lv = int(meta.get("levels_completed") or 0)
            snap = _snapshot(frame, f"interact_at_{cell}")
            snap["levels"] = new_lv
            log.append(snap)
            print(f"  INTERACT@{cell}: lv={new_lv} mover={ls20.locate_mover(frame)} "
                  f"stamp5_count={snap['stamp5_count']}")
            if new_lv > lv:
                _write_report(log, "INTERACT_CLEARED")
                return 0

        # detect any stamp5 change across the log
        base = log[0]["stamp5"]
        changed = [r for r in log[1:] if r["stamp5"] != base]
        if changed:
            _write_report(log, "STAMP_CHANGED")
            return 1
        _write_report(log, "STAMP_UNCHANGED")
        return 1
    finally:
        sess.close()


def _write_report(log, verdict) -> None:
    lines = [
        "# ls20 L3 盖印列扫掠（E6）报告",
        "",
        "> 脚本：`tools/ls20_l3_stamp_sweep_probe.py`",
        "> 性质：设计期探路（最小动作 + 比对 levels / color5 掩码），非运行时求解器",
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
        "- `STAMP_WALK_CLEARED`：走进盖印列（10,10 起）即过关（无需武装，色9/色5 皆可走）。",
        "- `INTERACT_CLEARED`：在盖印列某格 interact 过关。",
        "- `STAMP_CHANGED`：某动作使盖印块 color5 掩码变化（但未过关）。",
        "- `STAMP_UNCHANGED`：走完整列 + interact，color5 掩码不变 → 触发不在盖印门前。",
        "- `MOVES_CLEARED`：移动本身过关。",
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
