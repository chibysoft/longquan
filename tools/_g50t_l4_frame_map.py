"""Map L4 at1040 frame connectivity. tags=['g50t_recon']"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
d = json.loads((ROOT / "tests/fixtures/g50t_l4_at1040_frame.json").read_text(encoding="utf-8"))
g = np.array(d["frame"], dtype=np.uint8)
if g.ndim == 3:
    g = g[0]
print("shape", g.shape, "pos", d.get("pos"), "e8info", d.get("e8"))
h = {int(v): int((g == v).sum()) for v in np.unique(g)}
print("hist", h)
ys, xs = np.where(g == 8)
print("snake n", len(xs), "x", int(xs.min()), int(xs.max()), "y", int(ys.min()), int(ys.max()))
print("--- grid n5 / tags S=snake C=c15 G=goal W=walk ---")
for y in range(4, 60, 6):
    cells = []
    for x in range(4, 58, 6):
        sub = g[max(0, y - 2) : min(64, y + 3), max(0, x - 2) : min(64, x + 3)]
        n5 = int((sub == 5).sum())
        n15 = int((sub == 15).sum())
        n8 = int((sub == 8).sum())
        n9 = int((sub == 9).sum())
        tag = ""
        if n8:
            tag += "S"
        if n15 >= 5:
            tag += "C"
        if n9 >= 5:
            tag += "G"
        if n5 >= 15:
            tag += "W"
        elif n5 >= 8:
            tag += "w"
        if not tag:
            tag = "."
        cells.append(f"{x}:{n5:02d}{tag}")
    print(f"y{y:02d}", " ".join(cells))


def comps(val: int):
    mask = g == val
    visited = np.zeros_like(mask)
    out = []
    for y in range(64):
        for x in range(64):
            if mask[y, x] and not visited[y, x]:
                stack = [(y, x)]
                visited[y, x] = True
                pts = []
                while stack:
                    cy, cx = stack.pop()
                    pts.append((cy, cx))
                    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < 64 and 0 <= nx < 64 and mask[ny, nx] and not visited[ny, nx]:
                            visited[ny, nx] = True
                            stack.append((ny, nx))
                ys2 = [p[0] for p in pts]
                xs2 = [p[1] for p in pts]
                out.append(
                    (
                        len(pts),
                        round(float(np.mean(xs2)), 1),
                        round(float(np.mean(ys2)), 1),
                        min(xs2),
                        max(xs2),
                        min(ys2),
                        max(ys2),
                    )
                )
    return sorted(out, reverse=True)


print("c15 comps", comps(15)[:12])
print("c9 comps", comps(9)[:8])
for y in range(26, 31):
    xs_row = np.where(g[y] == 8)[0]
    if len(xs_row):
        print("snake y", y, "x", int(xs_row.min()), "..", int(xs_row.max()), "n", len(xs_row))
# tip candidates: snake cells adjacent to color5 corridors at step-6 centers
print("--- candidate tips (snake near walkable) ---")
for y in (22, 28, 34, 40):
    for x in range(10, 52, 6):
        if g[y, x] == 8:
            neigh5 = int((g[max(0, y - 3) : y + 4, max(0, x - 3) : x + 4] == 5).sum())
            print(f"  snake@({x},{y}) neigh5={neigh5}")
