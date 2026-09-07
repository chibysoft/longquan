"""ls20 L3 color-ring transform exhaustion — offline, zero budget.

WHY
  The L3 "second block" is a 3x3 color ring (center color0, four 2px arc
  segments color9/14/8/12 clockwise). One hypothesis was: rotate/mirror this
  ring so its color12 segment aligns with the legend color12 pattern A
  (`###/..#/#.#`), which would lock the L3 rule to "rotate the ring so color12
  matches the legend".

  This script exhaustively tests that hypothesis. It is READ-ONLY (no engine
  calls, no canned answers).

RESULT (negative but decisive)
  The ring's 8 outer cells and the target patterns' 6 outer cells are both
  subsets of the same 3x3 perimeter, so geometric matching has NO
  discriminating power:
    - single 2px segment -> 6px pattern: IoU always 2/6, every segment fits
    - any 4px pair union -> 6px pattern: IoU always 4/6
    - full 8px ring -> 6px pattern: IoU 6/8 (pattern IS a 6-cell subset)
  => "rotate ring so color12 aligns with legend" is FALSIFIED (over-matched).
  The real signal is the color-symmetry family (see docs §8 of
  ls20_l3_legend_alignment.md): legend/stamp patterns are fx / rot180 of each
  other, and legend color = match material.

Output: prints a match table and writes docs/ls20_l3_color_ring.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "ls20_l3_color_ring.md"
FIXTURE = ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json"


def plane(frame):
    a = np.asarray(frame, dtype=np.int8)
    if a.ndim == 2:
        return a
    for i in range(a.shape[0]):
        if np.any(a[i] == 12):
            return a[i]
    return a[0]


def second_block_ring(g):
    """Extract the 3x3 color ring at (30,46)-(32,48) as color->frozenset(cells)."""
    ring = {}
    for y in range(46, 49):
        for x in range(30, 33):
            c = int(g[y, x])
            ring.setdefault(c, set()).add((x - 30, y - 46))
    return {c: frozenset(v) for c, v in ring.items()}


def transforms(cells):
    return {
        "id":     {(x, y) for x, y in cells},
        "r90":    {(2 - y, x) for x, y in cells},
        "r180":   {(2 - x, 2 - y) for x, y in cells},
        "r270":   {(y, 2 - x) for x, y in cells},
        "fx":     {(2 - x, y) for x, y in cells},
        "fy":     {(x, 2 - y) for x, y in cells},
        "transp": {(y, x) for x, y in cells},
        "anti":   {(2 - y, 2 - x) for x, y in cells},
    }


def iou(a, b):
    a, b = set(a), set(b)
    inter = len(a & b)
    uni = len(a | b)
    return inter / uni if uni else 0.0


def render(cells):
    m = np.zeros((3, 3), dtype=int)
    for x, y in cells:
        m[y, x] = 1
    return "\n".join("".join("#" if v else "." for v in r) for r in m)


def main() -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    g = plane(data["frame"])
    ring = second_block_ring(g)

    # Target patterns (from legend/stamp alignment, see legend_alignment doc §8)
    A = frozenset({(0, 0), (1, 0), (2, 0), (2, 1), (0, 2), (2, 2)})  # legend L2/L3 (12) = stamp L1 (9)
    C = frozenset({(0, 0), (2, 0), (0, 1), (0, 2), (1, 2), (2, 2)})  # stamp L3 (9) = rot180(A)
    outer = frozenset(ring.get(9, set()) | ring.get(14, set())
                      | ring.get(8, set()) | ring.get(12, set()))

    L = [
        "# ls20 L3 颜色环变换穷举（离线证伪）",
        "",
        "> 2026-09-06 · 纯离线 · 零预算 · 脚本 `tools/ls20_color_ring.py`",
        "",
        "---",
        "",
        "## 1. 第二块颜色环",
        "",
        "第二块 3×3（像素 (30,46)-(32,48)），相对坐标：",
        "",
        "```",
        "9  14 14",
        "9  0  8",
        "12 12 8",
        "```",
        "",
        "| 颜色 | 落点（相对） | 段形状 |",
        "|------|--------------|--------|",
    ]
    for c in (9, 14, 8, 12):
        cells = sorted(ring[c])
        L.append(f"| `{c}` | {cells} | 2px |")
    L.append(f"| `0` | {sorted(ring[0])} | 中心 1px |")
    L += ["", "四段色（9/14/8/12）是 3×3 外圈 8 格的顺时针划分，中心 color0。", ""]

    L += ["---", "", "## 2. 目标图案", "",
          f"- **A**（legend L2/L3 的 color12 图案 = stamp L1 的 color9 图案）：",
          "```", render(A), "```",
          f"- **C**（stamp L3 的 color9 图案 = rot180(A)）：",
          "```", render(C), "```", ""]

    L += ["---", "", "## 3. 穷举匹配结果（8 个对称变换）", ""]

    L.append("### 3.1 单段 2px vs 6px 图案（IoU）")
    L.append("| 段 | vs A 最佳 IoU | vs A 子集? | vs C 最佳 IoU | vs C 子集? |")
    L.append("|----|--------------|-----------|--------------|-----------|")
    for c in (9, 14, 8, 12):
        seg = set(ring[c])
        bestA = max(iou(seg, t) for t in transforms(A).values())
        bestC = max(iou(seg, t) for t in transforms(C).values())
        subA = any(t <= set(A) for t in transforms(seg).values())
        subC = any(t <= set(C) for t in transforms(seg).values())
        L.append(f"| `{c}` | {bestA:.2f} | {subA} | {bestC:.2f} | {subC} |")

    L += ["", "### 3.2 全环 8px vs 图案", ""]
    for name, pat in (("A", A), ("C", C)):
        best = max((iou(outer, t), k) for k, t in transforms(pat).items())
        L.append(f"- 全环 vs `{name}`：最佳 IoU `{best[0]:.2f}`（变换 `{best[1]}`）")

    L += ["", "### 3.3 颜色对合并（4px）vs 图案", ""]
    colors = [9, 14, 8, 12]
    pairs = [(f"{colors[i]}+{colors[j]}", set(ring[colors[i]]) | set(ring[colors[j]]))
             for i in range(4) for j in range(i + 1, 4)]
    L.append("| 颜色对 | vs A 最佳 IoU | vs C 最佳 IoU |")
    L.append("|--------|--------------|--------------|")
    for pname, u in pairs:
        bA = max(iou(u, t) for t in transforms(A).values())
        bC = max(iou(u, t) for t in transforms(C).values())
        L.append(f"| `{pname}` | {bA:.2f} | {bC:.2f} |")

    L += ["", "### 3.4 叠加：图案每格落在色环哪个色（无变换）", ""]
    for name, pat in (("A（legend12 = stampL1）", A), ("C（stampL3）", C)):
        cnt = {}
        for cell in pat:
            c = next((k for k, v in ring.items() if cell in v), None)
            cnt[c] = cnt.get(c, 0) + 1
        L.append(f"- `{name}` 叠加 → {sorted(cnt.items(), key=lambda t: -t[1])}")

    L += [
        "",
        "---",
        "",
        "## 4. 结论（负结果，决定性）",
        "",
        "**「旋转颜色环使 color12 对齐 legend」被证伪。**",
        "",
        "原因不是不匹配，而是**匹配过多、无判别力**：颜色环的 8 个外圈格与目标图案",
        "的 6 个外圈格同属 3×3 外圈，故：",
        "- 单段 2px 恒能落入 6px 图案（IoU 恒 `2/6`，四个段全 subset=True）",
        "- 相邻两段合并 4px 落入（IoU 恒 `4/6`=0.67）；对角两段只有 `3/7`=0.43",
        "- 全环 8px 与图案 IoU 恒 `6/8`=0.75（图案就是它的 6 格外圈子集）",
        "",
        "几何对称变换**不提供唯一解**，因此「色环旋转 → 色12 对齐」不是可判别的规则。",
        "颜色环的几何匹配路径到此为止，不再继续穷举。",
        "",
        "## 5. 真正的信号（转移到颜色语义）",
        "",
        "穷举排除了「几何对齐」，反而凸显**颜色对称族**才是真信号（见",
        "`docs/ls20_l3_legend_alignment.md` §8）：",
        "",
        "| 图案 | 位置 | 关系 |",
        "|------|------|------|",
        "| B | legend L1（色9） | 基准（水平镜像前的） |",
        "| A | legend L2/L3（色12）、stamp L1（色9） | = fx(B) |",
        "| C | stamp L3（色9） | = rot180(A) |",
        "",
        "legend 卡片是色5（stamp 同色），内嵌目标色图案 => legend 是「stamp 块目标",
        "内嵌形状的对称变换预览」，legend 颜色 = match 材料。L3 材料=色12（mover），",
        "目标=把色12 摆成 A 形状（或让 stamp 呈现 C）。",
        "",
        "## 6. 下一步（按可证伪性排序）",
        "",
        "1. **线上 1 步证伪**：移动主 mover（色12），观察 levels 是否 2→3。这是对",
        "   「色12 是材料」的最直接判别（C2 已证「接触 plus 不武装」，但未证「色12",
        "   移动本身是否触发」）。",
        "2. **离线解 stamp 目标**：L3 stamp 嵌图 C（色9 6px）需要被「什么」填成——",
        "   mover（5×2 色12）无法精确填 6px 图案，故真正目标可能不是 mover 单块，",
        "   而是「mover + 漆」或「第二块」的组合。",
        "",
    ]

    txt = "\n".join(L) + "\n"
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
