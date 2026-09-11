"""g50t L2: A5-queue trick at second shrink (16,40).

Arrive: at (22,40) with LEFT queued → send A5 so LEFT lands on (16,40)
then next tick executes A5 while still on shrink tile.
"""
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

# Stop at (22,40): last move LEFT from (28,40); LEFT still queued for next
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
    return {
        "n": int(np.sum(g[1:63] == 8)),
        "shaft_L": int(np.sum(g[38:43, 14:19] == 8)),
        "mid_col": int(np.sum(g[16:28, 26:31] == 8)),
        "up16": int(np.sum(g[28:40, 14:19] == 8)),
    }


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

    trials = []
    # Trial A: at 22,40 send A5 (flush L→16,40), then flush A5 with U/D/L/R
    for flush_aid, name in [(1, "A5thenU"), (2, "A5thenD"), (3, "A5thenL"), (4, "A5thenR"), (5, "A5then5")]:
        guid, g = to_l2()
        prev = None
        log = []
        for a_ in TO_2240:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            log.append({"a": a_, "actor": prev, "e8": e8(g), "lv": d.get("levels_completed")})
        print(name, "AT22", prev, e8(g))

        # A5: should execute queued LEFT → land (16,40)
        d = act(guid, 5)
        guid = d["guid"]
        g2 = plane(d)
        a = actor(g2, prev)
        print(name, "afterA5cmd", a, e8(g2), "b", body_ndiff(g, g2), "lv", d.get("levels_completed"))
        g, prev = g2, a
        log.append({"phase": "A5cmd", "actor": a, "e8": e8(g2), "lv": d.get("levels_completed")})

        # flush A5
        d = act(guid, flush_aid)
        guid = d["guid"]
        g2 = plane(d)
        a = actor(g2, prev)
        print(name, "flush", flush_aid, a, e8(g2), "b", body_ndiff(g, g2), "lv", d.get("levels_completed"))
        g, prev = g2, a
        log.append({"phase": "flush", "aid": flush_aid, "actor": a, "e8": e8(g2), "lv": d.get("levels_completed")})
        if prev:
            print(name, "fpU", fp(g, int(prev["cx"]), int(prev["cy"]) - 6))
            print(name, "fpR", fp(g, int(prev["cx"]) + 6, int(prev["cy"])))

        # if respawned, try re-approach; else explore toward goal (28,22)
        seq = []
        if prev and abs(prev["cx"] - 52) < 1 and abs(prev["cy"] - 28) < 1:
            # died — try bottom path again with presumed latch
            seq = [2, 2, 2, 2, 2, 3, 3, 3, 3, 1, 1, 1, 3, 3, 1, 1, 4, 4, 1, 1]
        elif prev and abs(prev["cx"] - 16) < 1:
            # still near shrink — try U/R toward mid
            seq = [1, 1, 1, 4, 4, 1, 1, 4, 1, 1, 4, 4, 1]
        else:
            seq = [1, 1, 4, 4, 1, 1, 4, 1, 4, 1, 1]

        cleared = False
        for a_ in seq:
            d = act(guid, a_)
            guid = d["guid"]
            g2 = plane(d)
            a = actor(g2, prev)
            row = {
                "a": a_, "actor": a, "e8": e8(g2),
                "lv": d.get("levels_completed"), "b": body_ndiff(g, g2),
            }
            print(name, "GO", row)
            log.append(row)
            g, prev = g2, a
            if (d.get("levels_completed") or 0) >= 2:
                print("PASS", name)
                cleared = True
                break
        trials.append({"name": name, "cleared": cleared, "log": log, "final": prev})
        if cleared:
            break

    # Trial B: arrive on (16,40) via RIGHT from (10,40), queue A5 on the landing tick
    # Path: to 16,40 normally, L to 10 (lose shrink), then R+A5 trick
    print("=== Trial B: R-arrive A5 ===")
    guid, g = to_l2()
    prev = None
    to_1640 = TO_2240 + [3]  # land 16,40; LEFT queued
    for a_ in to_1640:
        d = act(guid, a_)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
    # flush LEFT to 10,40
    d = act(guid, 4)  # queue R, exec L → 10,40
    guid = d["guid"]
    g = plane(d)
    prev = actor(g, prev)
    print("B at10", prev, e8(g))
    # send A5: exec R → 16,40 shrink; queue A5
    d = act(guid, 5)
    guid = d["guid"]
    g2 = plane(d)
    a = actor(g2, prev)
    print("B A5cmd", a, e8(g2), "b", body_ndiff(g, g2))
    g, prev = g2, a
    # flush A5 with UP
    d = act(guid, 1)
    guid = d["guid"]
    g2 = plane(d)
    a = actor(g2, prev)
    print("B flushU", a, e8(g2), "b", body_ndiff(g, g2), "lv", d.get("levels_completed"))
    g, prev = g2, a
    blog = [{"actor": a, "e8": e8(g), "lv": d.get("levels_completed")}]
    for a_ in [1, 1, 4, 4, 1, 1, 4, 1, 2, 2, 3, 3, 1, 1, 4, 4, 1]:
        d = act(guid, a_)
        guid = d["guid"]
        g2 = plane(d)
        a = actor(g2, prev)
        print("B GO", a_, a, e8(g2), "lv", d.get("levels_completed"), "b", body_ndiff(g, g2))
        blog.append({"a": a_, "actor": a, "e8": e8(g2), "lv": d.get("levels_completed")})
        g, prev = g2, a
        if (d.get("levels_completed") or 0) >= 2:
            print("PASS B")
            break

    cleared = any(t["cleared"] for t in trials) or (d.get("levels_completed") or 0) >= 2
    OUT.write_text(json.dumps({
        "cleared": cleared,
        "method": "a5_queue_second_shrink",
        "trials": [{k: v for k, v in t.items() if k != "log"} | {"log_tail": t["log"][-8:]} for t in trials],
        "trial_b_tail": blog[-8:],
        "final_levels": d.get("levels_completed"),
    }, indent=2, default=str), encoding="utf-8")
    print("CLEARED", cleared, "lv", d.get("levels_completed"))
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
