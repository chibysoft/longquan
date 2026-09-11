"""Compare color15 walkability e8=52 vs persist36; BFS walkable centers.

tags=["g50t_recon"]
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    d = json.loads((ROOT / "tests/fixtures" / name).read_text(encoding="utf-8"))
    g = np.array(d["frame"], dtype=np.uint8)
    if g.ndim == 3:
        g = g[0]
    return g, d.get("pos"), d.get("e8")


def walk_score(g, x, y):
    sub = g[max(0, y - 2) : y + 3, max(0, x - 2) : x + 3]
    return int((sub == 5).sum()), int((sub == 15).sum()), int((sub == 0).sum())


def main():
    for name in ["g50t_l4_frame_live.json", "g50t_l4_at1040_frame.json", "g50t_l4_rightcol_live.json"]:
        p = ROOT / "tests/fixtures" / name
        if not p.exists():
            print("missing", name)
            continue
        g, pos, e = load(name)
        print("==", name, "pos", pos, "e8", e)
        for y in (22, 28, 34, 40, 46, 52):
            row = []
            for x in (10, 16, 22, 28, 34, 40, 46, 52):
                n5, n15, n0 = walk_score(g, x, y)
                # treat walkish if n5>=12 or (n5+n15)>=20 and n0<10
                ok = "Y" if n5 >= 12 or (n5 + n15 >= 18 and n0 <= 8) else "."
                row.append(f"{x}:{ok}{n5:02d}/{n15:02d}")
            print(f" y{y}", " ".join(row))
        # diff c15 mask vs floor adjacency
        c15 = g == 15
        floor = g == 5
        # cells of c15 adjacent to floor
        from collections import deque

        # BFS from (28,10) on cells where n5>=12 at step-6 grid, also allow n5+n15>=18
        starts = [(28, 10), (10, 40), (52, 28), (52, 10)]
        for sx, sy in starts:
            if sx > 60:
                continue
            q = deque([(sx, sy)])
            seen = {(sx, sy)}
            reach = []
            while q:
                x, y = q.popleft()
                reach.append((x, y))
                for dx, dy in ((6, 0), (-6, 0), (0, 6), (0, -6)):
                    nx, ny = x + dx, y + dy
                    if not (4 <= nx <= 58 and 4 <= ny <= 58):
                        continue
                    if (nx, ny) in seen:
                        continue
                    n5, n15, n0 = walk_score(g, nx, ny)
                    if n5 >= 12 or (n5 + n15 >= 18 and n0 <= 8):
                        seen.add((nx, ny))
                        q.append((nx, ny))
            goals = [c for c in reach if c[1] >= 46 or (c[0] <= 12 and c[1] >= 46)]
            print(f"  BFS from {(sx,sy)}: n={len(reach)} bottomish={goals[:8]} has1052={(10,52) in seen} has2852={(28,52) in seen}")


if __name__ == "__main__":
    main()
