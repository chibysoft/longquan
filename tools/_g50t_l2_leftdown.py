"""g50t L2: latch, reach top-left (16,10), descend shaft, right into goal."""
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

    def run(name, seq):
        guid, g = to_l2()
        log = []
        prev = None
        print("====", name)
        for i, aid in enumerate(seq):
            d = act(guid, aid)
            guid = d["guid"]
            g2 = plane(d)
            a = actor(g2, prev)
            entry = {
                "i": i, "a": aid, "body": body_ndiff(g, g2),
                "actor": a, "e8": e8(g2),
                "levels": d.get("levels_completed"), "state": d.get("state"),
            }
            log.append(entry)
            print(f"  {i} A{aid} b={entry['body']} {a} e8={entry['e8']} lv={entry['levels']}")
            g, prev = g2, a
            if (d.get("levels_completed") or 0) >= 2:
                print("PASS")
                break
        return log

    # Proven: latch + go top row left to x=16
    # Use at22_LLLL-like path that reached (16,10), then D
    # at22: [3,3,5,1, 3,3,1,1] + [3]*8 reached (10,10)
    # Simpler: head latch death, U to top, L to 16, D down, R to 28
    seq = (
        [3, 3, 5, 3]  # head A5 death
        + [1, 1, 1, 1]  # up (buffer: first may be L from death queue)
        + [3] * 8  # left along top
        + [2] * 10  # down
        + [4] * 5  # right into goal
        + [1, 2, 4, 3]
    )
    # Fix buffer after death: death via A3 means queue empty of U; 
    # Actually death press was A3 exec A5, queue=L. Next A1 exec L!
    # Better death via A1 so queue=U, next U continues up.
    seq2 = (
        [3, 3, 5, 1]  # death with U queued after
        + [1, 1, 1]  # up to top
        + [3] * 9
        + [2] * 10
        + [4] * 6
    )
    # After reaching (16,10) without relying on death direction:
    # head, A5, death A4 (R), then from spawn U U U LLLLL DDD RRR
    seq3 = (
        [3, 3, 5, 4]  # death, queue R (blocked at edge after respawn?)
        + [1, 1, 1, 1]
        + [3] * 9
        + [2] * 12
        + [4] * 6
        + [1] * 4
    )

    trials = {
        "A": run("A_deathU", seq2),
        "B": run("B_deathR", seq3),
        # no death: hold head, U to top via (40,10), L to 16, D
        "C": run(
            "C_hold_top",
            [3, 3, 5, 4, 1, 1, 1, 1]  # may death on 1
            + [3] * 8
            + [2] * 10
            + [4] * 6,
        ),
        # bottom (28,40) then wait/A5/stomp?
        "D": run(
            "D_2840_A5",
            [3, 3, 5, 2, 2, 2, 2, 2, 3, 3, 3, 3, 1, 1, 1, 5, 1, 1, 1, 1, 4, 4, 4],
        ),
    }

    cleared = any(max(e["levels"] for e in v) >= 2 for v in trials.values())
    OUT.write_text(json.dumps({
        "cleared": cleared,
        "trials": {k: {"max_lv": max(e["levels"] for e in v), "end": v[-1], "log": v} for k, v in trials.items()},
    }, indent=2, default=str), encoding="utf-8")
    print("CLEARED", cleared)
    for k, v in trials.items():
        print(k, "max", max(e["levels"] for e in v), "end", v[-1]["actor"])

    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
