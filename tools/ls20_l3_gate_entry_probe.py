"""Probe E9: does the C2 ritual (contact + UP/DOWN/DOWN) ARM L3, physically?

WHY
  Offline geometry (E9-offline) shows the stamp color5 is WALKABLE: walk_u
  (unarmed) contains (10,11) ov=5, walk_a (armed) contains (10,10) ov=10.
  So E6's "hard block" at (10,10) was NOT color5 — it was the color9 glyph C
  embedded in the stamp, which blocks UNARMED movement. The mover was never
  armed in E6.

  C1/C2 and seated-clear all report "BLOCKED (no level-up)" but only ever
  checked `levels`, never whether the mover PHYSICALLY entered (10,10). Two
  mutually-exclusive explanations remain:
    (a) the ritual does NOT arm L3  -> mover stays blocked at (10,9) above;
    (b) the ritual DOES arm L3, the mover enters (10,10) (ov>=10), but the
        stamp mechanism still does not clear (different match material/orient).
  This probe executes the C2 path and records the mover bbox every step, so the
  single question "does the mover physically enter (10,10)?" is answered.

FLOW
  1. reach_l3
  2. plan_experiment(C2) = contact plus + UDD ritual + armed walk to gate
  3. execute, record mover bbox + levels each step, flag physical gate entry

USAGE
  python tools/ls20_l3_gate_entry_probe.py --plan-only
  python tools/ls20_l3_gate_entry_probe.py
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
from longquan.interactive.match import mover_bbox_from_cursor
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import _ov_stamp
from tools.ls20_l3_armed_controller import reach_l3, plan_experiment

REPORT = ROOT / "docs" / "ls20_l3_gate_entry_probe.md"

# (10,10) -> pixel (54,50); (10,9) -> pixel (54,45)  (offset (4,0))
GATE_PX = (54, 50, 58, 51)
ABOVE_PX = (54, 45, 58,46)


def plan_only() -> int:
    import json
    data = json.loads((ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json")
                      .read_text(encoding="utf-8"))
    frame = data["frame"]
    path, notes = plan_experiment(frame, "C2")
    offset = ls20.grid_offset(frame)
    stamp = notes["stamp"] if "stamp" in notes else None
    print(f"C2 path len={len(path)} contact={notes.get('contact')} "
          f"gate={notes.get('gate')}")
    print(f"actions={[DIR_TO_ACTION[a] for a in path]}")
    # simulate cursor to find where the mover is expected to end
    state = ls20.init(frame)
    cur = state.cursor
    warps = ls20.detect_warps(frame, offset, ls20.build_walkable(frame, offset, armed=False))
    from tools.ls20_seated_clear import _step_cell
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    # rough: just report expected gate pixel
    print(f"GATE_PX={GATE_PX} (ov_stamp would be {_ov_stamp((10,10), offset, (53,49,59,55))})")
    return 0


def run_online() -> int:
    key = _api_key()
    if not key:
        raise RuntimeError("ARC_API_KEY not found")
    sess = OnlineSession(key)
    try:
        frame, meta = reach_l3(sess)
        lv = int(meta.get("levels_completed") or 0)
        print(f"reached L3 levels={lv} mover={ls20.locate_mover(frame)}")

        path, notes = plan_experiment(frame, "C2")
        print(f"C2 plan len={len(path)} contact={notes.get('contact')} "
              f"gate={notes.get('gate')}")

        log = [{"tag": "start", "levels": lv, "mover": ls20.locate_mover(frame)}]
        entered = False
        max_ov = 0
        state = ls20.init(frame)
        stamp = next(g.shape for g in state.goals if g.id == "ls20-stamp")
        offset = ls20.grid_offset(frame)

        for i, a in enumerate(path, 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            new_lv = int(meta.get("levels_completed") or 0)
            mover = ls20.locate_mover(frame)
            # physical overlap of mover footprint with stamp
            cur_ov = 0
            if mover is not None:
                cur_ov = _ov(mover, stamp)
            max_ov = max(max_ov, cur_ov)
            if mover is not None and mover[1] == GATE_PX[1]:  # y == 50 -> entered (10,10)
                entered = True
            log.append({
                "step": i, "action": DIR_TO_ACTION[a], "mover": mover,
                "levels": new_lv, "ov_stamp": cur_ov,
            })
            print(f"  {i:02d} A{DIR_TO_ACTION[a]} bbox={mover} lv={new_lv} "
                  f"ov_stamp={cur_ov}")
            if new_lv > lv:
                log.append({"tag": "CLEARED", "step": i, "levels": new_lv})
                _write_report(log, "CLEARED", entered, max_ov)
                return 0

        _write_report(log, "NOT_CLEARED", entered, max_ov)
        print(f">>> entered_gate={entered} max_ov={max_ov}")
        return 0 if entered else 1
    finally:
        sess.close()


def _ov(a, b):
    ox0, oy0 = max(a[0], b[0]), max(a[1], b[1])
    ox1, oy1 = min(a[2], b[2]), min(a[3], b[3])
    return (ox1 - ox0 + 1) * (oy1 - oy0 + 1) if ox0 <= ox1 and oy0 <= oy1 else 0


def _write_report(log, verdict, entered, max_ov) -> None:
    lines = [
        "# ls20 L3 盖印门物理进入判定（E9）报告",
        "",
        "> 脚本：`tools/ls20_l3_gate_entry_probe.py`",
        "> 性质：设计期探路（最小动作 + 记录 mover bbox / ov_stamp / levels）",
        "",
        "---",
        "",
        "## 结论",
        "",
        f"**{verdict}**",
        "",
        f"- 物理进入 (10,10)（y=50）：`{entered}`",
        f"- 全程最大 mover↔stamp 重叠：`{max_ov}` px",
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
        "- `entered=True` + `CLEARED`：C2 仪式武装成功且盖印机制同 L1/L2。",
        "- `entered=True` + `NOT_CLEARED`：武装成功、进入 (10,10)，但盖印机制不同",
        "  （匹配材料 / 朝向 / 顺序），levels 不变。",
        "- `entered=False`：C2 仪式**未**武装 L3，mover 停在 (10,9)，",
        "  color9 字形 C 仍挡 unarmed 移动 → 武装判据 ≠ L2 的 carrying-overlap。",
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
