"""g50t L2: latch@16,40 → reenter (28,40) e8=66 → bot → right → top → goal."""
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
TO_2240 = [3, 3, 5, 2, 2, 2, 2, 2, 3, 3, 3, 3, 1, 1, 1, 3, 3]


def H(key, j=False):
    h = {"X-API-Key": key, "Accept": "application/json"}
    if j:
        h["Content-Type"] = "application/json"
    return h


def plane(d):
    a = np.asarray(d["frame"], dtype=np.int64)
    return a[0] if a.ndim == 3 else a


def actor(g, prev=None):
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
    if prev:
        return min(cands, key=lambda b: abs(b["cx"] - prev["cx"]) + abs(b["cy"] - prev["cy"]))
    return max(cands, key=lambda b: b["cx"])


def e8(g):
    return {"n": int(np.sum(g[1:63] == 8)), "shaft_L": int(np.sum(g[38:43, 14:19] == 8))}


def body_ndiff(a, b):
    return int(np.sum(a[1:63] != b[1:63]))


def fp(g, cx, cy):
    cx, cy = int(round(cx)), int(round(cy))
    return [[int(g[cy + oy, cx + ox]) for ox in range(-2, 3)] for oy in range(-2, 3)]


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
        d = act(guid, 3)
        return d["guid"], plane(d)

    # to (28,40) with persistent 66 after second-shrink A5
    to_2840 = list(TO_2240) + [5, 1] + [2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 1, 1, 1]
    # from (28,40): U queued → D D to bot, R to (52,52), U to top, L to (10,10), D D, R R R
    route = [
        2, 2, 2,           # flush U; D; D → (28,52) (extra D ok)
        4, 4, 4, 4,        # → (52,52)
        1, 1, 1, 1, 1, 1, 1, 1,  # → (52,10)
        3, 3, 3, 3, 3, 3, 3, 3,  # → (10,10)
        2, 2,              # → (10,22)
        4, 4, 4,           # → (28,22) GOAL
    ]

    guid, g = to_l2()
    prev = None
    full = to_2840 + route
    log = []
    cleared = False
    for i, a_ in enumerate(full):
        d = act(guid, a_)
        guid = d["guid"]
        g2 = plane(d)
        a = actor(g2, prev)
        row = {
            "i": i, "a": a_, "actor": a, "e8": e8(g2),
            "lv": d.get("levels_completed"), "b": body_ndiff(g, g2),
        }
        print(i, "A" + str(a_), a, row["e8"], "lv", row["lv"], "b", row["b"])
        log.append(row)
        g, prev = g2, a
        if (d.get("levels_completed") or 0) >= 2:
            cleared = True
            print("PASS")
            full = full[: i + 1]
            break

    if not cleared and prev:
        print("FINAL", prev, e8(g))
        print("fp U/D/L/R", {
            "U": fp(g, prev["cx"], prev["cy"] - 6),
            "D": fp(g, prev["cx"], prev["cy"] + 6),
            "L": fp(g, prev["cx"] - 6, prev["cy"]),
            "R": fp(g, prev["cx"] + 6, prev["cy"]),
        })

    OUT.write_text(json.dumps({
        "cleared": cleared,
        "method": "persist66_via_2840_top_loop",
        "l2_actions_after_transition": full if cleared else to_2840 + route,
        "log": log,
        "final": {"actor": prev, "e8": e8(g), "levels": d.get("levels_completed")},
    }, indent=2, default=str), encoding="utf-8")
    print("CLEARED", cleared)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
