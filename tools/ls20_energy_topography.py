"""ls20 L3 energy topography (pure offline, zero budget).

WHY
  The L3 arming experiments established that BOTH armed-only gates sit in the
  LOWER half while every pickup sits in the UPPER half, and that after the plus
  contact ritual the mover has only ~8-11 fuel. This script maps the full energy
  surface so we can answer, without spending online steps:

    Q1  Where exactly are the pickups / portals / armed-only cells?
    Q2  Is either gate reachable with enough fuel, under the best strategy?
    Q3  Does a "full-energy path" to the lower half exist at all?

  It is a READ-ONLY design-time analysis (no engine calls, no canned answers).

Output: prints a summary and writes docs/ls20_l3_energy_topography.md.
"""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path
from typing import Dict, List, Tuple

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
OUT = ROOT / "docs" / "ls20_l3_energy_topography.md"
RITUAL = ((0, -1), (0, 1), (0, 1))


def _fuel0(ui: int) -> int:
    return MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))


def _dist(a, b, walk, warps):
    q = deque([(a, 0)]); seen = {a}
    while q:
        c, d = q.popleft()
        if c == b:
            return d
        for dd in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = _step_cell(c, dd, walk, warps)
            if n is not None and n not in seen:
                seen.add(n); q.append((n, d + 1))
    return None


def _pickup_cells(pickups, walk, offset):
    out = []
    for i, pb in enumerate(pickups):
        cells = sorted(c for c in walk
                       if _ov(mover_bbox_from_cursor(c, offset), pb) > 0)
        out.append((i, pb, cells))
    return out


def _max_fuel_surface(start, fuel0, walk, pickups, offset, warps, cap_steps=200):
    """Energy-augmented BFS: for each cell, the MAX fuel achievable there.

    Returns dict cell -> max fuel, plus the pmask achieved at that max.
    """
    best: Dict[Tuple[int, int], Tuple[int, int]] = {}  # cell -> (fuel, pmask)
    start_key = (start[0], start[1], fuel0, 0)
    q = deque([(start_key, [])])
    seen = {start_key}
    while q:
        (x, y, fuel, pmask), _ = q.popleft()
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
            n_fuel = MAX_FUEL if refilled else fuel - 1
            key = (nxt[0], nxt[1], n_fuel, n_mask)
            if key in seen:
                continue
            seen.add(key); q.append((key, None))
    return best


def main() -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    frame = data["frame"]
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
    main, seconds = main_mover_and_second(frame)
    blk = second_block(frame)

    armed_only = sorted(walk_a - walk_u)
    gate_second = second_gate_cells(frame, offset, walk_a, walk_u)
    gate_stamp = sorted(c for c in armed_only
                        if _ov(mover_bbox_from_cursor(c, offset), stamp) >= 10)

    # pickup cells + their energy (each = refill to MAX_FUEL on step)
    pk_cells = _pickup_cells(pickups, walk_u, offset)

    # contact cell (the unique plus-contact cell)
    def at_contact(c, _f, _p):
        return _ov(carrying_bbox_from_cursor(c, offset), marker) > 0
    contact_cells = sorted(c for c in walk_u if at_contact(c, 0, 0))

    # full fuel surface (unarmed)
    surf = _max_fuel_surface(state.cursor, fuel0, walk_u, pickups, offset, warps)

    # --- scenario analyses ---
    def gate_feasibility(gate):
        # (a) direct unarmed max fuel AT gate (gate is armed-only => not in walk_u)
        # (b) from contact+ritual, armed BFS
        return {}

    rows = []
    for name, gate in [("stamp gate (10,10)", gate_stamp[0] if gate_stamp else None),
                       ("second gate (5,9)", gate_second[0] if gate_second else None)]:
        if gate is None:
            rows.append((name, "missing", None, None, None))
            continue
        # direct armed distance from contact+ritual
        p1 = _energy_bfs(state.cursor, fuel0, 0, walk_u, pickups, offset,
                         at_contact, warps)
        if p1 is None:
            rows.append((name, "no-contact", None, None, None)); continue
        c1 = p1[1]; f1 = p1[2]; pm1 = p1[3]
        cur, fuel, pmask = c1, f1, pm1
        for d in RITUAL:
            nxt = _step_cell(cur, d, walk_u, warps)
            if nxt is None:
                fuel = -1; break
            n_mask, refilled = _pickup_mask(nxt, offset, pickups, pmask)
            fuel = MAX_FUEL if refilled else fuel - 1
            cur, pmask = nxt, n_mask
        ritual_end = cur; fuel_after_ritual = fuel
        p2 = _energy_bfs(cur, fuel, pmask, walk_a, pickups, offset,
                         lambda c, _f, _p: c == gate, warps)
        d_plain = _dist(ritual_end, gate, walk_a, warps)
        max_fuel_gate = surf.get(gate, (None,))[0] if gate in surf else None
        rows.append((name, gate, fuel_after_ritual, d_plain,
                     None if p2[0] is None else f"feasible fuel_end={p2[2]}"))

    # Build report
    lines = [
        "# ls20 L3 能量地形铺图",
        "",
        "> 2026-09-06 · 纯离线 · 零预算 · 脚本 `tools/ls20_energy_topography.py`",
        "",
        "---",
        "",
        "## 1. 静态清单",
        "",
        f"- 起始 cursor：`{state.cursor}`（像素 `{ls20.cursor_to_pixel(state.cursor, offset)}`）",
        f"- 网格 offset：`{offset}`",
        f"- walkable 格数（未武装）：`{len(walk_u)}`",
        f"- armed-only 格数（武装后新增）：`{len(armed_only)}`",
        f"- 起始能量 ui：`{ui}` → fuel0 = `{fuel0}`",
        "",
        "### 补给（playfield 色11）",
        "",
    ]
    if not pk_cells:
        lines.append("_无_")
    else:
        lines.append("| # | 像素 bbox | 逻辑格（mover 重叠） | 能量值 |")
        lines.append("|---|-----------|----------------------|--------|")
        for i, pb, cells in pk_cells:
            lines.append(f"| {i} | `{pb}` | `{cells}` | 回满 `{MAX_FUEL}` |")

    lines += ["", "### 传送门（detect_warps）", ""]
    if not warps:
        lines.append("_无_")
    else:
        lines.append("| (cell, dir) | 落点 |")
        lines.append("|-------------|------|")
        for (c, d), land in sorted(warps.items()):
            lines.append(f"| `{c}` + `{d}` | `{land}` |")

    lines += ["", "### armed-only 格（武装后新增可走）", ""]
    for c in armed_only:
        px, py = ls20.cursor_to_pixel(c, offset)
        nines = [(px + dx, py + dy) for dy in range(2) for dx in range(5)
                 if ls20._plane(frame)[py + dy, px + dx] == 9]
        is_second = c in gate_second
        is_stamp = c in gate_stamp
        tag = ("第二块门" if is_second else "") + (" / stamp门" if is_stamp else "")
        lines.append(f"- `{c}` 像素`({px},{py})` 清除色9=`{nines}` {tag}")

    lines += ["", "### 第二块 3x3 结构", "",
              f"- bbox：`{blk}`（mover 站 `(5,9)` 时完整罩住）", ""]

    lines += ["---", "", "## 2. 能量可达性（能量增强 BFS）", ""]
    # report max fuel at key cells
    keys = [("contact(9,2)", contact_cells[0] if contact_cells else None),
            ("stamp门(10,10)", gate_stamp[0] if gate_stamp else None),
            ("第二块门(5,9)", gate_second[0] if gate_second else None)]
    for label, c in keys:
        if c is None:
            lines.append(f"- `{label}`：不存在")
        elif c in surf:
            f, pm = surf[c]
            lines.append(f"- `{label}`：未武装最大燃料 = `{f}`（补给掩码 `{pm}`）")
        else:
            lines.append(f"- `{label}`：未武装不可达")

    lines += ["", "## 3. 三段能耗（接触 → 仪式 → 门）", "",
              "| 门 | 接触后燃料 | 仪式后燃料 | 到门几何距离 | 能量可达？ |",
              "|----|-----------|-----------|-------------|-----------|"]
    for name, gate, f_rit, d_plain, feas in rows:
        lines.append(f"| {name} | {f_rit + len(RITUAL) if isinstance(f_rit, int) and f_rit >= 0 else '—'} | "
                     f"{f_rit if isinstance(f_rit, int) and f_rit >= 0 else '—'} | "
                     f"{d_plain} | {feas or '能量不足'} |")

    lines += ["", "## 4. 结论（满能量路径是否存在）", ""]
    # r[4] is the feasibility string: "feasible fuel_end=..." (reachable) or None.
    any_feasible_stamp = any(r[0] == "stamp gate (10,10)" and r[4] is not None for r in rows)
    any_feasible_second = any(r[0] == "second gate (5,9)" and r[4] is not None for r in rows)
    lines.append(f"- 满能量路径到 stamp 门 `(10,10)`：{'存在（fuel_end=0）' if any_feasible_stamp else '不存在'}")
    lines.append(f"- 满能量路径到 第二块门 `(5,9)`：{'存在' if any_feasible_second else '不存在（能量不可达）'}")
    lines.append("")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
