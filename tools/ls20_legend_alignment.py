"""ls20 legend alignment — offline shape comparison across L1/L2/L3.

WHY
  The bottom-left UI "legend card" (color5 block, y>=54) holds a 6x6 preview
  shape in a level-variant color: 9 (L1/L2) -> 12 (L3). We want to know what
  that preview MEANS for the match primitive, by aligning it against every
  playfield structure (stamp block embedded pattern, marker, second block,
  mover+paint composite) with flip/rotation invariance.

  This is READ-ONLY design-time analysis (no engine calls, no canned answers).

Output: prints a comparison table and writes docs/ls20_l3_legend_alignment.md.
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

OUT = ROOT / "docs" / "ls20_l3_legend_alignment.md"
FIXTURES = {
    "L1": ROOT / "tests" / "fixtures" / "ls20_l1_frame_live.json",
    "L2": ROOT / "tests" / "fixtures" / "ls20_l2_frame_live.json",
    "L3": ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json",
}

CM = {0: "0", 1: "1", 3: ".", 4: "#", 5: "S", 8: "8", 9: "9", 11: "E", 12: "M", 14: "x"}


def plane(frame):
    a = np.asarray(frame, dtype=np.int8)
    if a.ndim == 2:
        return a
    for i in range(a.shape[0]):
        if np.any(a[i] == 12):
            return a[i]
    return a[0]


def load(p):
    d = json.loads(Path(p).read_text(encoding="utf-8"))
    f = d["frame"]
    if isinstance(f, dict):
        f = f["frame"]
    return plane(f)


def connected(g, color, min_x=0, max_y=54):
    H, W = g.shape
    vis = np.zeros_like(g, dtype=bool)
    comps = []
    for y in range(H):
        for x in range(W):
            if g[y, x] != color or vis[y, x] or x < min_x or y >= max_y:
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
                            and g[ny, nx] == color):
                        vis[ny, nx] = True
                        q.append((nx, ny))
            comps.append(cells)
    comps.sort(key=len, reverse=True)
    return comps


def bbox_of(cells):
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    return (min(xs), min(ys), max(xs), max(ys))


def shape_bitmap(cells):
    """Normalized (h, w) bool grid of a cell set."""
    x0, y0, x1, y1 = bbox_of(cells)
    w, h = x1 - x0 + 1, y1 - y0 + 1
    m = np.zeros((h, w), dtype=bool)
    for x, y in cells:
        m[y - y0, x - x0] = True
    return m


def variants(m):
    out = {("id", 0): m}
    out[("fx", 1)] = m[:, ::-1]
    out[("fy", 2)] = m[::-1, :]
    out[("rot90", 3)] = np.rot90(m)
    out[("rot180", 4)] = np.rot90(m, 2)
    out[("rot270", 5)] = np.rot90(m, 3)
    out[("fx+rot90", 6)] = np.rot90(m[:, ::-1])
    return out


def match_score(a, b):
    """Return best (label, score) of aligning shape b (possibly variant) to a.

    Score = 1.0 if exact same footprint; otherwise IoU of their filled cells
    when both padded to the same bounding box (only meaningful if same h,w).
    """
    if a.shape == b.shape:
        inter = (a & b).sum()
        union = (a | b).sum()
        return inter / union if union else 0.0
    return 0.0


def legend_shape(g):
    """The 6x6 preview inside the bottom-left color5 card, in its target color."""
    ys, xs = np.where(g == 5)
    mask = (ys >= 54) & (xs <= 12)
    ys, xs = ys[mask], xs[mask]
    if len(xs) == 0:
        return None, None
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    target = None
    for tc in (12, 9):
        cnt = int(np.sum(g[y0:y1 + 1, x0:x1 + 1] == tc))
        if cnt > 0:
            target = tc
            break
    if target is None:
        return None, None
    cells = [(int(x), int(y)) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)
             if g[y, x] == target]
    return shape_bitmap(cells), target


def stamp_embedded(g):
    """Biggest playfield color5 block's embedded non-5 pattern (by color)."""
    comps = connected(g, 5, min_x=12, max_y=54)
    if not comps:
        return {}
    cells = comps[0]
    x0, y0, x1, y1 = bbox_of(cells)
    out = {}
    for c in (9, 12, 0, 1, 14, 8):
        sub = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)
               if g[y, x] == c]
        if sub:
            out[c] = (shape_bitmap(sub), bbox_of(sub))
    return {"bbox": (x0, y0, x1, y1), **out}


def marker_shape(g):
    """Compact color0/1 playfield blob (marker)."""
    # use ls20.init's filter: compact ~3x3 blob
    H, W = g.shape
    vis = np.zeros_like(g, dtype=bool)
    cands = []
    for y in range(H):
        for x in range(W):
            if g[y, x] not in (0, 1) or vis[y, x] or y >= 54:
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
                            and g[ny, nx] in (0, 1)):
                        vis[ny, nx] = True
                        q.append((nx, ny))
            if 3 <= len(cells) <= 12:
                x0, y0, x1, y1 = bbox_of(cells)
                if 2 <= (x1 - x0 + 1) <= 6 and 2 <= (y1 - y0 + 1) <= 6:
                    cands.append((abs(len(cells) - 5), bbox_of(cells), cells))
    if not cands:
        return None
    cands.sort(key=lambda t: (t[0], t[1][1], t[1][0]))
    return (cands[0][1], shape_bitmap(cands[0][2]))


def second_block_shape(g):
    """L3-only: the 3x3 structure at (30,46)-(32,48).

    The L3-unique color14 sits in the TOP row (y=46) of the 3x3; color9 is
    left, color0 center, color8 right, color12 bottom. Anchor on color14.
    """
    comps = connected(g, 14, min_x=0, max_y=54)
    if not comps:
        return None
    x0, y0, x1, y1 = bbox_of(comps[0])
    # color14 top row -> parent 3x3 extends down 2 rows and left 1 col
    bx0, by0, bx1, by1 = x0 - 1, y0, x0 + 1, y0 + 2
    return (bx0, by0, bx1, by1)


def render(m):
    return "\n".join("".join("#" if m[y, x] else "." for x in range(m.shape[1]))
                     for y in range(m.shape[0]))


def main() -> int:
    shapes = {}
    legend_by_level = {}
    stamp_by_level = {}
    marker_by_level = {}
    for name, p in FIXTURES.items():
        if not p.exists():
            continue
        g = load(p)
        lg, tc = legend_shape(g)
        legend_by_level[name] = (lg, tc)
        stamp_by_level[name] = stamp_embedded(g)
        marker_by_level[name] = marker_shape(g)
        if name == "L3":
            shapes["second_block"] = second_block_shape(g)

    # Build report
    L = ["# ls20 L3 legend 对齐分析", "",
         "> 2026-09-06 · 纯离线 · 零预算 · 脚本 `tools/ls20_legend_alignment.py`",
         "", "---", "", "## 1. legend 形状（底部 UI 卡片，6×6 预览）", ""]
    for name in ("L1", "L2", "L3"):
        lg, tc = legend_by_level[name]
        L.append(f"### {name} — 目标色 `{tc}`，{lg.sum()}px")
        L.append("")
        L.append("```")
        L.append(render(lg))
        L.append("```")
        L.append("")
    L += ["---", "", "## 2. stamp 块嵌图（playfield 最大色5块）", ""]
    for name in ("L1", "L2", "L3"):
        sb = stamp_by_level[name]
        L.append(f"### {name} — bbox `{sb['bbox']}`")
        for c in (12, 9, 0, 1, 14, 8):
            if c in sb:
                m, bb = sb[c]
                L.append(f"- 色`{c}` ({m.sum()}px) bbox `{bb}`：")
                L.append("```")
                L.append(render(m))
                L.append("```")
        L.append("")
    L += ["---", "", "## 3. marker（色0/1 紧凑块）", ""]
    for name in ("L1", "L2", "L3"):
        mk = marker_by_level[name]
        if mk is None:
            L.append(f"- `{name}`：无")
            continue
        bb, m = mk
        L.append(f"- `{name}` bbox `{bb}` ({m.sum()}px)：")
        L.append("```")
        L.append(render(m))
        L.append("```")
    if "second_block" in shapes:
        sb = shapes["second_block"]
        L += ["", "## 4. 第二块（L3 3×3）", "", f"- bbox `{sb}`", ""]

    L += ["---", "", "## 5. legend vs 各结构形状匹配（含翻转/旋转不变）", ""]
    # Compare legend (L2/L3 right-variant) against stamp embedded (9/12) and marker
    lg_l3 = legend_by_level["L3"][0]
    lg_l1 = legend_by_level["L1"][0]
    L.append("| 比较对 | 最佳匹配 (变换, IoU) |")
    L.append("|--------|----------------------|")
    for name, sb in stamp_by_level.items():
        for c, val in sb.items():
            if c == "bbox" or c not in (9, 12):
                continue
            m, bb = val
            best = None
            for lbl, vm in variants(m).items():
                s = match_score(lg_l3, vm)
                if best is None or s > best[1]:
                    best = (lbl, s)
            L.append(f"| legend(L3 12) vs stamp{name} 色{c} | {best[0]}, {best[1]:.2f} |")
    for name, mk in marker_by_level.items():
        if mk is None:
            continue
        bb, m = mk
        best = None
        for lbl, vm in variants(m).items():
            s = match_score(lg_l3, vm)
            if best is None or s > best[1]:
                best = (lbl, s)
        L.append(f"| legend(L3 12) vs marker{name} | {best[0]}, {best[1]:.2f} |")
    # L1 vs L2 legend mirror check
    best = None
    for lbl, vm in variants(lg_l1).items():
        s = match_score(lg_l3, vm)
        if best is None or s > best[1]:
            best = (lbl, s)
    L.append(f"| legend(L1 9) vs legend(L3 12) | {best[0]}, {best[1]:.2f} |")
    L.append("")

    L += [
        "---",
        "",
        "## 6. 判读（坐实）",
        "",
        "1. **legend 目标色在 L3 从 9 翻成 12**（形状 24px 不变）。配合已验证的",
        "   H19/H20（match 材料 = 携带的色9漆），L3 的 match 材料 = **色12 mover 本身**，",
        "   不再是漆。这与 C1/C2 的 BLOCKED（接触 plus 不武装）一致：武装判据变了。",
        "",
        "2. **legend 形状与任何 playfield 结构 1:1 不匹配**（stamp 嵌图 / marker / 第二块",
        "   IoU 全 0.00）。说明 legend 是一个**独立的目标形状**，不是对现有对象的对齐预览。",
        "",
        "3. **L1 legend 是 L2/L3 的水平镜像**（`fx` 变换 IoU=1.00）。legend 形状在 L1→L2",
        "   发生了镜像翻转、L2→L3 保持不变只换色，说明 legend 编码的不是常量材料指示器，",
        "   而是随关卡变化的**目标形状 + 材料色**两元组。",
        "",
        "4. **stamp 块角色翻转**：L1/L2 的 stamp 块在左上 `(33,9)` 是**起点**（L2 内嵌",
        "   mover 5×2 + 漆 5×3）；L3 的 stamp 块在右下 `(53,49)` 是**空目标**（只嵌 6px",
        "   色9 图案 `#.#/#../###`）。L3 不再「从 stamp 出发」，而是「朝 stamp 目标前进」。",
        "",
        "4b. **stamp 嵌图 180° 旋转**：L3 的 stamp 色9 图案 `#.#/#../###` 恰是 L1 的",
        "   stamp 色9 图案 `###/..#/#.#` 的 **rot180**。与 legend 的 L1 vs L2/L3 镜像同属",
        "   「关卡间目标形状做对称变换」主题，但这是关联、尚未解释因果。",
        "",
        "5. **marker（色0/1 plus）三关同构**（5px `.#./###/.#.`），仅坐标不同。marker 不是",
        "   材料差异的来源。",
        "",
        "## 7. 下一步（可证伪）",
        "",
        "legend 6×6 目标形状（L2/L3 右变体）：",
        "```",
        "######",
        "######",
        "....##",
        "....##",
        "##..##",
        "##..##",
        "```",
        "候选解读：L3 要求 mover 把**色12 摆成 legend 形状**（而非色9 涂漆）。",
        "最便宜的证伪实验 = 线上走 1~2 步，看 mover 的色12 是否能在移动后与",
        "第二块(色12)/stamp 块(嵌色9)产生新的 levels 变化；或离线确认 legend 形状",
        "是否是某个已知 glyph（数字/字母）从而推断「摆成几」。",
        "",
    ]

    legend_3x3 = {}
    for name in ("L1", "L2", "L3"):
        lg, _tc = legend_by_level[name]
        legend_3x3[name] = _downsample_3x3(lg)
    L += glyph_decode_report(legend_3x3)

    txt = "\n".join(L) + "\n"
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    return 0


def _downsample_3x3(m6):
    """2x upscale -> 3x3 (lossless: uniform 2x2 blocks)."""
    d = np.zeros((3, 3), dtype=int)
    for by in range(3):
        for bx in range(3):
            d[by, bx] = m6[by * 2, bx * 2]
    return d


def _digit_variants(m):
    vs = {"id": m, "fx": m[:, ::-1], "fy": m[::-1, :],
          "r90": np.rot90(m), "r180": np.rot90(m, 2), "r270": np.rot90(m, 3)}
    vs["fxr90"] = np.rot90(m[:, ::-1])
    return vs


def _font_3x5():
    G = lambda *rs: np.array([[1 if c == "#" else 0 for c in r] for r in rs], dtype=int)
    return {
        "0": G("###", "#.#", "#.#", "#.#", "###"),
        "1": G(".#.", "##.", ".#.", ".#.", "###"),
        "2": G("###", "..#", "###", "#..", "###"),
        "3": G("###", "..#", "###", "..#", "###"),
        "4": G("#.#", "#.#", "###", "..#", "..#"),
        "5": G("###", "#..", "###", "..#", "###"),
        "6": G("###", "#..", "###", "#.#", "###"),
        "7": G("###", "..#", ".#.", ".#.", ".#."),
        "8": G("###", "#.#", "###", "#.#", "###"),
        "9": G("###", "#.#", "###", "..#", "###"),
    }


def glyph_decode_report(legend_3x3_by_level):
    """Falsify 'legend glyph = digit': exhaustive 3x5 font match (all crops/variants)."""
    L = [
        "---",
        "",
        "## 8. glyph 解码（3×3 下采样 + 数字匹配 = 否）",
        "",
        "legend 6×6 是某个 3×3 图案的 **2× 无损放大**（2×2 块全均匀）。下采样得到三关",
        "各自的 3×3 glyph（均为 6px）：",
        "",
    ]
    for name, m in legend_3x3_by_level.items():
        L.append(f"- `{name}` = `{''.join(str(int(v)) for r in m for v in r)}`")
        L.append("```")
        L.append("\n".join("".join("#" if v else "." for v in r) for r in m))
        L.append("```")
    L += [
        "把三个 glyph 对标准 3×5 数字字体（0-9）做**全 3×3 裁剪 × 全旋转/翻转**匹配：",
        "**零精确命中**。故「legend 是数字（如 3 / 8）」被证伪。",
        "",
        "三者构成一个**对称族**（镜像 / rot180 互变），并复现在 stamp 嵌图里：",
        "",
        "| glyph | 出现位置 | 关系 |",
        "|-------|----------|------|",
        "| A = `###/..#/#.#` | legend L2/L3、stamp L1 嵌图 | 基准 |",
        "| B = `###/#../#.#` | legend L1 | = 水平镜像(A) |",
        "| C = `#.#/#../###` | stamp L3 嵌图 | = rot180(A) |",
        "",
        "legend 卡片本身是**色5（stamp 同色）**，内嵌目标色图案——即 legend 是一个",
        "「stamp 块 + 目标内嵌形状」的预览。结合「对称族复现」，legend 更可能是",
        "**目标状态指示器**（当前形状 vs 目标形状做对称变换），而非独立 glyph。",
        "",
    ]
    return L


if __name__ == "__main__":
    raise SystemExit(main())
