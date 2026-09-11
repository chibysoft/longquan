"""g50t L2: top corridor (40,10)/(28,10) then DOWN to goal ~(28,22)."""
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
        "at_goal": int(np.sum(g[19:26, 25:32] == 8)),
    }


def fp(g, cx, cy):
    cx, cy = int(round(cx)), int(round(cy))
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

    def run(name, seq):
        guid, g = to_l2()
        prev = None
        log = []
        print("===", name)
        for i, a_ in enumerate(seq):
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
                print("PASS", name)
                return True, log, seq[: i + 1]
        if prev:
            print("fps", {k: fp(g, prev["cx"] + dx, prev["cy"] + dy)
                          for k, dx, dy in [("here", 0, 0), ("U", 0, -6), ("D", 0, 6), ("L", -6, 0), ("R", 6, 0)]})
        return False, log, None

    trials = {}

    # T1: no second A5 — from spawn L to head, U top, L to 28, D to goal
    # Need first-head A5? try without first: just L L to head then U
    trials["plain_top"] = [3, 3, 1, 1, 1, 3, 3, 2, 2, 2, 2, 2, 3, 2]

    # T2: A5 on first head then after death go top via x=40
    trials["head5_top"] = [3, 3, 5, 1, 1, 1, 3, 3, 2, 2, 2, 2]

    # T3: second shrink A5 latch, die, then top via (40,28) U
    # after die at spawn; L to head; U; L; D
    trials["sec5_top"] = (
        TO_2240 + [5, 1]  # latch+die (U flush)
        + [3, 3, 1, 1, 1, 3, 3, 2, 2, 2, 2, 2]  # to head? buffer messy
    )

    # T4: carefully — after L2, L to (40,28), A5, die, re-approach head without second shrink,
    # climb x=40 to y=10, left to x=28, down
    trials["head_latch_climb"] = [
        3, 3, 5,  # to head + A5 queued/land
        1,        # flush A5 → die?
        # after death, buffered U may move up; then go to (40,28) and climb
        3, 3, 1, 1, 1, 3, 3,
        2, 2, 2,  # down toward goal from (28,10)
        2, 2, 4, 2,
    ]

    # T5: explicit navigate to (28,10) then probe D with prints every step
    # From A5thenL evidence path after weird buffer: got to 28,10 with e8=82
    # Reproduce: second A5 latch die with L flush, then...
    trials["reproduce_2810"] = (
        TO_2240 + [5, 3]  # A5 then flush L → die
        + [
            # A5thenL GO sequence-ish after death with L buffer
            2, 2, 2, 2, 2, 3, 3, 3, 3, 1, 1, 1,  # may not match
        ]
    )

    cleared = False
    cleared_seq = None
    all_logs = {}
    for name, seq in trials.items():
        ok, log, cseq = run(name, seq)
        all_logs[name] = {"ok": ok, "tail": log[-15:], "final": log[-1] if log else None}
        if ok:
            cleared = True
            cleared_seq = cseq
            break

    # T6 focused: get to (40,28) climb regardless of latch
    if not cleared:
        print("=== climb40 ===")
        guid, g = to_l2()
        prev = None
        log = []
        # L L to head
        for a_ in [3, 3]:
            d = act(guid, a_)
            guid = d["guid"]
            g2 = plane(d)
            prev = actor(g2, prev)
            print("tohead", a_, prev, e8(g2), "b", body_ndiff(g, g2))
            g = g2
        # stand on head — try U without A5
        for a_ in [1, 1, 1, 1, 1]:
            d = act(guid, a_)
            guid = d["guid"]
            g2 = plane(d)
            a = actor(g2, prev)
            print("U", a_, a, e8(g2), "b", body_ndiff(g, g2), "lv", d.get("levels_completed"))
            g, prev = g2, a
            log.append({"a": a_, "actor": a, "e8": e8(g2), "lv": d.get("levels_completed")})
        if prev:
            print("fps", fp(g, prev["cx"], prev["cy"] - 6))
        # if at topish, L toward 28 then D
        for a_ in [3, 3, 3, 2, 2, 2, 2, 2, 4, 2, 3, 2]:
            d = act(guid, a_)
            guid = d["guid"]
            g2 = plane(d)
            a = actor(g2, prev)
            print("fin", a_, a, e8(g2), "lv", d.get("levels_completed"), "b", body_ndiff(g, g2))
            g, prev = g2, a
            if (d.get("levels_completed") or 0) >= 2:
                cleared = True
                print("PASS climb40")
                break
        all_logs["climb40"] = {"final": prev, "e8": e8(g), "lv": d.get("levels_completed")}

    # T7: A5 on head first (latch like L1), die, climb x=40 from spawn side
    if not cleared:
        print("=== head5_climb ===")
        guid, g = to_l2()
        prev = None
        # L L A5 then anything → die; then L L UUU L L DDD
        seq = [3, 3, 5, 1, 3, 3, 1, 1, 1, 3, 3, 2, 2, 2, 2, 2, 2]
        for i, a_ in enumerate(seq):
            d = act(guid, a_)
            guid = d["guid"]
            g2 = plane(d)
            a = actor(g2, prev)
            print(i, "A" + str(a_), a, e8(g2), "lv", d.get("levels_completed"), "b", body_ndiff(g, g2))
            g, prev = g2, a
            if (d.get("levels_completed") or 0) >= 2:
                cleared = True
                cleared_seq = seq[: i + 1]
                print("PASS head5_climb")
                break
        if prev:
            print("final fps D", fp(g, prev["cx"], prev["cy"] + 6))
            print("final fps L", fp(g, prev["cx"] - 6, prev["cy"]))
        all_logs["head5_climb"] = {"final": prev, "e8": e8(g), "lv": d.get("levels_completed")}

    OUT.write_text(json.dumps({
        "cleared": cleared,
        "cleared_seq": cleared_seq,
        "method": "top_corridor_down",
        "logs": all_logs,
    }, indent=2, default=str), encoding="utf-8")
    print("CLEARED", cleared)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
