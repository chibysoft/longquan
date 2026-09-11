"""g50t: while standing on snake head, probe all dirs + map changes + latch A5."""
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
OUT = ROOT / "tests/fixtures/g50t_l1_head_hold.json"


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


def e8(g):
    ys, xs = np.where(g == 8)
    if len(xs) == 0:
        return {"n": 0}
    return {
        "n": int(len(xs)),
        "ymin": int(ys.min()),
        "ymax": int(ys.max()),
        "xmin": int(xs.min()),
        "xmax": int(xs.max()),
        "shaft": int(np.sum(g[38:43, 14:19] == 8)),
        "stem": int(np.sum(g[12:38, 40] == 8)),
    }


def row(g, y, x0=12, x1=50):
    return "".join({0: ".", 5: "5", 8: "8", 9: "9"}.get(int(g[y, x]), "?") for x in range(x0, x1))


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

    # Go to head
    d = reset()
    g = plane(d)
    guid = d["guid"]
    for _ in range(5):
        d = act(guid, 4)
        guid = d["guid"]
        g = plane(d)
    print("ON HEAD", actor(g), e8(g))
    rows_before = {y: row(g, y) for y in list(range(8, 15)) + list(range(36, 44)) + [48, 49, 52]}
    for y, r in rows_before.items():
        print(f"{y:02d}|{r}")

    result = {"on_head": {"actor": actor(g), "e8": e8(g), "rows": rows_before}}

    # From head, try each direction in fresh head-hold sessions
    dir_tries = {}
    for aid, name in [(1, "U"), (2, "D"), (3, "L"), (4, "R"), (5, "5")]:
        d = reset()
        g = plane(d)
        guid = d["guid"]
        for _ in range(5):
            d = act(guid, 4)
            guid = d["guid"]
            g = plane(d)
        # now on head, queue=R. First press of aid executes R (blocked) or?
        log = []
        for i in range(4):
            d = act(guid, aid)
            guid = d["guid"]
            g2 = plane(d)
            log.append({
                "i": i,
                "body": body_ndiff(g, g2),
                "actor": actor(g2),
                "e8": e8(g2),
                "levels": d.get("levels_completed"),
                "state": d.get("state"),
            })
            print(name, i, log[-1]["body"], log[-1]["actor"], log[-1]["e8"])
            g = g2
        dir_tries[name] = log
    result["dir_from_head"] = dir_tries

    # Hold head with one A5 (flush), then check if shaft stays clear when we... can't leave.
    # Idea: maybe levels complete BY standing on head? Check levels - no.
    # Idea: maybe need to clear ALL 8 by repeated stomps - go L and R onto head many times
    d = reset()
    g = plane(d)
    guid = d["guid"]
    stomp = []
    # approach and oscillate 34↔40
    seq = [4] * 5 + [3, 3, 4, 4] * 8
    for i, aid in enumerate(seq):
        d = act(guid, aid)
        guid = d["guid"]
        g2 = plane(d)
        stomp.append({
            "i": i,
            "a": aid,
            "body": body_ndiff(g, g2),
            "actor": actor(g2),
            "e8": e8(g2),
            "levels": d.get("levels_completed"),
        })
        g = g2
    result["stomp"] = stomp
    print("STOMP last", stomp[-1])
    print("STOMP min n8", min(e["e8"].get("n", 99) for e in stomp))

    # NEW: while on head (shaft clear), is bottom path open for a hypothetical second body?
    # Check walkable at (16,40) while holding head
    d = reset()
    g = plane(d)
    guid = d["guid"]
    for _ in range(5):
        d = act(guid, 4)
        guid = d["guid"]
        g = plane(d)
    # analyze (16,40) footprint
    cx, cy = 16, 40
    cells = [[int(g[cy + oy, cx + ox]) for ox in range(-2, 3)] for oy in range(-2, 3)]
    result["hold_footprint_16_40"] = cells
    result["hold_rows"] = {y: row(g, y) for y in range(34, 55)}
    print("footprint 16,40 while hold", cells)
    for y in range(34, 55):
        print(f"{y:02d}|{row(g, y)}")

    # Maybe goal is destroy snake to n8=0 by stomping head enough - already saw restore on leave
    # Try ACTION5 exactly once on head then immediately check levels / n8 over time with noops via blocked R
    d = reset()
    g = plane(d)
    guid = d["guid"]
    for _ in range(5):
        d = act(guid, 4)
        guid = d["guid"]
        g = plane(d)
    d = act(guid, 5)  # flush
    guid = d["guid"]
    g = plane(d)
    hold = [{"actor": actor(g), "e8": e8(g), "levels": d.get("levels_completed")}]
    for i in range(20):
        d = act(guid, 4)  # blocked R as clock
        guid = d["guid"]
        g2 = plane(d)
        hold.append({
            "i": i,
            "body": body_ndiff(g, g2),
            "actor": actor(g2),
            "e8": e8(g2),
            "bar": int(np.sum(g2[63] == 1)),
            "levels": d.get("levels_completed"),
            "state": d.get("state"),
        })
        g = g2
    result["hold_clock"] = hold
    print("HOLD clock end", hold[-1])

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
