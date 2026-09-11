"""g50t L3: latch, dump frame, empirical flush-BFS for 2nd shrink / (22,28).

tags=["g50t_recon"]
"""
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
from tools.g50t_l3_recon_probe import (  # noqa: E402
    L1_SEQ,
    TO_2840,
    L2_ROUTE,
    H,
    plane,
    actor,
    e8,
)

OUT = ROOT / "tests/fixtures/g50t_l3_reach_bfs.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
FRAME = ROOT / "tests/fixtures/g50t_l3_latched_frame.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]


def p(*a, **k):
    print(*a, **k, flush=True)


def main():
    key = _api_key()
    s = requests.Session()
    card = s.post(
        f"{BASE}/api/scorecard/open",
        headers=H(key, True),
        json={"tags": ["g50t_recon"]},
        timeout=30,
    ).json()["card_id"]
    gid = s.get(f"{BASE}/api/games/g50t", headers=H(key), timeout=20).json()["game_id"]
    p("opened", gid)

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

    def enter_l3():
        d = reset()
        guid = d["guid"]
        g = plane(d)
        prev = None
        for a_ in L1_SEQ + [2] * 4 + [4] * 8:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) >= 1:
                break
        d = act(guid, 3)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        for a_ in TO_2840 + L2_ROUTE:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) >= 2:
                break
        d = act(guid, 3)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        return guid, g, prev, d

    def play(guid, g, prev, seq):
        for a_ in seq:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, True
        return guid, g, prev, d, False

    def latch(guid, g, prev):
        guid, g, prev, d, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if ok:
            return guid, g, prev, d, True
        guid, g, prev, d, ok = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        return guid, g, prev, d, ok

    out = {"visited": {}, "finds": [], "cleared": False}

    # Latch + dump frame
    guid, g, prev, d = enter_l3()
    guid, g, prev, d, ok = latch(guid, g, prev)
    start = (int(round(prev["cx"])), int(round(prev["cy"])))
    p("latched at", start, "e8", e8(g)["n"], "c11", int(np.sum(g == 11)))
    FRAME.write_text(
        json.dumps(
            {
                "actor": prev,
                "e8": e8(g),
                "c11": int(np.sum(g == 11)),
                "hist": {str(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))},
                "frame": g.tolist(),
            },
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    p("wrote", FRAME)

    # Offline analyze latched frame
    def centers():
        pts = []
        for y in range(10, 55, 6):
            for x in range(10, 55, 6):
                pts.append((x, y))
        return pts

    g0 = g.copy()
    p("## latched grid centers")
    for y in range(10, 55, 6):
        row = {x: int(g0[y, x]) for x in range(10, 55, 6)}
        p(f"  y{y}", row)

    # Empirical BFS: state = position after flush settle; edge = flush dir twice
    # Re-latch + replay path each expansion (expensive but reliable)
    # Budget ~20 cells
    visited = {start: []}
    frontier = deque([start])
    finds = []
    cleared = False
    goal_near = []

    while frontier and len(visited) < 22 and not cleared:
        pos = frontier.popleft()
        path = visited[pos]
        p(f"## expand {pos} pathlen={len(path)} visited={len(visited)}")
        for aid, dn in ((1, "U"), (2, "D"), (3, "L"), (4, "R")):
            guid, g, prev, d = enter_l3()
            guid, g, prev, d, ok = latch(guid, g, prev)
            if ok:
                cleared = True
                break
            for a_ in path:
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
            if not prev:
                continue
            before = (int(round(prev["cx"])), int(round(prev["cy"])))
            e0 = e8(g)["n"]
            # flush twice
            for a_ in (aid, aid):
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
            if not prev:
                continue
            after = (int(round(prev["cx"])), int(round(prev["cy"])))
            e1 = e8(g)["n"]
            lv = d.get("levels_completed") or 0
            if lv > 2:
                cleared = True
                p("*** CLEAR", path + [aid, aid], after)
                CLEAR.write_text(
                    json.dumps(
                        {
                            "cleared": True,
                            "method": "bfs_flush",
                            "path_from_latch": path + [aid, aid],
                            "end": after,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                break
            moved = after != before
            if e1 < 76:
                p(f"  ** SHRINK {dn}", before, "->", after, e0, "->", e1)
                finds.append(
                    {
                        "type": "shrink",
                        "dir": dn,
                        "from": before,
                        "to": after,
                        "e8": [e0, e1],
                        "path": path + [aid, aid],
                    }
                )
                # try A5 here for 2nd latch
                for a5 in (5, 5):
                    d = act(guid, a5)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                p("    A5 ->", prev, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
                finds[-1]["a5"] = {
                    "actor": prev,
                    "e8": e8(g)["n"],
                    "lv": d.get("levels_completed"),
                }
                if (d.get("levels_completed") or 0) > 2:
                    cleared = True
                    CLEAR.write_text(
                        json.dumps({"cleared": True, "method": "2nd_tip_a5", "find": finds[-1]}, indent=2, default=str),
                        encoding="utf-8",
                    )
                    break
            if abs(after[0] - 22) <= 3 and abs(after[1] - 28) <= 3:
                p(f"  NEAR 2228 {dn}", after, "e8", e1)
                goal_near.append({"pos": after, "path": path + [aid, aid], "e8": e1})
            if abs(after[0] - 22) <= 3 and abs(after[1] - 22) <= 3:
                p(f"  NEAR GOAL {dn}", after, "e8", e1, "lv", lv)
                goal_near.append({"pos": after, "path": path + [aid, aid], "e8": e1, "lv": lv})
            if moved and after not in visited:
                visited[after] = path + [aid, aid]
                frontier.append(after)
                p(f"  +{dn}", before, "->", after, "e8", e1)
            elif not moved:
                pass  # blocked
        if cleared:
            break

    p("## BFS done visited", len(visited), sorted(visited.keys()))
    p("finds", finds)
    p("goal_near", goal_near)

    # If 2nd shrink found with A5 death, try revisit persist + path to goal
    for f in finds:
        if f.get("type") != "shrink":
            continue
        if not f.get("a5") or not f["a5"].get("actor"):
            continue
        # if respawned, re-do: latch1, go to 2nd tip, A5, revisit, leave, hunt goal
        p("## persist 2nd tip cycle", f["to"])
        guid, g, prev, d = enter_l3()
        guid, g, prev, d, _ = latch(guid, g, prev)
        for a_ in f["path"]:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        p("  on 2nd", prev, "e8", e8(g)["n"])
        for a5 in (5, 5):
            d = act(guid, a5)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        p("  after A5", prev, "e8", e8(g)["n"])
        # revisit
        guid, g, prev, d, _ = latch(guid, g, prev)  # re-first-latch from spawn
        for a_ in f["path"]:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        e_on = e8(g)["n"]
        # leave toward (34,34)
        for a_ in (3, 3, 1, 1):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        p("  leave e8", e_on, "->", e8(g)["n"], "at", prev)
        if e8(g)["n"] < 70:
            p("  ** 2nd persist — hunt (22,28)/(22,22)")
            # dump grid
            for y in range(10, 55, 6):
                row = {x: int(g[y, x]) for x in range(10, 55, 6)}
                p(f"  y{y}", row)
            # greedy toward (22,28) then (22,22)
            for target in ((22, 28), (22, 22)):
                for _ in range(25):
                    if not prev:
                        break
                    cx, cy = prev["cx"], prev["cy"]
                    if abs(cx - target[0]) < 3 and abs(cy - target[1]) < 3:
                        p("  reached", target, prev, "lv", d.get("levels_completed"))
                        if (d.get("levels_completed") or 0) > 2:
                            cleared = True
                        break
                    dx, dy = target[0] - cx, target[1] - cy
                    aid = (4 if dx > 0 else 3) if abs(dx) >= abs(dy) else (2 if dy > 0 else 1)
                    b = (cx, cy)
                    for a_ in (aid, aid):
                        d = act(guid, a_)
                        guid = d["guid"]
                        g = plane(d)
                        prev = actor(g, prev)
                    a = (prev["cx"], prev["cy"]) if prev else None
                    p(f"  ->{target}", b, a, "A", aid, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
                    if (d.get("levels_completed") or 0) > 2:
                        cleared = True
                        CLEAR.write_text(
                            json.dumps({"cleared": True, "method": "2nd_persist_hunt", "end": a}, indent=2, default=str),
                            encoding="utf-8",
                        )
                        break
                    if a == b:
                        break
                if cleared:
                    break
        if cleared:
            break

    out["visited"] = {str(k): v for k, v in visited.items()}
    out["finds"] = finds
    out["goal_near"] = goal_near
    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_BFS_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
