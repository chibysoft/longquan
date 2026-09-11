"""g50t: does ACTION5 switch to a second actor / goal entity?"""
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
OUT = ROOT / "tests/fixtures/g50t_l1_switch_try.json"


def H(key, j=False):
    h = {"X-API-Key": key, "Accept": "application/json"}
    if j:
        h["Content-Type"] = "application/json"
    return h


def plane(d):
    a = np.asarray(d["frame"], dtype=np.int64)
    return a[0] if a.ndim == 3 else a


def all9(g):
    H_, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(H_):
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
                    if 0 <= nx < W and 0 <= ny < H_ and not seen[ny, nx] and int(g[ny, nx]) == 9:
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            out.append({
                "n": len(cells),
                "cx": round(sum(xs) / len(xs), 2),
                "cy": round(sum(ys) / len(ys), 2),
                "box": [min(xs), min(ys), max(xs), max(ys)],
            })
    out.sort(key=lambda b: (b["cy"], b["cx"]))
    return out


def actor_play(g):
    cands = [b for b in all9(g) if 7 <= b["cy"] <= 54 and 10 <= b["n"] <= 40]
    # exclude goal-ish
    play = [b for b in cands if b["cy"] < 45]
    return play


def body_ndiff(a, b):
    return int(np.sum(a[1:63] != b[1:63]))


def e8(g):
    ys, xs = np.where(g == 8)
    if len(xs) == 0:
        return {"n": 0}
    return {
        "n": int(len(xs)),
        "shaft": int(np.sum(g[38:43, 14:19] == 8)),
        "xmin": int(xs.min()),
    }


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

    result = {}

    # Baseline all9
    d = reset()
    g = plane(d)
    result["reset_all9"] = all9(g)
    print("reset9", all9(g))

    # On head, A5 once, list all9 + try move - see if southern 9 moves
    d = reset()
    g = plane(d)
    guid = d["guid"]
    for _ in range(5):
        d = act(guid, 4)
        guid = d["guid"]
        g = plane(d)
    d = act(guid, 5)
    guid = d["guid"]
    g = plane(d)
    print("head+A5", actor_play(g), "all9", all9(g), "e8", e8(g))
    result["head_A5"] = {"play": actor_play(g), "all9": all9(g), "e8": e8(g)}

    # After head+A5, try DOWN many - if control switched to something that can go shaft
    log = []
    for i in range(12):
        d = act(guid, 2)
        guid = d["guid"]
        g2 = plane(d)
        log.append({
            "i": i,
            "body": body_ndiff(g, g2),
            "play": actor_play(g2),
            "all9": all9(g2),
            "e8": e8(g2),
            "levels": d.get("levels_completed"),
        })
        print("D", i, log[-1]["body"], log[-1]["play"], log[-1]["e8"], "lv", log[-1]["levels"])
        g = g2
        if (d.get("levels_completed") or 0) >= 1:
            break
    result["after_switch_D"] = log

    # Try: go to head, A5 once (stay), then A5 is death - so instead
    # go to head WITHOUT flush, press A5 as first which executes queued R (noop) 
    # Actually: maybe A5 means DROP a block that holds the switch?
    # Compare frame on-head vs after single A5 for any new color cells
    d = reset()
    g = plane(d)
    guid = d["guid"]
    for _ in range(5):
        d = act(guid, 4)
        guid = d["guid"]
        g = plane(d)
    g_head = g.copy()
    d = act(guid, 5)
    guid = d["guid"]
    g_a5 = plane(d)
    delta = g_head != g_a5
    ys, xs = np.where(delta)
    changes = [(int(x), int(y), int(g_head[y, x]), int(g_a5[y, x])) for y, x in zip(ys, xs)]
    print("A5 delta from head", changes[:40], "n", len(changes))
    result["a5_delta"] = changes

    # Two-entity theory: southern 9 might be movable with A5 toggle
    # From RESET, press A5 twice (first noop queue, second exec A5), then move and watch south 9
    d = reset()
    g = plane(d)
    guid = d["guid"]
    south0 = [b for b in all9(g) if b["cy"] > 45]
    d = act(guid, 5)
    guid = d["guid"]
    d = act(guid, 5)
    guid = d["guid"]
    g = plane(d)
    print("double5 from reset", all9(g), "body vs start south", south0)
    # move D and see
    log2 = []
    for i, aid in enumerate([2, 2, 2, 4, 4, 4, 1, 1, 3, 3]):
        d = act(guid, aid)
        guid = d["guid"]
        g2 = plane(d)
        log2.append({
            "a": aid,
            "body": body_ndiff(g, g2),
            "all9": all9(g2),
            "play": actor_play(g2),
            "levels": d.get("levels_completed"),
        })
        print("x", aid, log2[-1]["body"], log2[-1]["play"], [b for b in log2[-1]["all9"] if b["cy"] > 45])
        g = g2
    result["double5_then_move"] = log2

    # Soft-drop theory: stand on head, A5 places a STONE (maybe color1/9) that holds pressure
    # Look for any non-9/5/8/0 new pixels after various A5 timings
    # Already a5_delta listed.

    # Maybe the HOLD opens shaft and the GOAL is to get the southern object somehow -
    # or levels complete when snake n8 reduced AND actor returns to start?
    d = reset()
    g = plane(d)
    guid = d["guid"]
    for _ in range(5):
        d = act(guid, 4)
        guid = d["guid"]
        g = plane(d)
    # return to start quickly  
    for aid in [3, 3, 3, 3, 3]:
        d = act(guid, aid)
        guid = d["guid"]
        g2 = plane(d)
        print("ret", actor_play(g2), e8(g2), "lv", d.get("levels_completed"))
        g = g2
    result["return_start"] = {"play": actor_play(g), "e8": e8(g), "levels": d.get("levels_completed")}

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
