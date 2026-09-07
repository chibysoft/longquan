"""Probe E5: where does the ring's mass go when (5,9) dissolves it?

CONTEXT (docs/ls20_l3_ring_entry_probe.md, E4)
  Entering (5,9) dissolves the ring: ring->None, c14 2->0, c12 36->10, c9 23->45.
  E4 showed the stamp gate stays armed-only and unreachable after. This probe
  asks the DIAGNOSTIC question E4 skipped: did the mover's CARRYING blob grow by
  the ~22px the ring released, or did that color-9 land elsewhere on the board?

  If carrying grew (15 -> ~37), the ring is a PICKUP the mover now carries — and
  the next step is to DEPOSIT it (stamp? a second ring?). If carrying is
  unchanged, the color-9 spilled into the environment (a door opened elsewhere).

USAGE
  python tools/ls20_l3_dissolve_inspect_probe.py --plan-only
  python tools/ls20_l3_dissolve_inspect_probe.py
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
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs
from tools.ls20_l3_armed_controller import reach_l3
from tools.ls20_second_block_probe import main_mover_and_second
from tools.ls20_l3_ring_interact_probe import _ring_bbox, _ring_colors

FIXTURE = ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json"
REPORT = ROOT / "docs" / "ls20_l3_dissolve_inspect_probe.md"

INTERACT = 5
POINT = (4, 9)
GATE = (5, 9)


def _comps(g, color, maxy=54):
    H, W = g.shape
    vis = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(H):
        for x in range(W):
            if g[y, x] != color or vis[y, x] or y >= maxy:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 0 <= ny < H and not vis[ny, nx] and g[ny, nx] == color:
                        vis[ny, nx] = True
                        q.append((nx, ny))
            if len(cells) >= 2:
                xs = [c[0] for c in cells]
                ys = [c[1] for c in cells]
                out.append((min(xs), min(ys), max(xs), max(ys), len(cells)))
    return sorted(out)


def _dump(frame, tag):
    g = ls20._plane(frame)
    mover = ls20.locate_mover(frame)
    carry = ls20.carrying_near_mover(frame, mover)
    _, seconds = main_mover_and_second(frame)
    ring = _ring_bbox(frame)
    return {
        "tag": tag,
        "mover": mover,
        "carrying": carry,
        "second": seconds[0] if seconds else None,
        "ring": ring,
        "ring_colors": _ring_colors(frame, ring) if ring else None,
        "c9": int((g == 9).sum()),
        "c12": int((g == 12).sum()),
        "c14": int((g == 14).sum()),
        "c3": int((g == 3).sum()),
        "c9_comps": _comps(g, 9),
        "c12_comps": _comps(g, 12),
    }


def plan_only() -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    frame = data["frame"]
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))
    p1, _, _, _ = _energy_bfs(
        state.cursor, fuel0, 0, walk_u, pickups, offset,
        lambda c, _f, _p: c == POINT, warps,
    )
    print(f"POINT={POINT} GATE={GATE}")
    print(f"pre path len = {len(p1)}")
    print(f"actions = {[DIR_TO_ACTION[a] for a in p1]}")
    print("pre-dissolve state:")
    for k, v in _dump(frame, "pre").items():
        print(f"  {k} = {v}")
    return 0


def run_online() -> int:
    key = _api_key()
    if not key:
        raise RuntimeError("no ARC_API_KEY")
    sess = OnlineSession(key)
    try:
        frame, meta = reach_l3(sess)
        print(f"reached L3 levels={meta.get('levels_completed')}")
        state = ls20.init(frame)
        offset = ls20.grid_offset(frame)
        walk_u = ls20.build_walkable(frame, offset, armed=False)
        warps = ls20.detect_warps(frame, offset, walk_u)
        pickups = ls20.energy_pickups(frame)
        ui = ls20.ui_energy(frame)
        fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))
        p1, _, _, _ = _energy_bfs(
            state.cursor, fuel0, 0, walk_u, pickups, offset,
            lambda c, _f, _p: c == POINT, warps,
        )
        print(f"pre state:")
        pre = _dump(frame, "pre")
        for k, v in pre.items():
            print(f"  {k} = {v}")

        log = [pre]
        lv = int(meta.get("levels_completed") or 0)
        for i, a in enumerate(p1, 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            new_lv = int(meta.get("levels_completed") or 0)
            if new_lv > lv:
                print(">>> LEVEL UP during move")
                return 0
        # enter gate -> dissolve
        resp = sess.action(DIR_TO_ACTION[(1, 0)])
        frame, meta = resp["frame"], resp
        new_lv = int(meta.get("levels_completed") or 0)
        post = _dump(frame, "post-dissolve")
        log.append(post)
        print(f"post-dissolve state (lv={new_lv}):")
        for k, v in post.items():
            print(f"  {k} = {v}")

        # did carrying grow?
        pc, cc = pre["carrying"], post["carrying"]
        print(f"carrying change: {pc} -> {cc}")
        _write_report(log, "INSPECTED")
        return 0
    finally:
        sess.close()


def _write_report(log, verdict) -> None:
    lines = [
        "# ls20 L3 环溶解检查（E5）报告",
        "",
        "> 脚本：`tools/ls20_l3_dissolve_inspect_probe.py`",
        "> 性质：设计期探路（最小动作 + 比对 levels），非运行时求解器",
        "",
        "---",
        "",
        "## 结论",
        "",
        f"**{verdict}**",
        "",
        "## 快照",
        "",
    ]
    for d in log:
        lines.append(f"- `{d}`")
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
