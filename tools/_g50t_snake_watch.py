"""g50t: mid-band routing; timer watch on hazard; eat-snake follow-ups."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import BASE, _api_key  # noqa: E402

TAGS = ["g50t_recon"]
OUT = ROOT / "tests/fixtures/g50t_l1_snake_watch.json"
STEP = 6


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
    for y in range(7, 55):
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
                    if 0 <= nx < W and 7 <= ny < 55 and not seen[ny, nx] and int(g[ny, nx]) == 9:
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


def eight_summary(g):
    ys, xs = np.where(g == 8)
    if len(xs) == 0:
        return {"n": 0}
    return {
        "n": int(len(xs)),
        "ymin": int(ys.min()),
        "ymax": int(ys.max()),
        "xmin": int(xs.min()),
        "xmax": int(xs.max()),
        "at_left_shaft_y38": int(np.sum(g[38:43, 14:19] == 8)),
        "stem40": int(np.sum(g[12:38, 40] == 8)),
    }


def body_ndiff(a, b):
    return int(np.sum(a[1:63] != b[1:63]))


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

    def run(name, cmds):
        d = reset()
        g = plane(d)
        guid = d["guid"]
        log = []
        for i, aid in enumerate(cmds):
            d = act(guid, aid)
            guid = d["guid"]
            g2 = plane(d)
            log.append({
                "i": i,
                "a": aid,
                "body": body_ndiff(g, g2),
                "actor": actor(g2),
                "e8": eight_summary(g2),
                "bar1": int(np.sum(g2[63] == 1)),
                "n1": int(np.sum(g2[1:6] == 1)),
                "levels": d.get("levels_completed"),
                "state": d.get("state"),
            })
            g = g2
            if (d.get("levels_completed") or 0) >= 1:
                break
        print(
            name,
            "lv",
            log[-1]["levels"],
            "end",
            log[-1]["actor"],
            "e8",
            log[-1]["e8"],
            "moves",
            sum(1 for e in log if e["body"] >= 40),
        )
        return log

    result = {}

    # Mid-band: D to cy=22 (2 steps), R to cx=28, explore
    # From reset: 3xD -> 2 effective downs to cy=22; queue D
    # Then R flushes extra D to cy=28 first!
    # Want cy=22: use 3xD (2 moves + queue D), then need flush without moving:
    # Actually after 2 effective at cy=22 with queue D, next any key does 3rd D to cy=28.
    # cy=28 still in left shaft (ok until 34). Then R.
    result["mid_spur"] = run("mid_spur", [2, 2, 2, 4, 4, 4, 4, 2, 2, 4, 4, 4])

    # Eat head then try A5 / L / D / U
    result["eat_head_then_5"] = run("eat_head_5", [4, 4, 4, 4, 4, 5, 5, 5, 2, 2, 2, 3, 3, 3])
    result["eat_head_then_L_D"] = run("eat_head_LD", [4, 4, 4, 4, 4, 3, 3, 2, 2, 2, 2, 4, 4])

    # Timer watch at cy=22: many blocked A3 (left into wall) 
    result["timer_at_22"] = run(
        "timer22",
        [2, 2, 2, 2] + [3] * 40,  # down to ~28/34 then spam left
    )

    # Compare 8 mask every 5 spam steps - store in log via e8

    # Approach bottom bar from left at cy=34, then A5 once (not twice?)
    result["bottom_A5_once"] = run("bottom_A5", [2] * 5 + [5] + [2] * 5 + [4] * 5)

    # Try walking onto bottom 8 bar with partial - from (16,34) use A5 then A2
    result["bottom_5_2"] = run("bottom_52", [2] * 5 + [5, 2, 5, 2, 5, 2, 2, 2])

    # Long eat: go to head, leave left, re-enter head repeatedly
    result["ream_head"] = run("ream", [4] * 5 + [3, 3, 4, 4, 3, 3, 4, 4, 4, 2, 2, 2])

    # Check if levels rises when standing on goal cells — cheat teleport? no.
    # After clearing: see if n8 can hit 0
    # Path: eat head (n8=66), go left down shaft, see e8 at_left_shaft

    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    # print key e8 series for timer
    print("TIMER e8 series:")
    for e in result["timer_at_22"][::5]:
        print(e["i"], e["actor"], e["e8"], "bar", e["bar1"], "body", e["body"])
    print("EAT5 series:")
    for e in result["eat_head_then_5"]:
        if e["body"] or e["i"] < 8:
            print(e["i"], "A" + str(e["a"]), e["actor"], e["e8"], e["body"])

    print("wrote", OUT)
    s.post(
        f"{BASE}/api/scorecard/close",
        headers=H(key, True),
        json={"card_id": card},
        timeout=15,
    )


if __name__ == "__main__":
    main()
