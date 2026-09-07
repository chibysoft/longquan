"""ls20 L3 mover-cover-legend localization — offline, zero budget.

WHY
  The legend (bottom-left color5 card) holds a 6x6 = 3x3-upscaled preview of
  the TARGET shape in the match-material color: color12 (mover) on L3. The L3
  stamp block (playfield color5, bottom-right) embeds the CURRENT pattern C in
  color9; legend A = rot180(C) is the target. Hypothesis: L3 clears when the
  mover (color12) covers the stamp's embedded target cells A.

  This script computes, for every walkable cell, how many of A's 6 target
  pixels the mover's 5x2 (color12) footprint covers — and, for reference, how
  many the mover+carrying 5x5 footprint covers. The question: can a SINGLE
  rigid 5x2 mover cover the 6px target, or does it need a composite?

  READ-ONLY (no engine calls, no canned answers).

Output: writes docs/ls20_l3_mover_cover.md.
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

OUT = ROOT / "docs" / "ls20_l3_mover_cover.md"
FIXTURE = ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json"


def plane(frame):
    a = np.asarray(frame, dtype=np.int8)
    if a.ndim == 2:
        return a
    for i in range(a.shape[0]):
        if np.any(a[i] == 12):
            return a[i]
    return a[0]


def stamp_interior(g):
    """Biggest playfield color5 block (x>=12, y<54) -> its embedded non-5 cells."""
    H, W = g.shape
    vis = np.zeros_like(g, dtype=bool)
    comps = []
    for y in range(H):
        for x in range(W):
            if g[y, x] != 5 or vis[y, x] or x < 12 or y >= 54:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (0 <= nx < W and 0 <= ny < H and not vis[ny, nx]
                            and g[ny, nx] == 5):
                        vis[ny, nx] = True
                        q.append((nx, ny))
            comps.append(cells)
    if not comps:
        return None
    comps.sort(key=len, reverse=True)
    cells = comps[0]
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    # embedded non-5 cells (pattern C, color9)
    emb = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)
           if g[y, x] != 5]
    return (x0, y0, x1, y1), emb


def rot180_cells(cells, x0, y0, x1, y1):
    """Rotate embedded cells 180deg about the 3x3 interior center."""
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    return sorted((int(round(2 * cx - x)), int(round(2 * cy - y))) for x, y in cells)


def main() -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    g = plane(data["frame"])
    state = ls20.init(g)
    offset = ls20.grid_offset(g)
    walk_u = ls20.build_walkable(g, offset, armed=False)
    walk_a = ls20.build_walkable(g, offset, armed=True)

    bbox, emb = stamp_interior(g)
    x0, y0, x1, y1 = bbox
    # embedded color9 = pattern C; target A = rot180(C)
    C = sorted(emb)
    A = rot180_cells(C, x0, y0, x1, y1)
    A_set = set(A)

    def cover(px, py, pw, ph):
        """Count target pixels A covered by a pw x ph footprint at (px,py)."""
        return sum(1 for tx, ty in A_set if px <= tx <= px + pw - 1 and py <= ty <= py + ph - 1)

    # mover 5x2 cover: unarmed reachable (walk_u) vs armed-reachable (walk_a)
    def rows_for(cells):
        out = []
        for c in cells:
            px, py = ls20.cursor_to_pixel(c, offset)
            cb = carrying_bbox_from_cursor(c, offset)
            cov_m = cover(px, py, 5, 2)
            cov_c = cover(cb[0], cb[1], cb[2] - cb[0] + 1, cb[3] - cb[1] + 1)
            out.append((cov_m, cov_c, c, (px, py)))
        out.sort(key=lambda t: (-t[0], -t[1]))
        return out

    best_u = rows_for(walk_u)
    best_a = rows_for(walk_a)

    def render_cells(cells):
        m = np.zeros((3, 3), dtype=int)
        for x, y in cells:
            m[y - (y0 + y1) // 2 + 1, x - (x0 + x1) // 2 + 1] = 1
        return "\n".join("".join("#" if v else "." for v in r) for r in m)

    L = [
        "# ls20 L3 mover 覆盖 legend 定位（离线）",
        "",
        "> 2026-09-06 · 纯离线 · 零预算 · 脚本 `tools/ls20_mover_cover_legend.py`",
        "",
        "---",
        "",
        "## 1. 锚定：legend 目标 A = stamp 内嵌图案 C 的 rot180",
        "",
        f"- stamp 块 bbox `{bbox}`（色5，右下）",
        f"- 内嵌色9 图案 **C**（当前态）=`{sorted(C)}`：",
        "```", render_cells(C), "```",
        f"- legend 色12 图案 **A**（目标态）= rot180(C) = `{sorted(A)}`：",
        "```", render_cells(A), "```",
        "",
        "锚定理由：legend 卡片是色5（与 stamp 同色），内嵌目标色图案 => legend",
        "=「stamp 块目标内嵌形状」的预览。L3 材料色=色12（mover）。",
        "",
        "---",
        "",
        "## 2. 覆盖计算（mover 5×2 vs 目标 A 的 6px）",
        "",
    ]

    L.append("### 2.1 unarmed walkable 中 mover 覆盖 top（实际可达，色9 仍挡）")
    L.append("| 覆盖 px | carrying 覆盖 | 逻辑格 | 像素 |")
    L.append("|--------|--------------|--------|------|")
    for cov_m, cov_c, c, pxpy in best_u[:8]:
        L.append(f"| {cov_m}/6 | {cov_c}/6 | `{c}` | `{pxpy}` |")

    L.append("")
    L.append("### 2.2 armed walkable 中 mover 覆盖 top（理论，需武装清色9）")
    L.append("| 覆盖 px | carrying 覆盖 | 逻辑格 | 像素 |")
    L.append("|--------|--------------|--------|------|")
    for cov_m, cov_c, c, pxpy in best_a[:8]:
        L.append(f"| {cov_m}/6 | {cov_c}/6 | `{c}` | `{pxpy}` |")

    max_u = best_u[0][0] if best_u else 0
    max_a = best_a[0][0] if best_a else 0
    L += [
        "",
        "---",
        "",
        "## 3. 结论",
        "",
        f"- unarmed 实际可达的最大覆盖：`{max_u}/6`",
        f"- armed 理论最大覆盖：`{max_a}/6`",
        "",
        "mover 是 **5×2 刚性块**，目标 A 是分散在 3 行（y51 顶行 3 格 / y52 右列",
        "1 格 / y53 底行 2 格）的 6px。mover 只有 2 行高、且 offset 锁死在 5px 网格",
        "（py 只能是 5 的倍数），所以：",
        "- 单块 mover **最多覆盖顶行 3 格**（站 `(10,10)`，px=54 覆盖 x55-57，py=50",
        "  覆盖 y51），永远够不到 y52/y53 的另外 3 格。",
        "",
        "**=> 单块 mover 不可能覆盖 legend A 的全部 6px，L3 过关材料必须是组合。**",
        "",
        "## 4. 组合候选（按可证伪性排序）",
        "",
        "1. **mover + carrying（色9 漆）**：carrying 在 mover 下方 3 行，5×5 足迹能",
        "   覆盖 y52/y53。但 carrying 是色9，不是材料色12——若材料必须是色12，则",
        "   携带漆反而「颜色不对」。需线上验证「mover 站 stamp 门 + 携带漆」是否触发。",
        "2. **mover 覆盖 + 第二块色12 段**：第二块 STATIC（已证 19 步不动），其色12",
        "   段 (30,48)/(31,48) 无法移动到位。排除。",
        "3. **stamp 门 (10,10) 是唯一入口**：mover 站 (10,10) 覆盖顶行 3 格 +",
        "   stamp_ov=10（恰阈值）。若「覆盖≥3 + stamp_ov≥10」即过关，则规则仍是",
        "   H20 盖印，只是武装判据变了（材料色12，非接触 plus）。",
        "",
    ]

    txt = "\n".join(L) + "\n"
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
