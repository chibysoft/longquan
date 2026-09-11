"""g50t L2 micro: from (40,22)/(40,16) after latch, press LEFT toward goal."""
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
    if len(cands) == 1:
        return cands[0]
    # prefer non-static: not the one that never moves — use all, pick by recent
    return cands


def e8(g):
    ys, xs = np.where(g[1:63] == 8)
    info = {"n": int(len(xs))}
    if len(xs):
        info.update({
            "xmin": int(xs.min()), "xmax": int(xs.max()),
            "ymin": int(ys.min() + 1), "ymax": int(ys.max() + 1),
            "shaft_L": int(np.sum(g[38:43, 14:19] == 8)),
        })
    return info


def footprint(g, cx, cy):
    cells = []
    for oy in range(-2, 3):
        row = []
        for ox in range(-2, 3):
            row.append(int(g[cy + oy, cx + ox]))
        cells.append(row)
    return cells


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

    def pick_actor(g, prev=None):
        a = actor(g)
        if isinstance(a, list):
            if prev:
                return min(a, key=lambda b: abs(b["cx"] - prev["cx"]) + abs(b["cy"] - prev["cy"]))
            return max(a, key=lambda b: b["cx"])
        return a

    def run(name, seq):
        guid, g = to_l2()
        log = []
        prev = None
        print("====", name)
        for i, aid in enumerate(seq):
            d = act(guid, aid)
            guid = d["guid"]
            g2 = plane(d)
            a = pick_actor(g2, prev)
            entry = {
                "i": i,
                "a": aid,
                "body": body_ndiff(g, g2),
                "actor": a,
                "e8": e8(g2),
                "levels": d.get("levels_completed"),
                "state": d.get("state"),
            }
            if a and abs(a["cx"] - 40) < 1 and a["cy"] in (16.0, 22.0, 28.0):
                entry["fp_left"] = footprint(g2, int(a["cx"]) - 6, int(a["cy"]))
            log.append(entry)
            print(f"  {i} A{aid} b={entry['body']} {a} e8n={entry['e8'].get('n')} lv={entry['levels']}")
            if entry.get("fp_left"):
                print("    fp toward L", entry["fp_left"])
            g = g2
            prev = a
            if (d.get("levels_completed") or 0) >= 2:
                print("PASS", name)
                break
        return log

    # Exact hold_L setup then LEFT spam from (40,22)
    seq_base = [3, 3, 3, 5, 3, 3, 3, 1, 1]  # ends intending (40,22)
    trials = {
        "from22_L": run("from22_L", seq_base + [3] * 8 + [2, 2, 1, 1]),
        "from22_L_via16": run(
            "from22_L_via16",
            [3, 3, 3, 5, 3, 3, 3, 1, 1, 1] + [3] * 8 + [2, 2, 2, 4],
        ),
        # bottom to (28,40), then R/L/U probes
        "bottom_2840_explore": run(
            "bottom_2840_explore",
            [3, 3, 5, 2, 2, 2, 2, 2, 3, 3, 3, 3, 1, 1, 1]
            + [4, 4, 3, 3, 1, 1, 1, 1, 4, 4, 2, 2],
        ),
        # Maybe goal is (40,52) bottom like L1? already walk there without clear
        # Try standing on mid goal by path (34,22): from head U then...
        "head_hold_no_death_UL": run(
            "head_hold_no_death_UL",
            # stay: A5 flush, don't exec A5 as death — use blocked R as clock then U
            [3, 3, 3, 5, 4, 1, 1, 1, 3, 3, 3, 3],
        ),
    }

    cleared = any(max(e["levels"] for e in v) >= 2 for v in trials.values())
    OUT.write_text(json.dumps({"cleared": cleared, "trials": {
        k: {"max_lv": max(e["levels"] for e in v), "log": v, "end": v[-1]}
        for k, v in trials.items()
    }}, indent=2, default=str), encoding="utf-8")
    print("CLEARED", cleared)
    for k, v in trials.items():
        print(k, "max", max(e["levels"] for e in v), "end", v[-1]["actor"])

    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
