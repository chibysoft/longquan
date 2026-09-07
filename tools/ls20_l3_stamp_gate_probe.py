"""Probe E6: is L3's stamp gate (10,10) a HARD color-9 gate or SOFT paint?

CONTEXT
  L1's stamp gate (6,2) is armed-only in the model (mover footprint overlaps the
  color-9 glyph A embedded in the color-5 stamp block) yet L1 SOLVES — so in L1
  that color-9 is SOFT (the mover walks over it into the stamp). C1/C2 reported
  L3 "BLOCKED (no level-up)" after walking the ARMED path into (10,10), but that
  verdict does not distinguish:
    (a) the engine refused the move into (10,10) (HARD gate), vs
    (b) the mover entered (10,10) but the level did not clear (wrong stamp mech).
  This probe reaches (10,9) unarmed, then steps DOWN once and records the mover
  bbox + levels to decide (a) vs (b). It also, on block, tries INTERACT at the
  gate and an approach from the bottom (10,11) as cheap follow-ups.

USAGE
  python tools/ls20_l3_stamp_gate_probe.py --plan-only
  python tools/ls20_l3_stamp_gate_probe.py
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
REPORT = ROOT / "docs" / "ls20_l3_stamp_gate_probe.md"

ABOVE = (10, 9)   # unarmed-walkable cell just above the stamp gate
GATE = (10, 10)   # armed-only cell overlapping the color-9 glyph C


def _snapshot(frame, tag):
    g = ls20._plane(frame)
    return {
        "tag": tag,
        "mover": ls20.locate_mover(frame),
        "carrying": ls20.carrying_near_mover(frame, ls20.locate_mover(frame)),
        "c9": int((g == 9).sum()),
        "c12": int((g == 12).sum()),
        "c14": int((g == 14).sum()),
    }


def _path_to(sess, frame, target):
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))
    p, _, _, _ = _energy_bfs(
        state.cursor, fuel0, 0, walk_u, pickups, offset,
        lambda c, _f, _p: c == target, warps,
    )
    return p


def plan_only() -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    frame = data["frame"]
    p = _path_to(None, frame, ABOVE)
    print(f"ABOVE={ABOVE} GATE={GATE}")
    print(f"path to ABOVE len={None if p is None else len(p)}")
    if p:
        print(f"actions = {[DIR_TO_ACTION[a] for a in p]}")
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    print(f"(10,9) in walk_u={ABOVE in walk_u}  (10,10) in walk_u={GATE in walk_u} "
          f"in walk_a={GATE in walk_a}")
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
        p = _path_to(sess, frame, ABOVE)
        if p is None:
            raise RuntimeError(f"no unarmed path to {ABOVE}")

        log = [_snapshot(frame, "start")]
        print(f"walking {len(p)} steps to {ABOVE}")
        for i, a in enumerate(p, 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            new_lv = int(meta.get("levels_completed") or 0)
            if new_lv > lv:
                log.append(_snapshot(frame, "LEVEL_UP_DURING_MOVE"))
                print(f"  >>> LEVEL UP during move step {i}")
                _write_report(log, "MOVES_CLEARED")
                return 0
        mover = ls20.locate_mover(frame)
        log.append(_snapshot(frame, "at_ABOVE"))
        print(f"at ABOVE mover={mover} levels={int(meta.get('levels_completed') or 0)}")

        # decisive step: DOWN into the gate
        resp = sess.action(DIR_TO_ACTION[(0, 1)])  # DOWN
        frame, meta = resp["frame"], resp
        new_lv = int(meta.get("levels_completed") or 0)
        mover_after = ls20.locate_mover(frame)
        log.append(_snapshot(frame, "after_DOWN_into_gate"))
        entered = mover_after != mover
        print(f"  DOWN into GATE: entered={entered} mover_before={mover} "
              f"mover_after={mover_after} levels={new_lv}")
        if new_lv > lv:
            _write_report(log, "GATE_ENTERED_AND_CLEARED")
            return 0
        if entered:
            # entered but no clear -> stamp mech needs more
            _write_report(log, "GATE_SOFT_ENTERED_NO_CLEAR")
            return 1

        # blocked -> hard gate. cheap follow-ups.
        log.append(_snapshot(frame, "gate_blocked"))
        print("  gate HARD. follow-ups:")

        resp = sess.action(5)  # INTERACT at the gate
        frame, meta = resp["frame"], resp
        log.append(_snapshot(frame, "interact_at_gate"))
        print(f"  INTERACT levels={int(meta.get('levels_completed') or 0)} "
              f"mover={ls20.locate_mover(frame)}")

        _write_report(log, "GATE_HARD_BLOCKED")
        return 1
    finally:
        sess.close()


def _write_report(log, verdict) -> None:
    lines = [
        "# ls20 L3 盖印门硬/软判定（E6）报告",
        "",
        "> 脚本：`tools/ls20_l3_stamp_gate_probe.py`",
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
        "- `GATE_ENTERED_AND_CLEARED`：进 (10,10) 即过关（盖印机制与 L1 同，无武装概念）。",
        "- `GATE_SOFT_ENTERED_NO_CLEAR`：能进 (10,10) 但不过关（色9 是软漆；盖印还需其它）。",
        "- `GATE_HARD_BLOCKED`：进不了 (10,10)（色9 门是硬的，武装判据仍未找到）。",
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
