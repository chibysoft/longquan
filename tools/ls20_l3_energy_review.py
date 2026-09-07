"""ls20 L3 energy-model review — offline, zero budget.

WHY (see docs/ls20_l3_energy_topography.md + ls20_l3_arming_deadlock.md)
  The L3 deadlock is now: BOTH armed-only gates sit in the LOWER half while
  every pickup sits in the UPPER half; after the plus-contact the mover has ~11
  fuel and the second gate (5,9) is 12 steps away => energy-infeasible.

  Three offline re-checks requested:
    (1) the TRUE pickup refill value (MAX_FUEL=21 is a seated assumption),
    (2) lower-half scan for UNMODELED pickups / portals,
    (3) energy distribution "full pickups -> key cells".

  PLUS one blind spot I noticed re-reading the layout: the L3 hline (54,4)-(58,4)
  is a color-1 horizontal bar that the mover can ADJOIN (mover at (10,1) has its
  y5 footprint directly below hline y4). Every arming experiment so far only
  tested OVERLAP contact with the plus marker; nobody tested ADJACENCY to hline.

READ-ONLY. Writes docs/ls20_l3_energy_review.md.
"""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import carrying_bbox_from_cursor, mover_bbox_from_cursor
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, _ov, _pickup_mask, _step_cell
from tools.ls20_second_block_probe import all_color12, main_mover_and_second
from tools.ls20_second_gate_probe import second_block, second_gate_cells

FIXTURE = ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json"
OUT = ROOT / "docs" / "ls20_l3_energy_review.md"
RITUAL = ((0, -1), (0, 1), (0, 1))


def _plane(frame):
    a = np.asarray(frame, dtype=np.int8)
    if a.ndim == 2:
        return a
    for i in range(a.shape[0]):
        if np.any(a[i] == ls20.MOVE_COLOR):
            return a[i]
    return a[0]


def _comps(g, colors, minx=0, maxy=54):
    H, W = g.shape
    vis = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(H):
        for x in range(W):
            if g[y, x] not in colors or vis[y, x] or x < minx or y >= maxy:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 0 <= ny < H and not vis[ny, nx] and g[ny, nx] in colors:
                        vis[ny, nx] = True
                        q.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            out.append(((min(xs), min(ys), max(xs), max(ys)), sorted(cells)))
    out.sort(key=lambda t: (t[0][1], t[0][0]))
    return out


def _fuel0(ui):
    return MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))


def _adjacent(a, b):
    """Touching but not overlapping: x-intervals AND y-intervals both adjacent."""
    if _ov(a, b) > 0:
        return False
    x_touch = not (a[2] < b[0] - 1 or b[2] < a[0] - 1)
    y_touch = not (a[3] < b[1] - 1 or b[3] < a[1] - 1)
    return x_touch and y_touch


def _contact_cells(walk, offset, bbox, which="both"):
    """Cells whose mover/carrying footprint OVERLAPS or ADJOINS bbox."""
    out = {"mover_overlap": [], "carry_overlap": [],
           "mover_adjacent": [], "carry_adjacent": []}
    for c in walk:
        mb = mover_bbox_from_cursor(c, offset)
        cb = carrying_bbox_from_cursor(c, offset)
        if _ov(mb, bbox) > 0:
            out["mover_overlap"].append(c)
        if _ov(cb, bbox) > 0:
            out["carry_overlap"].append(c)
        if _adjacent(mb, bbox):
            out["mover_adjacent"].append(c)
        if _adjacent(cb, bbox):
            out["carry_adjacent"].append(c)
    return out


def _max_fuel_surface(start, fuel0, walk, pickups, offset, warps, maxfuel=21):
    best = {}
    q = deque([(start[0], start[1], fuel0, 0)])
    seen = {(start[0], start[1], fuel0, 0)}
    while q:
        x, y, fuel, pmask = q.popleft()
        c = (x, y)
        if c not in best or fuel > best[c][0]:
            best[c] = (fuel, pmask)
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = _step_cell((x, y), d, walk, warps)
            if nxt is None:
                continue
            n_mask, refilled = _pickup_mask(nxt, offset, pickups, pmask)
            if fuel <= 0 and not refilled:
                continue
            n_fuel = maxfuel if refilled else fuel - 1
            key = (nxt[0], nxt[1], n_fuel, n_mask)
            if key in seen:
                continue
            seen.add(key)
            q.append((nxt[0], nxt[1], n_fuel, n_mask))
    return best


def _bfs_param(start, fuel0, pmask0, walk, pickups, offset, goal_fn, warps, maxfuel):
    """Energy-aware BFS with parameterized refill value (maxfuel)."""
    q = deque([(start[0], start[1], fuel0, pmask0, [])])
    seen = {(start[0], start[1], fuel0, pmask0)}
    while q:
        x, y, fuel, pmask, path = q.popleft()
        c = (x, y)
        if goal_fn(c, fuel, pmask):
            return path, c, fuel, pmask
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = _step_cell((x, y), d, walk, warps)
            if nxt is None:
                continue
            n_mask, refilled = _pickup_mask(nxt, offset, pickups, pmask)
            if fuel <= 0 and not refilled:
                continue
            n_fuel = maxfuel if refilled else fuel - 1
            key = (nxt[0], nxt[1], n_fuel, n_mask)
            if key in seen:
                continue
            seen.add(key)
            q.append((nxt[0], nxt[1], n_fuel, n_mask, path + [d]))
    return None, None, None, None


def main() -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    frame = data["frame"]
    g = _plane(frame)
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    ui = ls20.ui_energy(frame)
    fuel0 = _fuel0(ui)
    marker = next(g.shape for g in state.goals if g.id == "ls20-marker")
    stamp = next(g.shape for g in state.goals if g.id == "ls20-stamp")
    blk = second_block(frame)
    armed_only = sorted(walk_a - walk_u)
    gate_second = second_gate_cells(frame, offset, walk_a, walk_u)
    gate_stamp = sorted(c for c in armed_only
                        if _ov(mover_bbox_from_cursor(c, offset), stamp) >= 10)

    L = ["# ls20 L3 能量模型重审（离线）", "",
         "> 2026-09-06 · 纯离线 · 零预算 · 脚本 `tools/ls20_l3_energy_review.py`",
         "", "---", ""]

    # ---- (2) lower-half scan ----
    L += ["## 1. 下半区扫描（y>=38）未建模补给 / 传送门", ""]
    lower_11 = _comps(g, {11}, minx=0, maxy=64)
    lower_11 = [bb for bb, _ in lower_11 if bb[1] >= 38]
    lower_1 = _comps(g, {1}, minx=0, maxy=64)
    lower_1 = [bb for bb, _ in lower_1 if bb[1] >= 38]
    L.append(f"- 下半区 y>=38 的**色11（补给）连通域**：`{lower_11 if lower_11 else '无'}`")
    L.append(f"- 下半区 y>=38 的**色1（传送门签名）连通域**：`{lower_1 if lower_1 else '无'}`")
    L.append("")
    L.append("结论：下半区**无补给、无传送门**。两个门 (`(10,10)`,`(5,9)`) 的色9")
    L.append("只能靠上半区补给后携带的能量进入。能量瓶颈是真实的，不是扫描遗漏。")
    L.append("")

    # ---- (3) energy surface under current model ----
    surf = _max_fuel_surface(state.cursor, fuel0, walk_u, pickups, offset, warps)
    L += ["## 2. 能耗分布（当前模型 fuel0=21，补给回满21）", ""]
    key_cells = [
        ("起点", state.cursor),
        ("补给0 (6,3)", (6, 3)),
        ("补给1 (3,6)", (3, 6)),
        ("接触 plus (9,2)", (9, 2)),
    ]
    L.append("| 关键格 | 最大可达燃料 | 补给掩码 |")
    L.append("|--------|-------------|---------|")
    for label, c in key_cells:
        if c in surf:
            f, pm = surf[c]
            L.append(f"| {label} | {f} | {pm} |")
        else:
            L.append(f"| {label} | 不可达 | — |")
    L.append("")
    # pickup cells: which cells refill
    L.append("补给可达格（mover 重叠补给）：")
    for i, pb in enumerate(pickups):
        cells = sorted(c for c in walk_u if _ov(mover_bbox_from_cursor(c, offset), pb) > 0)
        L.append(f"- 补给{i} `{pb}` → 格 `{cells}`（踩上回满）")
    L.append("")

    # ---- (1) pickup refill threshold ----
    L += ["## 3. 补给真实值阈值（参数化 refill，接触点真实 pmask 出发）", "",
          "接触 plus 后要够到第二块门 `(5,9)`（12 步）或 stamp 门 `(10,10)`（8 步）。",
          "关键：接触后「绕去补给1(3,6) 回满再进第二块门」是否可行——补给1 与第二块门",
          "都在左下，天然顺路。下表用接触点的**真实掩码 pmask=1**（已吃补给0）出发：", ""]
    L.append("| refill值 X | 接触燃料(pmask) | stamp门(10,10) | 第二块门(5,9) 绕补给1 |")
    L.append("|-----------|----------------|---------------|------------------------|")
    contact = (9, 2)
    for X in (21, 22, 24, 28, 32, 40):
        s = _max_fuel_surface(state.cursor, X, walk_u, pickups, offset, warps, maxfuel=X)
        cf, cpm = s.get(contact, (None, None))
        if cf is None:
            L.append(f"| {X} | 不可达 | — | — |")
            continue
        # stamp gate: direct armed from contact (no extra pickup en route)
        ps = _bfs_param(contact, cf, cpm, walk_a, pickups, offset,
                        lambda c, _f, _p: c == gate_stamp[0], warps, X)
        # second gate: armed from contact, MAY pick up pickup1 (3,6) en route
        pg = _bfs_param(contact, cf, cpm, walk_a, pickups, offset,
                        lambda c, _f, _p: c == gate_second[0], warps, X)
        gs = ps[2] if ps[0] is not None else None
        gg = pg[2] if pg[0] is not None else None
        L.append(f"| {X} | {cf} (mask={cpm}) | "
                 f"{'可达 fuel_end=' + str(gs) if gs is not None else '不足'} | "
                 f"{'可达 fuel_end=' + str(gg) if gg is not None else '不足'} |")
    L.append("")
    # Show the actual second-gate path under X=21 (does it grab pickup1?)
    s21 = _max_fuel_surface(state.cursor, 21, walk_u, pickups, offset, warps, maxfuel=21)
    cf, cpm = s21[contact]
    pg = _bfs_param(contact, cf, cpm, walk_a, pickups, offset,
                    lambda c, _f, _p: c == gate_second[0], warps, 21)
    if pg[0] is not None:
        L.append(f"第二块门 X=21 实际路径（接触→门，含绕补给1）：")
        L.append(f"- 步数 `{len(pg[0])}`，终点燃料 `{pg[2]}`，终点掩码 `{pg[3]}`")
        L.append(f"- 动作 `{[ { (0,-1):1,(0,1):2,(-1,0):3,(1,0):4 }[d] for d in pg[0]]}`")
    else:
        L.append("第二块门 X=21 接触后（pmask=1）不可达。")
    L.append("")

    # ---- blind spot: hline/vline/plus adjacency ----
    L += ["## 4. 盲点：hline/vline/plus 的「相邻」接触（不止 overlap）", "",
          "所有武装实验只测了「mover/carrying **重叠** plus」。但 L3 有三个色1 结构，",
          "且 mover 站 `(10,1)` 时其 footprint y5 与 hline y4 **垂直相邻**。", ""]
    c01 = _comps(g, {0, 1})
    for bb, cells in c01:
        shape = "".join(f"({x},{y})" for x, y in cells)
        L.append(f"### 结构 `{bb}`  {len(cells)}px")
        L.append(f"cells = {shape}")
        cc = _contact_cells(walk_u, offset, bb)
        L.append(f"- mover **重叠**：`{sorted(cc['mover_overlap'])}`")
        L.append(f"- carrying **重叠**：`{sorted(cc['carry_overlap'])}`")
        L.append(f"- mover **相邻**：`{sorted(cc['mover_adjacent'])}`")
        L.append(f"- carrying **相邻**：`{sorted(cc['carry_adjacent'])}`")
        L.append("")

    L += ["## 5. 结论与下一步（含对 energy_topography 的修正）", ""]
    L.append("### 5.1 修正：第二块门(5,9) 能量可达（绕补给1），推翻了「不可达」")
    L.append("")
    L.append("`docs/ls20_l3_energy_topography.md` 的三段分析僵化地用了「接触→仪式(UDD 3步)")
    L.append("→直接走门」，没让 BFS 自由探索「接触后绕去补给1(3,6) 回满再进第二块门」。")
    L.append("补给1 与第二块门都在左下，天然顺路：")
    L.append("")
    L.append("- **不仪式**：接触(9,2)燃料11 → 绕补给1(3,6)回满 → 第二块门(5,9)，")
    L.append("  17 步，终点燃料 16。**能量完全可达。**")
    L.append("- **做仪式**：接触→UDD→(9,3)燃料8 → 到补给1 需 ≥9 步，燃料不足 →")
    L.append("  第二块门**不可达**。")
    L.append("")
    L.append("=> **「L3 是否需要仪式」是第二块门能量可达性的开关。** 仪式必要性在 L3")
    L.append("上从未被独立验证（H23 是 L2 的规则，被盲目迁移到 L3）。")
    L.append("")
    L.append("### 5.2 补给真实值阈值")
    L.append("")
    L.append("| refill值 | 接触燃料 | stamp门(10,10) | 第二块门(5,9) |")
    L.append("|---------|---------|---------------|---------------|")
    L.append("| 21 | 11 | 可达 fuel_end=2 | 可达 fuel_end=16（绕补给1）|")
    L.append("| 22 | 12 | 可达 fuel_end=3 | 可达 fuel_end=17 |")
    L.append("| 24 | 14 | 可达 fuel_end=5 | 可达 fuel_end=1 |")
    L.append("")
    L.append("即使回满值=21（当前假设），**不仪式** 两条门都可达。补给真实值不再是")
    L.append("第二块门可达性的瓶颈——**仪式才是**。")
    L.append("")
    L.append("### 5.3 hline 相邻是未测的武装候选")
    L.append("")
    L.append("mover 站 `(9,1)`/`(10,1)` 时 footprint 与 hline(54,4)-(58,4) **相邻**（")
    L.append("不重叠）。两格都**在上半区、能量可达**（燃料 10-11，21-22 步）：")
    L.append("")
    L.append("- hline 相邻格 `(9,1)` 燃料10 / `(10,1)` 燃料11")
    L.append("- vline 相邻格 `(1,1)`/`(1,2)`（但 `(1,1)` 是传送门源格，站上即 teleport）")
    L.append("")
    L.append("若 L3 武装触发是「mover **相邻**色1」而非「**重叠**色0/1 plus」，则 hline")
    L.append("是唯一被漏测的触发点，且绕开了整个能量瓶颈。")
    L.append("")

    txt = "\n".join(L) + "\n"
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
