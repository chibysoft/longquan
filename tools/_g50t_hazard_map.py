"""g50t: map color-8 cells; try clear/dodge by walking top corridor; watch 8 motion."""
from __future__ import annotations

import json
sys_path_insert = True
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import BASE, _api_key  # noqa: E402

TAGS = ["g50t_recon"]
OUT = ROOT / "tests/fixtures/g50t_l1_hazard_map.json"


def H(key, j=False):
    h = {"X-API-Key": key, "Accept": "application/json"}
    if j:
        h["Content-Type"] = "application/json"
    return h


def plane(d):
    a = np.asarray(d["frame"], dtype=np.int64)
    return a[0] if a.ndim == 3 else a


def actor(g):
    H_, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    best = []
    for y in range(7, 48):
        for x in range(W):
            if seen[y, x] or int(g[y, x]) != 9:
                continue
            stack = [(x, y)]
            seen[y, x] = True
            cells = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 7 <= ny < 48 and not seen[ny, nx] and int(g[ny, nx]) == 9:
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            if 10 <= len(cells) <= 40 and len(cells) > len(best):
                best = cells
    if not best:
        return None
    xs = [c[0] for c in best]
    ys = [c[1] for c in best]
    return {
        "n": len(best),
        "cx": round(sum(xs) / len(xs), 2),
        "cy": round(sum(ys) / len(ys), 2),
        "box": [min(xs), min(ys), max(xs), max(ys)],
    }


def eights(g):
    ys, xs = np.where(g == 8)
    cells = list(zip(xs.tolist(), ys.tolist()))
    return {
        "n": len(cells),
        "cells": cells[:120],
        "ymin": int(ys.min()) if len(ys) else None,
        "ymax": int(ys.max()) if len(ys) else None,
        "xmin": int(xs.min()) if len(xs) else None,
        "xmax": int(xs.max()) if len(xs) else None,
    }


def body_ndiff(a, b):
    return int(np.sum(a[1:63] != b[1:63]))


def hud_lives(g):
    # color1 block at top
    return {
        "n1": int(np.sum(g[1:6, :] == 1)),
        "bar1": int(np.sum(g[63] == 1)),
        "top9": int(np.sum(g[1:6, 0:10] == 9)),
    }


def main():
    key = _api_key()
    s = requests.Session()
    card = s.post(
        f"{BASE}/api/scorecard/open", headers=H(key, True), json={"tags": TAGS}, timeout=30
    ).json()["card_id"]
    gid = s.get(f"{BASE}/api/games/g50t", headers=H(key), timeout=20).json()["game_id"]

    def reset():
        return s.post(
            f"{BASE}/api/cmd/RESET",
            headers=H(key, True),
            json={"card_id": card, "game_id": gid},
            timeout=30,
        ).json()

    def act(guid, aid):
        d = s.post(
            f"{BASE}/api/cmd/ACTION{aid}",
            headers=H(key, True),
            json={"game_id": gid, "guid": guid},
            timeout=30,
        ).json()
        if "guid" not in d:
            raise RuntimeError(str({k: d.get(k) for k in d if k != "frame"}))
        return d

    d = reset()
    g = plane(d)
    e0 = eights(g)
    print("initial 8", {k: e0[k] for k in e0 if k != "cells"})
    # print 8 occupancy by row
    rows = {}
    for x, y in e0["cells"]:
        rows.setdefault(y, []).append(x)
    rowsum = {y: (min(xs), max(xs), len(xs)) for y, xs in sorted(rows.items())}
    print("8 by row", rowsum)

    result = {"init8_rows": rowsum, "init8": {k: e0[k] for k in e0 if k != "cells"}}

    # March right along top into 8s; record n8 and whether we pass
    d = reset()
    g = plane(d)
    guid = d["guid"]
    right_log = []
    for i in range(20):
        d = act(guid, 4)
        guid = d["guid"]
        g2 = plane(d)
        e = eights(g2)
        a = actor(g2)
        right_log.append({
            "i": i,
            "body": body_ndiff(g, g2),
            "actor": a,
            "n8": e["n"],
            "8box": [e["xmin"], e["ymin"], e["xmax"], e["ymax"]],
            "lives": hud_lives(g2),
            "levels": d.get("levels_completed"),
            "state": d.get("state"),
        })
        print(
            f"R{i} body={right_log[-1]['body']} act={a} n8={e['n']} "
            f"lives={right_log[-1]['lives']} st={d.get('state')}"
        )
        g = g2
        if (d.get("levels_completed") or 0) >= 1:
            break
        if d.get("state") not in (None, "NOT_FINISHED"):
            break
    result["right_march"] = right_log

    # After going to edge of 8 zone, go down - does corridor clear?
    d = reset()
    g = plane(d)
    guid = d["guid"]
    # R to ~34 (about 3 effective = 4 presses from reset? 16+18=34 -> 3 steps, 4 presses)
    for i in range(4):
        d = act(guid, 4)
        guid = d["guid"]
        g = plane(d)
    mid = {"actor": actor(g), "n8": int(np.sum(g == 8)), "e": eights(g)}
    print("mid before down", mid["actor"], mid["n8"])
    down_log = []
    for i in range(12):
        d = act(guid, 2)
        guid = d["guid"]
        g2 = plane(d)
        down_log.append({
            "i": i,
            "body": body_ndiff(g, g2),
            "actor": actor(g2),
            "n8": int(np.sum(g2 == 8)),
            "lives": hud_lives(g2),
            "levels": d.get("levels_completed"),
        })
        print("D", i, down_log[-1])
        g = g2
    result["right_then_down"] = {"mid": mid, "down": down_log}

    # Destroy 8s: walk through them (R along y=10 into 8 column), see n8→0?
    # From ASCII 8s at top around x38-41 y9-12. Continue R.
    # Also try vertical along the 585 column from a position.

    # Check if 8s move when actor moves far (down shaft) — compare 8 masks
    d = reset()
    g = plane(d)
    guid = d["guid"]
    mask0 = (g == 8)
    for i in range(5):
        d = act(guid, 2)
        guid = d["guid"]
        g = plane(d)
    mask1 = (g == 8)
    moved8 = int(np.sum(mask0 != mask1))
    print("8 mask delta after D4", moved8, "n8", int(mask1.sum()))
    result["eight_delta_after_D4"] = {
        "delta": moved8,
        "n8": int(mask1.sum()),
        "actor": actor(g),
    }

    # Try bumping into 8 from above at (16,34) repeatedly — any progress / n8 drop?
    d = reset()
    g = plane(d)
    guid = d["guid"]
    for _ in range(5):
        d = act(guid, 2)
        guid = d["guid"]
        g = plane(d)
    bump = []
    for i in range(10):
        d = act(guid, 2)
        guid = d["guid"]
        g2 = plane(d)
        bump.append({
            "i": i,
            "body": body_ndiff(g, g2),
            "actor": actor(g2),
            "n8": int(np.sum(g2 == 8)),
            "lives": hud_lives(g2),
            "state": d.get("state"),
            "levels": d.get("levels_completed"),
        })
        print("BUMP", i, bump[-1])
        g = g2
    result["bump_8_at_bottom"] = bump

    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print("wrote", OUT)
    s.post(
        f"{BASE}/api/scorecard/close",
        headers=H(key, True),
        json={"card_id": card},
        timeout=15,
    )


if __name__ == "__main__":
    main()
