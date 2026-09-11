"""g50t L2 precise clear: latch head, reach mid goal ~(29,22)."""
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
OUT = ROOT / "tests/fixtures/g50t_l2_clear_attempt.json"
L1_SEQ = [4] * 5 + [5] + [2] * 10 + [4] * 6


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
    best = None
    for y in range(7, 56):
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
                    if 0 <= nx < W and 7 <= ny < 56 and not seen[ny, nx] and int(g[ny, nx]) == 9:
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            if len(cells) != 24:
                continue
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            blob = {
                "n": 24,
                "cx": round(sum(xs) / 24, 2),
                "cy": round(sum(ys) / 24, 2),
                "box": [min(xs), min(ys), max(xs), max(ys)],
            }
            if best is None or blob["cx"] > best["cx"]:
                best = blob
    return best


def e8(g):
    n = int(np.sum(g[1:63] == 8))
    return {"n": n, "shaft_L": int(np.sum(g[38:43, 14:19] == 8))}


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

    def to_l2():
        d = reset()
        guid = d["guid"]
        for aid in L1_SEQ + [2] * 4 + [4] * 8:
            d = act(guid, aid)
            guid = d["guid"]
            if (d.get("levels_completed") or 0) >= 1:
                break
        else:
            raise RuntimeError("L1 fail")
        d = act(guid, 3)
        return d["guid"], plane(d), d

    def run(name, seq):
        guid, g, d = to_l2()
        log = []
        print("====", name, "start", actor(g))
        for i, aid in enumerate(seq):
            d = act(guid, aid)
            guid = d["guid"]
            g2 = plane(d)
            a = actor(g2)
            entry = {
                "i": i,
                "a": aid,
                "body": body_ndiff(g, g2),
                "actor": a,
                "e8": e8(g2),
                "levels": d.get("levels_completed"),
                "state": d.get("state"),
            }
            log.append(entry)
            print(
                f"  {i} A{aid} b={entry['body']} {a} e8={entry['e8']} lv={entry['levels']}"
            )
            g = g2
            if (d.get("levels_completed") or 0) >= 2:
                print("PASS", name)
                break
        return log

    trials = {}

    # Core: head latch, re-head, U to y22, L to goal x~28
    trials["head_U_L_goal"] = run(
        "head_U_L_goal",
        [3, 3, 3, 5, 1]  # head, A5, death
        + [3, 3, 3]  # re-head
        + [1, 1]  # (40,22)
        + [3, 3, 3, 3]  # left toward goal
        + [2, 2, 1, 1, 3, 3],
    )

    # From (40,16) go L (top of mid gap?)
    trials["head_UU_L"] = run(
        "head_UU_L",
        [3, 3, 3, 5, 1]
        + [3, 3, 3]
        + [1, 1, 1]  # to (40,16) or (40,10)
        + [3, 3, 3, 3, 3]
        + [2, 2, 2, 2, 3, 3],
    )

    # Bottom corridor then up? 
    trials["latch_bottom_L_U"] = run(
        "latch_bottom_L_U",
        [3, 3, 3, 5, 2]
        + [2, 2, 2, 2, 3, 3, 3, 3]  # bottom left
        + [1, 1, 1, 1, 1, 1, 3, 3, 3],
    )

    # Stay on head NO death: A5 flush only, U while e8=82 still?
    # After A5 on head body=0 still holding; U first executes blocked L
    trials["no_death_U_L"] = run(
        "no_death_U_L",
        [3, 3, 3, 5, 1, 1, 1, 3, 3, 3, 3, 2, 2],
    )

    # Reach (28,22) via (40,22) carefully with buffer flushes
    # Want positions: head -> death -> head -> (40,22) -> (34,22) -> (28,22)
    trials["precision_goal"] = run(
        "precision_goal",
        [3, 3,  # (46), (40) shrink
         5,  # queue A5
         1,  # death
         3, 3,  # (46), (40) again
         1,  # queue U (exec blocked L?)
         1,  # (40,22)
         3,  # queue L
         3,  # (34,22)
         3,  # (28,22) GOAL?
         3, 2, 2, 1, 1],
    )

    # Overshoot control: after (40,22), only L
    trials["at22_LLLL"] = run(
        "at22_LLLL",
        [3, 3, 5, 1, 3, 3, 1, 1] + [3] * 8 + [2, 1, 4],
    )

    cleared = any(max(e["levels"] for e in v) >= 2 for v in trials.values())
    OUT.write_text(json.dumps({
        "cleared": cleared,
        "trials": {
            k: {
                "max_lv": max(e["levels"] for e in v),
                "end": v[-1],
                "near_goal": [
                    e for e in v
                    if e["actor"] and e["actor"]["cx"] <= 34 and 16 <= e["actor"]["cy"] <= 28
                ],
                "log": v,
            }
            for k, v in trials.items()
        },
    }, indent=2, default=str), encoding="utf-8")
    print("CLEARED", cleared)
    for k, v in trials.items():
        near = [
            e for e in v
            if e["actor"] and e["actor"]["cx"] <= 34 and 16 <= e["actor"]["cy"] <= 28
        ]
        print(k, "max", max(e["levels"] for e in v), "near", near[:3], "end", v[-1]["actor"])

    s.post(
        f"{BASE}/api/scorecard/close",
        headers=H(key, True),
        json={"card_id": card},
        timeout=15,
    )


if __name__ == "__main__":
    main()
