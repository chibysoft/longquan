"""g50t: build walkable mask (color5), BFS path, execute with command buffer."""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import BASE, _api_key  # noqa: E402

TAGS = ["g50t_recon"]
OUT = ROOT / "tests/fixtures/g50t_l1_bfs_try.json"
STEP = 6  # actor center moves by 6


def H(key, j=False):
    h = {"X-API-Key": key, "Accept": "application/json"}
    if j:
        h["Content-Type"] = "application/json"
    return h


def plane(d):
    a = np.asarray(d["frame"], dtype=np.int64)
    return a[0] if a.ndim == 3 else a


def actor_cells(g):
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
                    if (
                        0 <= nx < W
                        and 7 <= ny < 48
                        and not seen[ny, nx]
                        and int(g[ny, nx]) == 9
                    ):
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            if 10 <= len(cells) <= 40 and len(cells) > len(best):
                best = cells
    return best


def actor(g):
    cells = actor_cells(g)
    if not cells:
        return None
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    return {
        "n": len(cells),
        "cx": round(sum(xs) / len(xs), 2),
        "cy": round(sum(ys) / len(ys), 2),
        "box": [min(xs), min(ys), max(xs), max(ys)],
        "cells": cells,
    }


def goal(g):
    H_, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    best = None
    for y in range(45, 62):
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
                    if (
                        0 <= nx < W
                        and 45 <= ny < 62
                        and not seen[ny, nx]
                        and int(g[ny, nx]) == 9
                    ):
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            if not cells:
                continue
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            blob = {
                "n": len(cells),
                "cx": round(sum(xs) / len(xs), 2),
                "cy": round(sum(ys) / len(ys), 2),
                "box": [min(xs), min(ys), max(xs), max(ys)],
            }
            if best is None or blob["n"] > best["n"]:
                best = blob
    return best


def footprint_ok(g, cx, cy, ignore_8=False):
    """Actor is 5x5 centered near (cx,cy); check all cells walkable.
    Walkable: color in {5,9} (floor or self). Optionally forbid 8.
    """
    # box from observed: half-width 2
    x0, x1 = int(cx) - 2, int(cx) + 2
    y0, y1 = int(cy) - 2, int(cy) + 2
    H_, W = g.shape
    if x0 < 0 or y0 < 1 or x1 >= W or y1 >= 63:
        return False
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            v = int(g[y, x])
            if v in (5, 9):
                continue
            if ignore_8 and v == 8:
                continue
            if v == 8 and not ignore_8:
                return False
            # 0 or other = blocked
            return False
    return True


def body_ndiff(a, b):
    return int(np.sum(a[1:63] != b[1:63]))


def bfs(g, start, goal_xy, allow_8=False):
    sx, sy = int(start[0]), int(start[1])
    gx, gy = int(goal_xy[0]), int(goal_xy[1])
    # snap goal to nearest reachable center on STEP grid from start
    q = deque([(sx, sy)])
    prev = {(sx, sy): None}
    dirs = [(0, -STEP, 1), (0, STEP, 2), (-STEP, 0, 3), (STEP, 0, 4)]  # U D L R
    while q:
        x, y = q.popleft()
        if abs(x - gx) + abs(y - gy) <= 3:
            # reconstruct
            path = []
            cur = (x, y)
            while prev[cur] is not None:
                p, aid = prev[cur]
                path.append(aid)
                cur = p
            path.reverse()
            return path, (x, y)
        for dx, dy, aid in dirs:
            nx, ny = x + dx, y + dy
            if (nx, ny) in prev:
                continue
            if not footprint_ok(g, nx, ny, ignore_8=allow_8):
                continue
            prev[(nx, ny)] = ((x, y), aid)
            q.append((nx, ny))
    return None, None


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

    d0 = reset()
    g0 = plane(d0)
    a0 = actor(g0)
    gl = goal(g0)
    print("start", a0, "goal", gl)

    # Map walkable centers on STEP grid
    walk = []
    for cy in range(10, 55, STEP):
        for cx in range(16, 50, STEP):
            ok = footprint_ok(g0, cx, cy, ignore_8=False)
            ok8 = footprint_ok(g0, cx, cy, ignore_8=True)
            if ok or ok8:
                walk.append({"cx": cx, "cy": cy, "ok": ok, "ok_ignore8": ok8, "center": int(g0[cy, cx])})
    print("walkable centers", len(walk), "strict", sum(1 for w in walk if w["ok"]))

    path, end = bfs(g0, (int(a0["cx"]), int(a0["cy"])), (int(gl["cx"]), int(gl["cy"])), allow_8=False)
    path8, end8 = bfs(g0, (int(a0["cx"]), int(a0["cy"])), (int(gl["cx"]), int(gl["cy"])), allow_8=True)
    print("BFS no8", path, "end", end)
    print("BFS allow8", path8, "end", end8)

    # Also BFS to each walkable near goal band
    near_goal = [w for w in walk if w["cy"] >= 40 and w["ok"]]
    print("near_goal strict", near_goal[:10], "n", len(near_goal))

    results = {
        "start": a0,
        "goal": gl,
        "walk_n": len(walk),
        "walk_strict": sum(1 for w in walk if w["ok"]),
        "walk_sample": walk[:40],
        "bfs": {"path": path, "end": end},
        "bfs8": {"path": path8, "end": end8},
        "near_goal": near_goal,
    }

    def execute_buffered(path_aids, label):
        """Execute path with 1-step buffer: send path + final flush duplicate of last."""
        if not path_aids:
            return {"label": label, "error": "empty"}
        d = reset()
        g = plane(d)
        guid = d["guid"]
        # From RESET empty queue: first command only queues. So send path as-is
        # (first becomes queue), then flush with repeat of last OR a harmless press.
        cmds = list(path_aids) + [path_aids[-1]]  # extra to flush last move
        log = []
        for i, aid in enumerate(cmds):
            d = act(guid, aid)
            guid = d["guid"]
            g2 = plane(d)
            log.append({
                "i": i,
                "a": aid,
                "body": body_ndiff(g, g2),
                "actor": {k: actor(g2)[k] for k in ("n", "cx", "cy", "box")} if actor(g2) else None,
                "n8": int(np.sum(g2 == 8)),
                "levels": d.get("levels_completed"),
                "state": d.get("state"),
            })
            g = g2
            if (d.get("levels_completed") or 0) >= 1:
                break
        print(label, "lv", log[-1]["levels"], "end", log[-1]["actor"], "len", len(log))
        return {"label": label, "cmds": cmds, "levels": log[-1]["levels"], "log": log}

    if path:
        results["exec_no8"] = execute_buffered(path, "no8")
    if path8 and path8 != path:
        results["exec_allow8"] = execute_buffered(path8, "allow8")

    # Try BFS to deepest reachable without 8, then explore
    # Find farthest cy reachable
    best_path = None
    best_end = None
    for w in sorted(walk, key=lambda z: (-z["cy"], -z["cx"])):
        if not w["ok"]:
            continue
        p, e = bfs(g0, (int(a0["cx"]), int(a0["cy"])), (w["cx"], w["cy"]), allow_8=False)
        if p is not None:
            best_path, best_end = p, e
            break
    print("farthest", best_end, "pathlen", None if best_path is None else len(best_path))
    results["farthest"] = {"end": best_end, "path": best_path}
    if best_path:
        results["exec_farthest"] = execute_buffered(best_path, "farthest")

    # Probe: from start, which single-step targets are footprint_ok?
    probes = {}
    for name, (dx, dy) in {"U": (0, -6), "D": (0, 6), "L": (-6, 0), "R": (6, 0)}.items():
        nx, ny = int(a0["cx"]) + dx, int(a0["cy"]) + dy
        probes[name] = {
            "target": (nx, ny),
            "ok": footprint_ok(g0, nx, ny),
            "ok8": footprint_ok(g0, nx, ny, True),
            "cells": [int(g0[ny + oy, nx + ox]) for oy in range(-2, 3) for ox in range(-2, 3)],
        }
    results["step_probes"] = probes
    print("probes", probes)

    # What about from (16,34)?
    d = reset()
    g = plane(d)
    guid = d["guid"]
    for _ in range(5):
        d = act(guid, 2)
        guid = d["guid"]
        g = plane(d)
    a = actor(g)
    probes34 = {}
    if a:
        for name, (dx, dy) in {"U": (0, -6), "D": (0, 6), "L": (-6, 0), "R": (6, 0)}.items():
            nx, ny = int(a["cx"]) + dx, int(a["cy"]) + dy
            probes34[name] = {
                "target": (nx, ny),
                "ok": footprint_ok(g, nx, ny),
                "ok8": footprint_ok(g, nx, ny, True),
                "cells": [int(g[ny + oy, nx + ox]) for oy in range(-2, 3) for ox in range(-2, 3)]
                if 2 <= ny <= 60
                else None,
            }
    results["probes_at_16_34"] = {"actor": a, "probes": probes34}
    print("at34", a, probes34)

    # ASCII walkable strip around actor row
    def row_scan(g, y):
        return "".join(
            {0: ".", 5: "5", 8: "8", 9: "9"}.get(int(g[y, x]), str(int(g[y, x])))
            for x in range(10, 55)
        )

    results["rows"] = {str(y): row_scan(g0, y) for y in list(range(7, 43)) + list(range(48, 56))}

    OUT.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("wrote", OUT)
    s.post(
        f"{BASE}/api/scorecard/close",
        headers=H(key, True),
        json={"card_id": card},
        timeout=15,
    )


if __name__ == "__main__":
    main()
