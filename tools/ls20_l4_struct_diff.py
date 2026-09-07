"""Offline structural diff: ls20 L1-L4 start frames."""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import mover_bbox_from_cursor
from tools.ls20_seated_clear import _ov
from tools.ls20_seated_clear_full import _unlock_candidates

REPORT = ROOT / "docs" / "ls20_l4_struct_diff_l1l3.md"


def load(name: str):
    p = ROOT / "tests" / "fixtures" / f"{name}.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    return d["frame"] if isinstance(d, dict) and "frame" in d else d


def blobs(g, color, ymax=64):
    H, W = g.shape
    vis = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(min(ymax, H)):
        for x in range(W):
            if g[y, x] != color or vis[y, x]:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (
                        0 <= nx < W and 0 <= ny < H and ny < ymax
                        and not vis[ny, nx] and g[ny, nx] == color
                    ):
                        vis[ny, nx] = True
                        q.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            out.append((len(cells), (min(xs), min(ys), max(xs), max(ys))))
    return sorted(out, reverse=True)


def has_plus(g) -> bool:
    H, W = g.shape
    for y in range(min(54, H - 2)):
        for x in range(W - 2):
            patch = g[y : y + 3, x : x + 3]
            core = ((0, 1), (1, 0), (1, 1), (1, 2), (2, 1))
            if all(int(patch[dy, dx]) in (0, 1) for dx, dy in core):
                return True
    return False


def summarize(name: str, frame) -> dict:
    g = ls20._plane(frame)
    off = ls20.grid_offset(frame)
    st = ls20.init(frame)
    wu = ls20.build_walkable(frame, off, armed=False)
    wa = ls20.build_walkable(frame, off, armed=True)
    warps = ls20.detect_warps(frame, off, wu)
    pickups = ls20.energy_pickups(frame)
    stamp = next((x.shape for x in st.goals if x.id == "ls20-stamp"), None)
    marker = next((x.shape for x in st.goals if x.id == "ls20-marker"), None)
    gates = []
    if stamp is not None:
        for c in sorted(wa):
            if _ov(mover_bbox_from_cursor(c, off), stamp) >= 10:
                gates.append(c)
    counts = {int(v): int(c) for v, c in zip(*np.unique(g, return_counts=True))}
    return {
        "name": name,
        "mover": ls20.locate_mover(frame),
        "cursor": st.cursor,
        "marker": marker,
        "stamp": stamp,
        "has_plus": has_plus(g),
        "pickups": pickups,
        "n_warps": len(warps),
        "armed_only": sorted(wa - wu),
        "unlock": _unlock_candidates(frame),
        "gates": gates,
        "c14_play": blobs(g, 14, 54)[:4],
        "c1_blobs": len(blobs(g, 1, 54)),
        "ui": ls20.ui_energy(frame),
        "c0": counts.get(0, 0),
        "c1": counts.get(1, 0),
        "c8": counts.get(8, 0),
        "c9": counts.get(9, 0),
        "c11": counts.get(11, 0),
        "c12": counts.get(12, 0),
        "c14": counts.get(14, 0),
    }


def main() -> None:
    names = [
        "ls20_l1_frame_live",
        "ls20_l2_frame_live",
        "ls20_l3_frame_live",
        "ls20_l4_frame_live",
    ]
    rows = [summarize(n, load(n)) for n in names]
    l4 = rows[3]
    lines = [
        "# ls20 L4 vs L1–L3 结构差（离线）",
        "",
        "> 只消费 fixture 真帧；用于收窄 L4 武装假设。",
        "",
        "## 对照表",
        "",
        "| 项 | L1 | L2 | L3 | **L4** |",
        "|----|----|----|----|--------|",
    ]
    fields = [
        ("mover", "mover"),
        ("cursor", "cursor"),
        ("marker", "marker"),
        ("stamp", "stamp"),
        ("has_plus", "has_plus"),
        ("pickups", "pickups"),
        ("n_warps", "n_warps"),
        ("armed_only", "armed_only"),
        ("unlock", "unlock"),
        ("gates", "gates"),
        ("c14_play", "c14_play"),
        ("c1_blobs", "c1_blobs"),
        ("c0", "c0"),
        ("c8", "c8"),
        ("c9", "c9"),
        ("c12", "c12"),
        ("c14", "c14"),
    ]
    for label, key in fields:
        cells = " | ".join(f"`{r[key]}`" for r in rows)
        lines.append(f"| {label} | {cells} |")

    lines += [
        "",
        "## L4 相对 L1–L3 的突出差异",
        "",
    ]
    diffs = []
    if not l4["has_plus"] and any(r["has_plus"] for r in rows[:3]):
        diffs.append("- **无 plus marker**（L2/L3 有；L1 接触即武装也依赖 marker）")
    if l4["n_warps"] > rows[2]["n_warps"]:
        diffs.append(
            f"- **传送更多**：L4 warps={l4['n_warps']}（含水平中轨）；L3={rows[2]['n_warps']}"
        )
    if l4["gates"] and l4["gates"][0][1] <= 2:
        diffs.append(f"- **盖印门在顶部** `{l4['gates']}`；spawn 同在顶带 `{l4['cursor']}`")
    if l4["unlock"]:
        diffs.append(
            f"- 通用 unlock 仍命中 `{l4['unlock']}`，但线上环不可达 → **规则误报**"
        )
    if l4["c14_play"]:
        diffs.append(f"- playfield 色14：`{l4['c14_play']}`（环残片）；主色14 在底部图例")
    if l4["c8"] > 0:
        diffs.append(f"- 有色8（`{l4['c8']}` px），L1 通常无")
    diffs.append("- 图例色14 字形与 stamp 色9 字形 **尺度不同、无旋转匹配**（已离线核对）")
    diffs.append("- 门旁 `(2,1)` LEFT → 图例底板翻转（线上已结案：非解锁）")
    lines.extend(diffs)
    lines += [
        "",
        "## 由此导出的优先假设",
        "",
        "1. L4 不用 plus/UDD；武装物可能是 **补给状态 / 软重置 / 其它顶门几何**",
        "2. 不要再追环 unlock 与 legend 翻转",
        "3. 线上少次探针：双补给顺序 → 门旁；或别处耗尽能量看重生 walk",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote", REPORT)
    for r in rows:
        print(r["name"], "plus", r["has_plus"], "warps", r["n_warps"],
              "unlock", r["unlock"], "gates", r["gates"])


if __name__ == "__main__":
    main()
