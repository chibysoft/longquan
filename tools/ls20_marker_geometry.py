"""Offline marker geometry for ls20 (H1 arming-marker analysis).

L3 has THREE 5-pixel color-0/1 components of different shapes. `ls20.init`
currently keeps only the 3x3 one and discards the line segments. This script
dumps every component's exact pixel shape (rel_shape within bbox), its x-center
offset from the stamp column, and compares shapes against L2's seated arming
marker — so the H1 question ("which component is the arming marker?") can be
answered from geometry, before any online probe.

Read-only; no engine calls, no canned answers.
"""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20


def components(g, colors=(0, 1), ymax=54, min_area=3, max_area=12):
    """Connected components of `colors` above ymax, as (area, bbox, rel_shape)."""
    vis = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(g.shape[0]):
        for x in range(g.shape[1]):
            if g[y, x] not in colors or vis[y, x] or y >= ymax:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (0 <= nx < g.shape[1] and 0 <= ny < g.shape[0]
                            and not vis[ny, nx] and g[ny, nx] in colors):
                        vis[ny, nx] = True
                        q.append((nx, ny))
            if min_area <= len(cells) <= max_area:
                xs = [c[0] for c in cells]
                ys = [c[1] for c in cells]
                bb = (min(xs), min(ys), max(xs), max(ys))
                rel = tuple(sorted((cx - bb[0], cy - bb[1]) for cx, cy in cells))
                out.append((len(cells), bb, rel))
    out.sort(key=lambda t: (t[1][0], t[1][1]))
    return out


def shape_kind(rel):
    """Classify a 5-pixel shape: plus / hline / vline / other."""
    if rel == ((0, 1), (1, 0), (1, 1), (1, 2), (2, 1)):
        return "plus"
    if all(r[1] == 0 for r in rel):
        return "hline"
    if all(r[0] == 0 for r in rel):
        return "vline"
    return "other"


def analyze(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    g = ls20._plane(data["frame"])
    s = ls20.init(data["frame"])
    stamps = [gl.shape for gl in s.goals if gl.id == "ls20-stamp"]
    stamp = stamps[0] if stamps else None
    sx = (stamp[0] + stamp[2]) / 2 if stamp else None
    rows = []
    for area, bb, rel in components(g):
        cx = (bb[0] + bb[2]) / 2
        dx = (cx - sx) if sx is not None else None
        ov = 0
        if stamp is not None:
            ox0, ox1 = max(bb[0], stamp[0]), min(bb[2], stamp[2])
            ov = max(0, ox1 - ox0 + 1)
        rows.append({
            "bbox": bb, "area": area, "kind": shape_kind(rel),
            "rel_shape": rel, "x_center": cx, "dx_stamp": dx, "x_overlap": ov,
        })
    return stamp, rows


def main():
    l2_stamp, l2_rows = analyze("tests/fixtures/ls20_l2_frame_live.json")
    l3_stamp, l3_rows = analyze("tests/fixtures/ls20_l3_frame_live.json")
    l2_kind = l2_rows[0]["kind"] if l2_rows else None
    l2_rel = l2_rows[0]["rel_shape"] if l2_rows else None

    print(f"L2 stamp={l2_stamp} arming_marker_kind={l2_kind} rel={l2_rel}\n")
    print(f"L3 stamp={l3_stamp}\n")
    print(f"{'bbox':>20} {'area':>4} {'kind':>7} {'x_center':>8} {'dx_stamp':>8} {'x_overlap':>9} {'same_as_L2':>10}")
    for r in l3_rows:
        same = (r["kind"] == l2_kind)
        print(f"{str(r['bbox']):>20} {r['area']:>4} {r['kind']:>7} "
              f"{r['x_center']:>8.1f} {r['dx_stamp']:>8.1f} {r['x_overlap']:>9} {str(same):>10}")


if __name__ == "__main__":
    main()
