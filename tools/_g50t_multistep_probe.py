"""Ad-hoc g50t multi-step action probe (independent scorecard)."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import BASE, _api_key  # noqa: E402

TAGS = ["g50t_recon"]


def H(key: str, j: bool = False):
    h = {"X-API-Key": key, "Accept": "application/json"}
    if j:
        h["Content-Type"] = "application/json"
    return h


def plane(d):
    a = np.asarray(d["frame"], dtype=np.int64)
    return a[0] if a.ndim == 3 else a


def cc(g, colors, ymin=1, maxn=500):
    H_, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(ymin, H_):
        for x in range(W):
            c = int(g[y, x])
            if seen[y, x] or c not in colors:
                continue
            stack = [(x, y)]
            seen[y, x] = True
            cells = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy, int(g[cy, cx])))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (
                        0 <= nx < W
                        and ymin <= ny < H_
                        and not seen[ny, nx]
                        and int(g[ny, nx]) in colors
                    ):
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            if 1 <= len(cells) <= maxn:
                xs = [t[0] for t in cells]
                ys = [t[1] for t in cells]
                out.append({
                    "n": len(cells),
                    "cx": round(sum(xs) / len(xs), 2),
                    "cy": round(sum(ys) / len(xs), 2),
                    "box": [min(xs), min(ys), max(xs), max(ys)],
                    "cols": dict(Counter(t[2] for t in cells)),
                })
    out.sort(key=lambda b: (b["box"][1], b["box"][0]))
    return out


def diff_info(a, b):
    m = a != b
    ys, xs = np.where(m)
    cells = [(int(x), int(y), int(a[y, x]), int(b[y, x])) for y, x in zip(ys, xs)]
    return int(m.sum()), cells[:24]


def main():
    key = _api_key()
    s = requests.Session()
    card = s.post(
        f"{BASE}/api/scorecard/open", headers=H(key, True), json={"tags": TAGS}, timeout=30
    ).json()["card_id"]
    gid = s.get(f"{BASE}/api/games/g50t", headers=H(key), timeout=20).json()["game_id"]
    print("card", card, "gid", gid)

    def reset():
        return s.post(
            f"{BASE}/api/cmd/RESET",
            headers=H(key, True),
            json={"card_id": card, "game_id": gid},
            timeout=30,
        ).json()

    def act(guid, aid):
        return s.post(
            f"{BASE}/api/cmd/ACTION{aid}",
            headers=H(key, True),
            json={"game_id": gid, "guid": guid},
            timeout=30,
        ).json()

    for aid in [1, 2, 3, 4, 5]:
        d = reset()
        g = plane(d)
        guid = d["guid"]
        print("=== chain ACTION", aid, "===")
        print(" start c8", cc(g, {8})[:3])
        print(" start c1", cc(g, {1})[:3])
        print(" start small9", [b for b in cc(g, {9}) if b["n"] <= 40][:6])
        for step in range(6):
            d = act(guid, aid)
            guid = d["guid"]
            g2 = plane(d)
            nd, cells = diff_info(g, g2)
            print(
                f"  step{step} ndiff={nd} cells={cells[:10]} "
                f"c8={cc(g2, {8})[:2]} lv={d.get('levels_completed')} state={d.get('state')}"
            )
            g = g2

    print("=== mixed sequence ===")
    d = reset()
    g = plane(d)
    guid = d["guid"]
    print("start8", cc(g, {8})[:2], "hist", dict(zip(*np.unique(g, return_counts=True))))
    seq = [4, 4, 4, 4, 2, 2, 2, 2, 5, 1, 1, 3, 3, 5, 5, 5]
    for i, aid in enumerate(seq):
        d = act(guid, aid)
        guid = d["guid"]
        g2 = plane(d)
        nd, cells = diff_info(g, g2)
        print(
            f"  {i} A{aid} nd={nd} cells={cells[:8]} c8={cc(g2, {8})[:1]} "
            f"c1={cc(g2, {1})[:1]}"
        )
        g = g2

    # Compare two fresh RESETs for stability
    print("=== reset stability ===")
    g_a = plane(reset())
    g_b = plane(reset())
    nd, cells = diff_info(g_a, g_b)
    print("reset-vs-reset ndiff", nd, cells[:10])

    s.post(
        f"{BASE}/api/scorecard/close",
        headers=H(key, True),
        json={"card_id": card},
        timeout=15,
    )
    print("closed")


if __name__ == "__main__":
    main()
