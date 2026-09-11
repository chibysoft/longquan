"""g50t L2: after second-shrink A5 latch, persistent e8=66; hunt path to goal ~(28,22)."""
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
    return {
        "n": int(np.sum(g[1:63] == 8)),
        "shaft_L": int(np.sum(g[38:43, 14:19] == 8)),
        "col28": int(np.sum(g[16:40, 26:31] == 8)),
        "row22": int(np.sum(g[20:25, 14:40] == 8)),
    }


def fp(g, cx, cy):
    cx, cy = int(cx), int(cy)
    return [[int(g[cy + oy, cx + ox]) for ox in range(-2, 3)] for oy in range(-2, 3)]


def body_ndiff(a, b):
    return int(np.sum(a[1:63] != b[1:63]))


def walkable_centers(g):
    """coarse 6-grid centers where 5x5 footprint is all 5/9 (actor-ok)."""
    ok = []
    for cy in range(10, 55, 6):
        for cx in range(10, 55, 6):
            patch = g[cy - 2 : cy + 3, cx - 2 : cx + 3]
            if patch.shape != (5, 5):
                continue
            vals = set(int(v) for v in patch.flat)
            if vals <= {5, 9}:
                ok.append((cx, cy, int(np.sum(patch == 9))))
    return ok


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

    def step(guid, g, prev, aid):
        d = act(guid, aid)
        g2 = plane(d)
        a = actor(g2, prev)
        return d["guid"], g2, a, d, body_ndiff(g, g2)

    # Setup: A5-queue at second shrink, die, re-arm persistent 66 via (16,40)
    guid, g = to_l2()
    prev = None
    for a_ in TO_2240:
        guid, g, prev, d, _ = step(guid, g, prev, a_)
    # A5 cmd: L→(16,40); then flush A5 with U → die
    guid, g, prev, d, b = step(guid, g, prev, 5)
    print("land16", prev, e8(g), "b", b)
    guid, g, prev, d, b = step(guid, g, prev, 1)
    print("die", prev, e8(g), "b", b, "lv", d.get("levels_completed"))

    # Bottom route to (16,40) to arm persistent 66
    # buffer may have U → first downs messy; use enough moves
    arm = [2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 1, 1, 1, 3, 3, 3]
    for a_ in arm:
        guid, g, prev, d, b = step(guid, g, prev, a_)
        print("arm", a_, prev, e8(g), "b", b)
        if prev and abs(prev["cx"] - 16) < 1 and abs(prev["cy"] - 40) < 1 and e8(g)["n"] == 66:
            break

    print("ARMED", prev, e8(g))
    print("walk66", walkable_centers(g)[:40], "n=", len(walkable_centers(g)))
    if prev:
        for label, dx, dy in [("U", 0, -6), ("D", 0, 6), ("L", -6, 0), ("R", 6, 0)]:
            print("fp", label, fp(g, prev["cx"] + dx, prev["cy"] + dy))

    # Hunt paths toward (28,22): top corridor then down; or left shaft up
    hunts = {
        "top_then_down": [3, 3, 1, 1, 1, 1, 1, 4, 4, 2, 2, 2, 4, 2, 2, 3, 2, 2],
        "left_shaft_up": [1, 1, 1, 1, 1, 4, 4, 1, 1, 4, 4, 2, 2, 4, 1, 1],
        "bot_mid_up": [4, 4, 1, 1, 1, 1, 1, 3, 1, 1, 4, 1, 1, 3, 1],
        "to_1010_down": [3, 1, 1, 1, 1, 1, 4, 4, 2, 2, 4, 2, 2, 2, 3, 2],
    }

    results = []
    cleared = False
    cleared_seq = None

    for name, extra in hunts.items():
        # fresh setup each hunt
        guid, g = to_l2()
        prev = None
        seq_log = []
        full = list(TO_2240) + [5, 1] + arm + extra
        for a_ in full:
            guid, g, prev, d, b = step(guid, g, prev, a_)
            row = {"a": a_, "actor": prev, "e8": e8(g), "lv": d.get("levels_completed"), "b": b}
            seq_log.append(row)
            if len(seq_log) > len(TO_2240) + 2 and len(seq_log) % 3 == 0:
                print(name, len(seq_log), prev, e8(g), "lv", d.get("levels_completed"))
            if (d.get("levels_completed") or 0) >= 2:
                print("PASS", name)
                cleared = True
                cleared_seq = full[: len(seq_log)]
                break
        # from final pos, dump nearby fps if near goal band
        if prev:
            print(name, "FINAL", prev, e8(g), "walk_n", len(walkable_centers(g)))
            print(name, "fp@actor", fp(g, prev["cx"], prev["cy"]))
            print(name, "fpU", fp(g, prev["cx"], prev["cy"] - 6))
            print(name, "fpD", fp(g, prev["cx"], prev["cy"] + 6))
        results.append({
            "name": name,
            "final": prev,
            "e8": e8(g),
            "levels": d.get("levels_completed"),
            "tail": seq_log[-12:],
            "near_goal": [
                r for r in seq_log
                if r["actor"] and abs(r["actor"]["cx"] - 28) < 8 and abs(r["actor"]["cy"] - 22) < 10
            ],
        })
        if cleared:
            break

    # One more: after arm, BFS-like manual toward goal using walkable map
    if not cleared:
        guid, g = to_l2()
        prev = None
        for a_ in list(TO_2240) + [5, 1] + arm:
            guid, g, prev, d, b = step(guid, g, prev, a_)
        print("MAP66", prev, e8(g))
        centers = walkable_centers(g)
        print("centers", centers)
        # try reach (28,22) if walkable
        goalish = [c for c in centers if abs(c[0] - 28) <= 6 and abs(c[1] - 22) <= 6]
        print("goalish", goalish)
        # from (16,40) try L to (10,40) then U
        for a_ in [3, 1, 1, 1, 1, 1, 4, 4, 4, 2, 2, 2, 2, 4, 2, 3, 3, 2, 4, 1, 1, 1]:
            guid, g, prev, d, b = step(guid, g, prev, a_)
            print("mapGO", a_, prev, e8(g), "lv", d.get("levels_completed"), "b", b)
            if (d.get("levels_completed") or 0) >= 2:
                cleared = True
                print("PASS map")
                break

    OUT.write_text(json.dumps({
        "cleared": cleared,
        "cleared_seq": cleared_seq,
        "method": "persistent66_hunt",
        "results": results,
        "final_levels": d.get("levels_completed"),
    }, indent=2, default=str), encoding="utf-8")
    print("CLEARED", cleared)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
