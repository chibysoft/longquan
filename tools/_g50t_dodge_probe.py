"""g50t: probe ACTION5 wait/hazard motion; unlock LEFT/UP; dodge toward goal."""
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
OUT = ROOT / "tests/fixtures/g50t_l1_dodge_probe.json"


def H(key, j=False):
    h = {"X-API-Key": key, "Accept": "application/json"}
    if j:
        h["Content-Type"] = "application/json"
    return h


def plane(d):
    a = np.asarray(d["frame"], dtype=np.int64)
    return a[0] if a.ndim == 3 else a


def ccs(g, color, y0=1, y1=63):
    H_, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(y0, min(y1, H_)):
        for x in range(W):
            if seen[y, x] or int(g[y, x]) != color:
                continue
            stack = [(x, y)]
            seen[y, x] = True
            cells = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (
                        0 <= nx < W
                        and y0 <= ny < min(y1, H_)
                        and not seen[ny, nx]
                        and int(g[ny, nx]) == color
                    ):
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


def actor(g):
    cands = [b for b in ccs(g, 9, 7, 45) if 10 <= b["n"] <= 40]
    return max(cands, key=lambda b: b["n"]) if cands else None


def hazard(g):
    hs = ccs(g, 8, 7, 62)
    return hs[0] if hs else None


def body_ndiff(a, b):
    return int(np.sum(a[1:63] != b[1:63]))


def diff_hist(a, b):
    from collections import Counter
    m = a[1:63] != b[1:63]
    ys, xs = np.where(m)
    hist = Counter()
    for y, x in zip(ys.tolist(), xs.tolist()):
        hist[(int(a[y + 1, x]), int(b[y + 1, x]))] += 1
    return {f"{u}->{v}": n for (u, v), n in hist.most_common(12)}


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

    result = {"card": card, "game": gid}

    # Pure ACTION5 chain from RESET
    d = reset()
    g = plane(d)
    guid = d["guid"]
    wait_log = []
    for i in range(12):
        d = act(guid, 5)
        guid = d["guid"]
        g2 = plane(d)
        wait_log.append({
            "i": i,
            "body": body_ndiff(g, g2),
            "hist": diff_hist(g, g2),
            "actor": actor(g2),
            "hazard": hazard(g2),
            "n8": int(np.sum(g2 == 8)),
            "levels": d.get("levels_completed"),
        })
        print("WAIT", i, wait_log[-1]["body"], wait_log[-1]["hist"], "hz", wait_log[-1]["hazard"])
        g = g2
    result["wait_chain"] = wait_log

    # After moving RIGHT once (effective), try LEFT twice
    d = reset()
    g = plane(d)
    guid = d["guid"]
    for aid in [4, 4]:  # noop + right
        d = act(guid, aid)
        guid = d["guid"]
        g = plane(d)
    a_mid = actor(g)
    left_log = []
    for i in range(6):
        d = act(guid, 3)
        guid = d["guid"]
        g2 = plane(d)
        left_log.append({
            "i": i,
            "body": body_ndiff(g, g2),
            "hist": diff_hist(g, g2),
            "actor": actor(g2),
            "dx": None if not (actor(g) and actor(g2)) else round(actor(g2)["cx"] - actor(g)["cx"], 2),
        })
        print("LEFT", i, left_log[-1])
        g = g2
    result["left_after_right"] = {"mid": a_mid, "log": left_log}

    # After moving DOWN once, try UP
    d = reset()
    g = plane(d)
    guid = d["guid"]
    for aid in [2, 2]:
        d = act(guid, aid)
        guid = d["guid"]
        g = plane(d)
    a_mid = actor(g)
    up_log = []
    for i in range(6):
        d = act(guid, 1)
        guid = d["guid"]
        g2 = plane(d)
        up_log.append({
            "i": i,
            "body": body_ndiff(g, g2),
            "hist": diff_hist(g, g2),
            "actor": actor(g2),
            "dy": None if not (actor(g) and actor(g2)) else round(actor(g2)["cy"] - actor(g)["cy"], 2),
        })
        print("UP", i, up_log[-1])
        g = g2
    result["up_after_down"] = {"mid": a_mid, "log": up_log}

    # Interleave move + wait: R,R,5,5,R,R,5,5,... watch hazard vs actor
    d = reset()
    g = plane(d)
    guid = d["guid"]
    inter = []
    seq = [4, 4, 5, 5, 4, 4, 5, 5, 2, 2, 5, 5, 4, 4, 5, 5, 2, 2, 2, 2, 5, 5, 4, 4, 4, 4]
    for i, aid in enumerate(seq):
        d = act(guid, aid)
        guid = d["guid"]
        g2 = plane(d)
        inter.append({
            "i": i,
            "a": aid,
            "body": body_ndiff(g, g2),
            "hist": diff_hist(g, g2) if body_ndiff(g, g2) else {},
            "actor": actor(g2),
            "hazard": hazard(g2),
            "n8": int(np.sum(g2 == 8)),
            "levels": d.get("levels_completed"),
            "state": d.get("state"),
        })
        print(
            f"INT {i} A{aid} body={inter[-1]['body']} act={inter[-1]['actor']} "
            f"n8={inter[-1]['n8']} lv={inter[-1]['levels']}"
        )
        g = g2
        if (d.get("levels_completed") or 0) >= 1:
            break
    result["interleave"] = inter

    # Hazard-only motion: stand still with A5 after being away from hazard
    # First go DOWN to y=34 (safe left corridor), then wait many
    d = reset()
    g = plane(d)
    guid = d["guid"]
    for _ in range(10):
        d = act(guid, 2)
        guid = d["guid"]
        g = plane(d)
    deep_wait = []
    for i in range(16):
        d = act(guid, 5)
        guid = d["guid"]
        g2 = plane(d)
        deep_wait.append({
            "i": i,
            "body": body_ndiff(g, g2),
            "hist": diff_hist(g, g2),
            "actor": actor(g2),
            "hazard": hazard(g2),
            "n8": int(np.sum(g2 == 8)),
        })
        print("DEEPWAIT", i, deep_wait[-1]["body"], deep_wait[-1]["hazard"], deep_wait[-1]["hist"])
        g = g2
    result["deep_wait"] = {"actor_before_wait": actor(g), "log": deep_wait}

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
