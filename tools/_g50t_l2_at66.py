"""g50t L2: at (16,40) e8=66 shaft_L=0, probe all dirs without A5 death."""
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

# Reach (16,40) with shrink, ending with L so queue is L (blocked after)
TO_1640 = [3, 3, 5, 2, 2, 2, 2, 2, 3, 3, 3, 3, 1, 1, 1, 3, 3, 3]


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


def fp(g, cx, cy):
    return [[int(g[cy + oy, cx + ox]) for ox in range(-2, 3)] for oy in range(-2, 3)]


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
        d = act(guid, 3)
        return d["guid"], plane(d)

    guid, g = to_l2()
    prev = None
    log = []
    print("navigate to 16,40")
    for i, aid in enumerate(TO_1640):
        d = act(guid, aid)
        guid = d["guid"]
        g2 = plane(d)
        a = actor(g2, prev)
        print(i, "A" + str(aid), a, e8(g2), "b", body_ndiff(g, g2))
        g, prev = g2, a
        log.append({"i": i, "a": aid, "actor": a, "e8": e8(g2), "levels": d.get("levels_completed")})

    print("AT", prev, e8(g))
    print("fp U", fp(g, 16, 34))
    print("fp D", fp(g, 16, 46))
    print("fp L", fp(g, 10, 40))
    print("fp R", fp(g, 22, 40))

    # Probe each dir twice
    probes = {}
    for aid, name in [(1, "U"), (2, "D"), (3, "L"), (4, "R"), (5, "5")]:
        # fresh to 1640 each time
        guid, g = to_l2()
        prev = None
        for a_ in TO_1640:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        rows = []
        for k in range(6):
            d = act(guid, aid)
            guid = d["guid"]
            g2 = plane(d)
            a = actor(g2, prev)
            rows.append({
                "k": k, "body": body_ndiff(g, g2), "actor": a, "e8": e8(g2),
                "levels": d.get("levels_completed"),
            })
            print(name, k, rows[-1]["body"], a, rows[-1]["e8"], "lv", rows[-1]["levels"])
            g, prev = g2, a
            if (d.get("levels_completed") or 0) >= 2:
                print("PASS")
                break
        probes[name] = rows

    # If R works, continue to goal x=28 then U
    guid, g = to_l2()
    prev = None
    for a_ in TO_1640 + [4] * 8 + [1] * 8 + [4] * 4:
        d = act(guid, a_)
        guid = d["guid"]
        g2 = plane(d)
        a = actor(g2, prev)
        print("GO", a_, a, e8(g2), "lv", d.get("levels_completed"), "b", body_ndiff(g, g2))
        g, prev = g2, a
        if (d.get("levels_completed") or 0) >= 2:
            print("PASS GO")
            break

    cleared = (d.get("levels_completed") or 0) >= 2
    OUT.write_text(json.dumps({
        "cleared": cleared,
        "at_1640_fps": {
            "U": fp(g, 16, 34) if prev and prev["cx"] == 16 else None,
        },
        "probes": probes,
        "final": {"actor": prev, "e8": e8(g), "levels": d.get("levels_completed")},
    }, indent=2, default=str), encoding="utf-8")
    print("CLEARED", cleared)

    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
