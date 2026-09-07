"""Probe E7: full-plane pixel diff pre/post ring dissolve.

WHY
  E5 (dissolve_inspect) recorded COUNTS only: on entering (5,9), c12 36->10
  (legend 24px + ring 2px vanish) and c9 23->45 (+22px). It never said WHERE the
  26px of color12 went or what the +22px color9 became. That gap hides the L3
  mechanism. This probe dumps the FULL 64x64 plane before and after the dissolve
  and computes the exact per-pixel diff, plus a component breakdown that INCLUDES
  the bottom block (y>=54, which E5 filtered out).

USAGE
  python tools/ls20_l3_dissolve_fulldiff_probe.py --plan-only
  python tools/ls20_l3_dissolve_fulldiff_probe.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
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
REPORT = ROOT / "docs" / "ls20_l3_dissolve_fulldiff_probe.md"

POINT = (4, 9)   # ring-left adjacent
GATE = (5, 9)    # enter to dissolve


def _hist(g):
    vals, counts = np.unique(g, return_counts=True)
    return {int(v): int(c) for v, c in zip(vals, counts)}


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
    p = _path_to(data["frame"], POINT)
    print(f"POINT={POINT} GATE={GATE}")
    print(f"path to POINT len={None if p is None else len(p)}")
    if p:
        print(f"actions = {[DIR_TO_ACTION[a] for a in p]}")
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
        p = _path_to(frame, POINT)
        if p is None:
            raise RuntimeError(f"no path to {POINT}")

        for a in p:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
        pre = ls20._plane(frame).copy()
        print(f"pre: mover={ls20.locate_mover(frame)} hist={_hist(pre)}")

        # dissolve
        resp = sess.action(DIR_TO_ACTION[(1, 0)])  # RIGHT into (5,9)
        frame, meta = resp["frame"], resp
        post = ls20._plane(frame).copy()
        new_lv = int(meta.get("levels_completed") or 0)
        print(f"post-dissolve: mover={ls20.locate_mover(frame)} lv={new_lv} "
              f"hist={_hist(post)}")

        # pixel diff
        changed = []
        ys, xs = np.where(pre != post)
        for x, y in zip(xs.tolist(), ys.tolist()):
            changed.append((x, y, int(pre[y, x]), int(post[y, x])))
        print(f"changed pixels: {len(changed)}")
        for c in changed:
            print(f"  ({c[0]:2d},{c[1]:2d}) {c[2]} -> {c[3]}")

        _write_report(pre, post, changed, lv, new_lv)
        return 0
    finally:
        sess.close()


def _write_report(pre, post, changed, lv, new_lv) -> None:
    lines = [
        "# ls20 L3 环溶解全平面 diff（E7）报告",
        "",
        "> 脚本：`tools/ls20_l3_dissolve_fulldiff_probe.py`",
        "> 性质：设计期探路（最小动作 + 全平面 diff），非运行时求解器",
        "",
        "---",
        "",
        "## 直方图",
        "",
        f"- pre : `{_hist(pre)}`",
        f"- post: `{_hist(post)}`",
        "",
        "## 像素 diff（x, y, before, after）",
        "",
    ]
    # group by color transition
    trans = Counter((b, a) for (_x, _y, b, a) in changed)
    lines.append("### 颜色转换统计")
    for (b, a), n in sorted(trans.items()):
        lines.append(f"- `{b} -> {a}` : {n} px")
    lines.append("")
    lines.append("### 逐像素")
    for x, y, b, a in sorted(changed, key=lambda t: (t[1], t[0])):
        lines.append(f"- `({x},{y}) {b}->{a}`")
    lines += [
        "",
        "## 判读",
        "",
        f"- levels: {lv} -> {new_lv}",
        "- 关注：`12 -> ?`（legend 24px + ring 2px 的去向）与 `? -> 9`（+22px 的来源）。",
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
