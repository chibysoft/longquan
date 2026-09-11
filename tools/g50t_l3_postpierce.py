"""g50t L3: after pierce, dump neighbors + re-BFS + try U-then-east / D-then-west.

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

OUT = ROOT / "tests/fixtures/g50t_l3_postpierce.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
DIRS = {1: (0, -6), 2: (0, 6), 3: (-6, 0), 4: (6, 0)}


def p(*a, **k):
    print(*a, **k, flush=True)


def c11info(g):
    ys, xs = np.where(g == 11)
    if len(xs) == 0:
        return {"n": 0}
    return {
        "n": int(len(xs)),
        "xmin": int(xs.min()),
        "xmax": int(xs.max()),
        "ymin": int(ys.min()),
        "ymax": int(ys.max()),
    }


def right_blk(g):
    return int(np.sum(g[20:25, 50:55] == 11))


def patch5(g, cx, cy, r=8):
    x0, x1 = max(0, cx - r), min(64, cx + r + 1)
    y0, y1 = max(0, cy - r), min(64, cy + r + 1)
    return {
        "box": [y0, x0, y1, x1],
        "rows": g[y0:y1, x0:x1].tolist(),
    }


def walkable_center(g, x, y):
    """Heuristic: 5x5 around center mostly floor(5) or actor(9), no 0/8/11."""
    if not (2 <= x <= 61 and 2 <= y <= 61):
        return False
    sub = g[y - 2 : y + 3, x - 2 : x + 3]
    bad = np.isin(sub, [0, 8, 11]).sum()
    good = np.isin(sub, [5, 9, 1, 2]).sum()
    return bad == 0 and good >= 20


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
        return guid, g, prev

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
        return play(guid, g, prev, TO_3434 + [4, 4, 3, 3])

    def show(tag, prev, g, d=None):
        p(
            f"  {tag}",
            (prev["cx"], prev["cy"]) if prev else None,
            "e8",
            e8(g)["n"],
            "c11",
            c11info(g),
            "blkN",
            right_blk(g),
            "lv",
            None if d is None else d.get("levels_completed"),
        )

    def to_pierce(guid, g, prev):
        # U*6, D, D, R  -> land (34,22) pierce, pending R drained as noop
        for a_ in (1, 1, 1, 1, 1, 1, 2, 2, 4):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, True
        return guid, g, prev, d, False

    out = {"cleared": False}
    cleared = False

    # --- dump pierce landing ---
    p("## pierce dump")
    guid, g, prev = enter_l3()
    guid, g, prev, d, ok = latch(guid, g, prev)
    if ok:
        cleared = True
    guid, g, prev, d, ok = to_pierce(guid, g, prev)
    if ok:
        cleared = True
    show("pierce", prev, g, d)
    cx, cy = int(round(prev["cx"])), int(round(prev["cy"]))
    dump = {
        "pos": (cx, cy),
        "c11": c11info(g),
        "blkN": right_blk(g),
        "patch": patch5(g, cx, cy, 12),
        "neighbors_heuristic": {},
        "neighbor_probe": {},
    }
    for aid, (dx, dy) in DIRS.items():
        nx, ny = cx + dx, cy + dy
        dump["neighbors_heuristic"][aid] = {
            "to": (nx, ny),
            "walkish": walkable_center(g, nx, ny),
            "cell": int(g[ny, nx]) if 0 <= nx < 64 and 0 <= ny < 64 else None,
            "sub_hist": {
                int(k): int(v)
                for k, v in zip(*np.unique(g[ny - 2 : ny + 3, nx - 2 : nx + 3], return_counts=True))
            }
            if 2 <= nx <= 61 and 2 <= ny <= 61
            else None,
        }
    # live probe each dir once (need fresh pending): double-tap each from pierce
    # After pierce we have pending R noop. Flush with same R then try dirs.
    for aid in (4, 1, 2, 3, 4):
        before = (prev["cx"], prev["cy"])
        d = act(guid, aid)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        dump["neighbor_probe"][f"A{aid}"] = {
            "from": before,
            "to": (prev["cx"], prev["cy"]) if prev else None,
            "moved": before != ((prev["cx"], prev["cy"]) if prev else None),
            "c11": c11info(g),
            "lv": d.get("levels_completed"),
        }
        show(f"probeA{aid}", prev, g, d)
        if (d.get("levels_completed") or 0) > 2:
            cleared = True
            break
    out["pierce_dump"] = dump

    # --- after pierce: U then try east on y16 / y10 ---
    trials = {
        "pierce_U_R": [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 4, 4, 4, 4, 4, 4],
        "pierce_UU_R": [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2],
        "pierce_D_L": [1, 1, 1, 1, 1, 1, 2, 2, 4, 2, 3, 3, 3, 3, 3, 1, 1],
        "pierce_U_R_from16_D": [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 4, 4, 4, 2, 2, 3, 3],
        # go top-east first THEN descend x40? (may not be in graph)
        "topE_then_D40": [1, 1, 1, 1, 1, 1, 4, 4, 4, 2, 2, 2, 3, 3],
        # double pierce: up and down again
        "double_pierce": [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 2, 2, 4, 4, 4, 2, 3],
    }

    for name, seq in trials.items():
        if cleared:
            break
        p(f"## {name}")
        guid, g, prev = enter_l3()
        guid, g, prev, d, ok = latch(guid, g, prev)
        if ok:
            cleared = True
            break
        log = []
        for a_ in seq:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            log.append(
                {
                    "a": a_,
                    "pos": (prev["cx"], prev["cy"]) if prev else None,
                    "c11": c11info(g),
                    "blkN": right_blk(g),
                    "lv": d.get("levels_completed"),
                }
            )
            show(f"A{a_}", prev, g, d)
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                CLEAR.write_text(
                    json.dumps({"cleared": True, "method": name, "log": log}, indent=2, default=str),
                    encoding="utf-8",
                )
                break
        path = []
        for r in log:
            if r["pos"] and (not path or path[-1] != r["pos"]):
                path.append(r["pos"])
        p("  path", path)
        out[name] = {"path": path, "final": log[-1] if log else None, "new_cells": [
            pos for pos in path if pos not in {
                (10.0, 10.0), (10.0, 16.0), (10.0, 22.0),
                (16.0, 10.0), (22.0, 10.0), (28.0, 10.0),
                (34.0, 10.0), (34.0, 16.0), (34.0, 22.0), (34.0, 28.0), (34.0, 34.0),
                (40.0, 10.0), (40.0, 34.0), (46.0, 10.0), (52.0, 10.0), (52.0, 16.0),
            }
        ]}
        if cleared:
            break
        # if new x on y22/28, hunt goal
        if prev and prev["cy"] in (22.0, 28.0) and prev["cx"] not in (34.0, 10.0):
            p("  OFF-COLUMN midband — hunt")
            for _ in range(20):
                cx, cy = prev["cx"], prev["cy"]
                dx, dy = 22 - cx, 22 - cy
                aid = (4 if dx > 0 else 3) if abs(dx) >= abs(dy) else (2 if dy > 0 else 1)
                b = (cx, cy)
                for a_ in (aid, aid):
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                show("h", prev, g, d)
                if (d.get("levels_completed") or 0) > 2:
                    cleared = True
                    CLEAR.write_text(
                        json.dumps({"cleared": True, "method": name + "+hunt"}, indent=2, default=str),
                        encoding="utf-8",
                    )
                    break
                if prev and (prev["cx"], prev["cy"]) == b:
                    break
            if cleared:
                break

    # empirical flush-BFS from pierce state (online)
    if not cleared:
        p("## online BFS from pierce")
        guid, g, prev = enter_l3()
        guid, g, prev, d, _ = latch(guid, g, prev)
        guid, g, prev, d, _ = to_pierce(guid, g, prev)
        # drain pending
        d = act(guid, 4)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        start = (int(round(prev["cx"])), int(round(prev["cy"])))
        seen = {start}
        q = deque([(start, guid, g, prev, [])])
        reached = [start]
        edges = []
        steps = 0
        while q and steps < 80:
            (x, y), guid, g, prev, path = q.popleft()
            for aid, (dx, dy) in DIRS.items():
                # double tap to overcome buffer from unknown pending
                ng, nprev, nguid = g, prev, guid
                moved = False
                for tap in (aid, aid):
                    d = act(nguid, tap)
                    nguid = d["guid"]
                    ng = plane(d)
                    nprev = actor(ng, nprev)
                    if (d.get("levels_completed") or 0) > 2:
                        cleared = True
                        p("*** CLEAR during BFS")
                        CLEAR.write_text(
                            json.dumps({"cleared": True, "method": "postpierce_bfs"}, indent=2),
                            encoding="utf-8",
                        )
                        break
                if cleared:
                    break
                if not nprev:
                    continue
                nx, ny = int(round(nprev["cx"])), int(round(nprev["cy"]))
                if (nx, ny) != (x, y):
                    moved = True
                    edges.append({"from": (x, y), "a": aid, "to": (nx, ny), "c11": c11info(ng)})
                    if (nx, ny) not in seen:
                        seen.add((nx, ny))
                        reached.append((nx, ny))
                        q.append(((nx, ny), nguid, ng, nprev, path + [aid]))
                        p("  NEW", (nx, ny), "via", aid, "c11", c11info(ng), "blk", right_blk(ng))
                # reset to this node by re-entering — too expensive; instead continue from new state only if moved
                # PROBLEM: we mutated state. Need re-seed from scratch for each branch.
                # Abort naive BFS — do star probe only from pierce
                break
            if cleared:
                break
            steps += 1
            break  # only one node without reset — see star below
        out["bfs_note"] = "truncated; see star"
        # star: from pierce, try each dir with full reset
        star = {}
        for aid in (1, 2, 3, 4):
            guid, g, prev = enter_l3()
            guid, g, prev, d, _ = latch(guid, g, prev)
            guid, g, prev, d, _ = to_pierce(guid, g, prev)
            d = act(guid, 4)  # drain
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            before = (prev["cx"], prev["cy"])
            # queue aid then flush with noop-ish: send aid twice
            for tap in (aid, aid):
                d = act(guid, tap)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
            after = (prev["cx"], prev["cy"]) if prev else None
            star[aid] = {
                "before": before,
                "after": after,
                "moved": before != after,
                "c11": c11info(g),
                "blkN": right_blk(g),
                "lv": d.get("levels_completed"),
            }
            p("  star", aid, before, "->", after, "c11", c11info(g))
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                break
            # if moved, try one more hop each dir
            if before != after and not cleared:
                hops = {}
                for aid2 in (1, 2, 3, 4):
                    guid2, g2, prev2 = enter_l3()
                    guid2, g2, prev2, d2, _ = latch(guid2, g2, prev2)
                    guid2, g2, prev2, d2, _ = to_pierce(guid2, g2, prev2)
                    d2 = act(guid2, 4)
                    guid2 = d2["guid"]
                    g2 = plane(d2)
                    prev2 = actor(g2, prev2)
                    for tap in (aid, aid, aid2, aid2):
                        d2 = act(guid2, tap)
                        guid2 = d2["guid"]
                        g2 = plane(d2)
                        prev2 = actor(g2, prev2)
                        if (d2.get("levels_completed") or 0) > 2:
                            cleared = True
                            break
                    hops[aid2] = {
                        "pos": (prev2["cx"], prev2["cy"]) if prev2 else None,
                        "c11": c11info(g2),
                        "lv": d2.get("levels_completed"),
                    }
                    p("    hop", aid, "then", aid2, hops[aid2]["pos"], hops[aid2]["c11"])
                    if cleared:
                        break
                star[aid]["hops"] = hops
                if cleared:
                    break
        out["star"] = star

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_POSTPIERCE"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
