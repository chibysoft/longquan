"""Offline gate-geometry analysis for ls20 L3 (NO engine — zero online cost).

Proves/answers, from saved frames only:
  A. (10,10) is the UNIQUE ov>=10 stamping cell in L3  (-> no "backdoor" cell).
  B. blocking analysis of (10,10): footprint colors + neighbor walkability.
  C. fuel budget for contact(9,2) -> stamp gate (armed path).
  D. L1/L2/L3 stamp glyph comparison (tests the A/B/C glyph-family hypothesis).
  E. L2 vs L3: does clearing require walking ONTO the color9 glyph, or not?

Red lines respected: reads only saved frames; never queries the engine.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_seated_clear import (
    MAX_FUEL, _energy_bfs, _ov, _ov_stamp, _step_cell,
)

FIX = ROOT / "tests" / "fixtures"
COLCHAR = {0: "0", 1: "1", 3: "3", 4: "4", 5: "#", 8: "8", 9: "G",
           11: "E", 12: "M", 14: "R"}


def load_frame(name: str):
    d = json.loads((FIX / name).read_text(encoding="utf-8"))
    fr = d["frame"] if isinstance(d, dict) and "frame" in d else d
    return np.asarray(fr, dtype=np.int8)


def plane(frame):
    return ls20._plane(frame)


def render_bbox(g, bbox, pad=1):
    x0, y0, x1, y1 = bbox
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(g.shape[1] - 1, x1 + pad), min(g.shape[0] - 1, y1 + pad)
    rows = []
    for y in range(y0, y1 + 1):
        rows.append("".join(COLCHAR.get(int(g[y, x]), "?") for x in range(x0, x1 + 1)))
    return "\n".join(rows)


def color9_in(g, bbox, pad=0):
    x0, y0, x1, y1 = bbox
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(g.shape[1] - 1, x1 + pad), min(g.shape[0] - 1, y1 + pad)
    pts = sorted((int(x), int(y)) for y in range(y0, y1 + 1)
                 for x in range(x0, x1 + 1) if g[y, x] == 9)
    return pts


def ov_cells(frame, min_ov=10):
    """All logical cells whose 5x2 footprint overlaps the stamp by >= min_ov."""
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    stamp = next(g.shape for g in state.goals if g.id == "ls20-stamp")
    out = []
    for cx in range(-2, 30):
        for cy in range(-2, 30):
            ov = _ov_stamp((cx, cy), offset, stamp)
            if ov >= min_ov:
                out.append((cx, cy, ov))
    return out, stamp, offset


def footprint_colors(g, cell, offset):
    px, py = ls20.cursor_to_pixel(cell, offset)
    return sorted(int(c) for c in g[py:py + 2, px:px + 5].flatten())


def main() -> None:
    levels = {
        "L1": load_frame("ls20_l1_frame_live.json"),
        "L2": load_frame("ls20_l2_frame_live.json"),
        "L3": load_frame("ls20_l3_frame_live.json"),
        "L3-dissolved": load_frame("ls20_l3_frame_dissolved.json"),
    }

    # ---- D/E: stamp glyph per level + ov>=10 cells + walkability ----
    print("=" * 72)
    print("D/E. 每关 stamp 字形 + ov>=10 唯一格 + 是否需踩 color9 字形")
    print("=" * 72)
    for name, fr in levels.items():
        g = plane(fr)
        try:
            state = ls20.init(fr)
        except Exception as e:
            print(f"[{name}] init fail: {e}")
            continue
        stamp = next((gg.shape for gg in state.goals if gg.id == "ls20-stamp"), None)
        if stamp is None:
            print(f"[{name}] no stamp")
            continue
        offset = ls20.grid_offset(fr)
        walk_u = ls20.build_walkable(fr, offset, armed=False)
        walk_a = ls20.build_walkable(fr, offset, armed=True)
        cells, _, _ = ov_cells(fr, 10)
        c9 = color9_in(g, stamp, pad=1)
        print(f"\n--- {name} ---")
        print(f"  stamp bbox = {stamp}")
        print(f"  color9 字形像素 (within stamp±1) = {c9}")
        print(f"  stamp 渲染:\n{render_bbox(g, stamp, pad=2)}")
        print(f"  ov>=10 的格子: {cells}")
        for (cx, cy, ov) in cells:
            inu = (cx, cy) in walk_u
            ina = (cx, cy) in walk_a
            fc = footprint_colors(g, (cx, cy), offset)
            print(f"    ({cx},{cy}) ov={ov}  walk_u={inu} walk_a={ina} "
                  f"footprint={fc}")

    # ---- A/B: L3 unique-cell proof + blocking ----
    print("\n" + "=" * 72)
    print("A/B. L3 (10,10) 唯一 ov>=10 + 阻挡分析")
    print("=" * 72)
    g = plane(levels["L3"])
    state = ls20.init(levels["L3"])
    offset = ls20.grid_offset(levels["L3"])
    stamp = next(gg.shape for gg in state.goals if gg.id == "ls20-stamp")
    walk_u = ls20.build_walkable(levels["L3"], offset, armed=False)
    walk_a = ls20.build_walkable(levels["L3"], offset, armed=True)
    cells, _, _ = ov_cells(levels["L3"], 10)
    print(f"stamp={stamp} offset={offset}")
    print(f"ov>=10 cells = {cells}")
    print(f"(10,10) footprint colors = {footprint_colors(g, (10,10), offset)}")
    gpx = ls20.cursor_to_pixel((10, 10), offset)
    print(f"(10,10) color9 inside = {color9_in(g, (gpx[0], gpx[1], gpx[0]+4, gpx[1]+1), pad=0)}")
    for nb in [(10, 9), (10, 11), (9, 10), (11, 10)]:
        print(f"  邻居 {nb}: walk_u={(nb in walk_u)} walk_a={(nb in walk_a)} "
              f"足迹={footprint_colors(g, nb, offset)}")

    # ---- C: fuel budget contact -> gate (armed) ----
    print("\n" + "=" * 72)
    print("C. L3 燃料预算: contact(9,2) -> stamp gate (armed)")
    print("=" * 72)
    pickups = ls20.energy_pickups(levels["L3"])
    ui = ls20.ui_energy(levels["L3"])
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))
    warps = ls20.detect_warps(levels["L3"], offset, walk_u)
    print(f"pickups={pickups} ui_energy={ui} fuel0={fuel0}")
    print(f"warps={ {str(k): v for k, v in warps.items()} }")
    # armed path from cursor to any ov>=10 cell
    start = state.cursor
    def at_stamp(cell, _f, _p):
        return _ov_stamp(cell, offset, stamp) >= 10
    p, c2, f2, pm2 = _energy_bfs(start, fuel0, 0, walk_a, pickups, offset,
                                 at_stamp, warps)
    print(f"cursor0={start} -> armed path to ov>=10: "
          f"{None if p is None else len(p)} steps, end={c2}, fuel={f2}")
    # unarmed path to ov>=10 (does it even need arming?)
    p_u, c2_u, f2_u, pm2_u = _energy_bfs(start, fuel0, 0, walk_u, pickups,
                                         offset, at_stamp, warps)
    print(f"cursor0={start} -> UNARMED path to ov>=10: "
          f"{None if p_u is None else len(p_u)} steps, end={c2_u}, fuel={f2_u}")
    # connectivity (no fuel) to (10,10)
    from collections import deque
    def reachable(walk, tgt):
        q = deque([start]); seen = {start}
        while q:
            c = q.popleft()
            if c == tgt:
                return True
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + d[0], c[1] + d[1])
                if n in walk and n not in seen:
                    seen.add(n); q.append(n)
        return False
    print(f"no-fuel connected to (10,10): walk_u={reachable(walk_u,(10,10))} "
          f"walk_a={reachable(walk_a,(10,10))}")


if __name__ == "__main__":
    main()
