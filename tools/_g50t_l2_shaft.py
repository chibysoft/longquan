"""g50t L2: after latch, use left shaft / bottom to reach goal ~(29,22)."""
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
    cands = []
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
            if len(cells) == 24:
                xs = [c[0] for c in cells]
                ys = [c[1] for c in cells]
                cands.append({
                    "n": 24,
                    "cx": round(sum(xs) / 24, 2),
                    "cy": round(sum(ys) / 24, 2),
                    "box": [min(xs), min(ys), max(xs), max(ys)],
                })
    if not cands:
        return None
    return max(cands, key=lambda b: (b["cx"], -b["cy"]))  # prefer rightmost; ok


def actor_any(g):
    """Any n=24 ring (for when on left side)."""
    H_, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    cands = []
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
            if len(cells) == 24:
                xs = [c[0] for c in cells]
                ys = [c[1] for c in cells]
                cands.append({
                    "n": 24,
                    "cx": round(sum(xs) / 24, 2),
                    "cy": round(sum(ys) / 24, 2),
                    "box": [min(xs), min(ys), max(xs), max(ys)],
                })
    return cands


def e8(g):
    return {"n": int(np.sum(g[1:63] == 8)), "shaft_L": int(np.sum(g[38:43, 14:19] == 8))}


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
        return d["guid"], plane(d)

    def run(name, seq):
        guid, g = to_l2()
        log = []
        print("====", name)
        for i, aid in enumerate(seq):
            d = act(guid, aid)
            guid = d["guid"]
            g2 = plane(d)
            rings = actor_any(g2)
            # pick ring that moved / any
            a = None
            if rings:
                # closest to previous if any
                if log and log[-1]["actor"]:
                    prev = log[-1]["actor"]
                    a = min(rings, key=lambda b: abs(b["cx"] - prev["cx"]) + abs(b["cy"] - prev["cy"]))
                else:
                    a = max(rings, key=lambda b: b["cx"])
            entry = {
                "i": i,
                "a": aid,
                "body": body_ndiff(g, g2),
                "actor": a,
                "rings": rings,
                "e8": e8(g2),
                "levels": d.get("levels_completed"),
                "state": d.get("state"),
            }
            log.append(entry)
            print(f"  {i} A{aid} b={entry['body']} act={a} e8={entry['e8']} lv={entry['levels']}")
            g = g2
            if (d.get("levels_completed") or 0) >= 2:
                print("PASS", name)
                break
        return log

    trials = {}

    # Latch then top-left to (16,10), descend left shaft, right to goal
    # head: 3,3,5,3(death) then 3,3 rehead optional; better go top after latch
    trials["latch_top_left_down"] = run(
        "latch_top_left_down",
        # head + A5 + death via L
        [3, 3, 5, 3]
        # after death at spawn: go top then left all the way
        + [1, 1, 1, 1]  # up to y10 (buffer aware)
        + [3] * 10  # left to x16/10
        + [2] * 8  # down left shaft
        + [4] * 6  # right toward goal
        + [1, 2, 4, 4, 3, 3],
    )

    # Latch bottom: D, L to x16, U shaft, R to goal
    trials["latch_bottom_left_up"] = run(
        "latch_bottom_left_up",
        [3, 3, 5, 2]  # head A5 death via D
        + [2, 2, 2, 2]
        + [3] * 10  # left along bottom
        + [1] * 10  # up left shaft
        + [4] * 6  # right to goal
        + [1, 1, 4, 4],
    )

    # From proven (28,40): need around snake — try L to (16,40), U, R
    trials["via_2840"] = run(
        "via_2840",
        [3, 3, 5, 2]
        + [2, 2, 2, 2, 3, 3, 3, 3]  # to ~(28,52) area
        + [1, 1, 1]  # up to ~40
        + [3, 3, 3]  # left to 16
        + [1, 1, 1, 1]  # up
        + [4, 4, 4, 4]  # right to goal
        + [2, 1, 4],
    )

    # Hold on head, U to (40,22), L — without death if possible
    # After A5 on head, U U: first clears queue
    trials["hold_U_L_from_40_22"] = run(
        "hold_U_L_from_40_22",
        [3, 3, 5, 1, 1]  # may death on first 1
        # if death, recover:
        + [3, 3, 3, 1, 1]
        + [3, 3, 3, 3, 3]
        + [2, 2, 4, 4],
    )

    # Touch goal from above: (28,10) can't D; try (22,10) D or (34,10) D
    trials["top_probe_down"] = run(
        "top_probe_down",
        [3, 3, 5, 3]
        + [1, 1, 1, 3, 3, 3, 3, 3, 3]  # (22,10) or so
        + [2, 2, 2, 2, 4, 4, 2, 2, 4, 4, 1, 1],
    )

    cleared = any(max(e["levels"] for e in v) >= 2 for v in trials.values())
    OUT.write_text(json.dumps({
        "cleared": cleared,
        "trials": {
            k: {
                "max_lv": max(e["levels"] for e in v),
                "end": v[-1],
                "path": [
                    {"i": e["i"], "a": e["a"], "actor": e["actor"], "e8": e["e8"], "lv": e["levels"]}
                    for e in v if e["body"] > 20 or e["levels"] >= 2
                ],
                "log": v,
            }
            for k, v in trials.items()
        },
    }, indent=2, default=str), encoding="utf-8")
    print("CLEARED", cleared)
    for k, v in trials.items():
        print(k, "max", max(e["levels"] for e in v), "end", v[-1]["actor"])

    s.post(
        f"{BASE}/api/scorecard/close",
        headers=H(key, True),
        json={"card_id": card},
        timeout=15,
    )


if __name__ == "__main__":
    main()
