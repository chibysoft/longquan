"""g50t: track playfield color-9 actor (exclude HUD), confirm dirs, short path try."""
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
OUT = ROOT / "tests/fixtures/g50t_l1_dir_clear_try.json"


def H(key, j=False):
    h = {"X-API-Key": key, "Accept": "application/json"}
    if j:
        h["Content-Type"] = "application/json"
    return h


def plane(d):
    a = np.asarray(d["frame"], dtype=np.int64)
    return a[0] if a.ndim == 3 else a


def ccs9(g, y0=7, y1=62):
    """Color-9 CCs in playfield band (exclude top HUD y<=5, keep bottom goal)."""
    H_, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(y0, min(y1, H_)):
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
                    if (
                        0 <= nx < W
                        and y0 <= ny < min(y1, H_)
                        and not seen[ny, nx]
                        and int(g[ny, nx]) == 9
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
    """Playfield actor: color9 CC with cy < 45, largest n (start blob ~24)."""
    cands = [b for b in ccs9(g) if b["cy"] < 45 and 10 <= b["n"] <= 40]
    if not cands:
        cands = [b for b in ccs9(g) if b["cy"] < 45]
    if not cands:
        return None
    return max(cands, key=lambda b: b["n"])


def goal(g):
    cands = [b for b in ccs9(g) if b["cy"] >= 45]
    return max(cands, key=lambda b: b["n"]) if cands else None


def body_ndiff(a, b):
    return int(np.sum(a[1:63] != b[1:63]))


def bar63(g):
    row = g[63]
    return {"n1": int(np.sum(row == 1)), "n9": int(np.sum(row == 9))}


def main():
    key = _api_key()
    s = requests.Session()
    card = s.post(
        f"{BASE}/api/scorecard/open", headers=H(key, True), json={"tags": TAGS}, timeout=30
    ).json()["card_id"]
    gid = s.get(f"{BASE}/api/games/g50t", headers=H(key), timeout=20).json()["game_id"]
    print("card", card, gid)

    def reset():
        return s.post(
            f"{BASE}/api/cmd/RESET",
            headers=H(key, True),
            json={"card_id": card, "game_id": gid},
            timeout=30,
        ).json()

    def act(guid, aid):
        r = s.post(
            f"{BASE}/api/cmd/ACTION{aid}",
            headers=H(key, True),
            json={"game_id": gid, "guid": guid},
            timeout=30,
        )
        r.raise_for_status()
        d = r.json()
        if "guid" not in d:
            raise RuntimeError(f"no guid in response keys={list(d.keys())} body={ {k:d.get(k) for k in d if k!='frame'} }")
        return d

    result = {"card_id": card, "game_id": gid, "tags": TAGS}

    d0 = reset()
    g0 = plane(d0)
    result["reset"] = {
        "actor": actor(g0),
        "goal": goal(g0),
        "all_pf9": ccs9(g0),
        "levels": d0.get("levels_completed"),
        "acts": d0.get("available_actions"),
        "n8": int(np.sum(g0 == 8)),
    }
    print("reset", result["reset"])

    # Directional: measure 2nd identical press (1st often noop)
    dir_rows = []
    for aid in [1, 2, 3, 4, 5]:
        d = reset()
        g = plane(d)
        guid = d["guid"]
        a0 = actor(g)
        d = act(guid, aid)
        guid = d["guid"]
        g1 = plane(d)
        d = act(guid, aid)
        guid = d["guid"]
        g2 = plane(d)
        a1, a2 = actor(g1), actor(g2)
        dx = None if not (a1 and a2) else round(a2["cx"] - a1["cx"], 2)
        dy = None if not (a1 and a2) else round(a2["cy"] - a1["cy"], 2)
        label = "NOMOVE"
        if dx is not None and dy is not None:
            if abs(dx) > abs(dy) and abs(dx) >= 0.5:
                label = "RIGHT" if dx > 0 else "LEFT"
            elif abs(dy) >= 0.5:
                label = "DOWN" if dy > 0 else "UP"
        row = {
            "action": f"ACTION{aid}",
            "a0": a0,
            "first_body": body_ndiff(g, g1),
            "second_body": body_ndiff(g1, g2),
            "a1": a1,
            "a2": a2,
            "dx": dx,
            "dy": dy,
            "label": label,
            "bar2": bar63(g2),
            "n8_2": int(np.sum(g2 == 8)),
        }
        dir_rows.append(row)
        print(f"A{aid} bodies={row['first_body']}/{row['second_body']} Δ=({dx},{dy}) {label} a2={a2}")

    result["directions"] = dir_rows
    dir_map = {r["action"]: r["label"] for r in dir_rows if r["label"] != "NOMOVE"}
    result["dir_map"] = dir_map
    print("dir_map", dir_map)

    # Continuous march in each moving direction (up to 12 effective steps)
    marches = {}
    for aid, label in [(2, "DOWN"), (4, "RIGHT"), (3, "LEFT"), (1, "UP")]:
        d = reset()
        g = plane(d)
        guid = d["guid"]
        log = []
        for i in range(16):
            d = act(guid, aid)
            guid = d["guid"]
            g2 = plane(d)
            a = actor(g2)
            entry = {
                "i": i,
                "body": body_ndiff(g, g2),
                "actor": a,
                "n8": int(np.sum(g2 == 8)),
                "levels": d.get("levels_completed"),
                "state": d.get("state"),
                "bar": bar63(g2),
            }
            log.append(entry)
            g = g2
            if (d.get("levels_completed") or 0) >= 1:
                break
        marches[label] = {
            "aid": aid,
            "start": log[0] if log else None,
            "end": log[-1] if log else None,
            "moves": [e for e in log if e["body"] > 5],
            "levels": log[-1]["levels"] if log else 0,
        }
        print(label, "moves", len(marches[label]["moves"]), "end", marches[label]["end"])
    result["marches"] = marches

    # Manual corridor path guess from ASCII:
    # actor starts ~ (16,10); open floor is color0/inside 5 walls.
    # From ASCII: right along y~8-12 channel until near x=38 8-hazard, then need to go down gaps.
    # Looking at maze: at y14-18 there are gaps in walls. Try RRR then DDD through gap then RRR...
    sequences = {
        "R8": [4] * 10,
        "D8": [2] * 10,
        "R3D6R6D10": [4] * 3 + [2] * 6 + [4] * 6 + [2] * 10,
        "R3D3R3D3R6D12": [4, 4, 4, 2, 2, 2, 4, 4, 4, 2, 2, 2, 4, 4, 4, 4, 4, 4] + [2] * 14,
        "R2D8R8": [4, 4] + [2] * 8 + [4] * 8,
        "with5_R4_5_D4": [4, 4, 4, 4, 5, 2, 2, 2, 2],
    }
    seq_out = {}
    for name, seq in sequences.items():
        d = reset()
        g = plane(d)
        guid = d["guid"]
        log = []
        for i, aid in enumerate(seq):
            d = act(guid, aid)
            guid = d["guid"]
            g2 = plane(d)
            a = actor(g2)
            gl = goal(g2)
            log.append({
                "i": i,
                "a": aid,
                "body": body_ndiff(g, g2),
                "actor": a,
                "goal": gl,
                "n8": int(np.sum(g2 == 8)),
                "levels": d.get("levels_completed"),
                "state": d.get("state"),
            })
            g = g2
            if (d.get("levels_completed") or 0) >= 1:
                break
        seq_out[name] = {
            "levels": log[-1]["levels"] if log else 0,
            "end_actor": log[-1]["actor"] if log else None,
            "end_goal": log[-1]["goal"] if log else None,
            "moves": [e for e in log if e["body"] > 5],
            "n8_min": min((e["n8"] for e in log), default=None),
            "n8_end": log[-1]["n8"] if log else None,
        }
        print(name, "lv", seq_out[name]["levels"], "actor", seq_out[name]["end_actor"],
              "moves", len(seq_out[name]["moves"]), "n8", seq_out[name]["n8_min"], "->", seq_out[name]["n8_end"])
    result["sequences"] = seq_out

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
