"""g50t: reproduce shaft-open after head touch; push to goal; levels check."""
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
OUT = ROOT / "tests/fixtures/g50t_l1_clear_attempt.json"


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


def play9(g):
    """Player ring: n~24 in playfield, not HUD/bar."""
    cands = [b for b in all9(g) if 7 <= b["box"][1] and b["box"][3] <= 62 and 15 <= b["n"] <= 30]
    return cands


def e8(g):
    ys, xs = np.where(g == 8)
    if len(xs) == 0:
        return {"n": 0}
    return {
        "n": int(len(xs)),
        "shaft": int(np.sum(g[38:43, 14:19] == 8)),
        "xmin": int(xs.min()),
        "ymin": int(ys.min()),
    }


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

    def run(name, seq):
        d = reset()
        g = plane(d)
        guid = d["guid"]
        log = []
        for i, aid in enumerate(seq):
            d = act(guid, aid)
            guid = d["guid"]
            g2 = plane(d)
            entry = {
                "i": i,
                "a": aid,
                "body": body_ndiff(g, g2),
                "play": play9(g2),
                "e8": e8(g2),
                "bar": int(np.sum(g2[63] == 1)),
                "levels": d.get("levels_completed"),
                "state": d.get("state"),
            }
            log.append(entry)
            p = entry["play"][0] if entry["play"] else None
            print(
                f"{name} {i} A{aid} body={entry['body']} play={p} e8={entry['e8']} "
                f"lv={entry['levels']} st={entry['state']}"
            )
            g = g2
            if (d.get("levels_completed") or 0) >= 1 or d.get("state") == "WIN":
                break
        return log

    result = {}

    # Reproduce prior: R5, A5, then many D then R to goal
    result["head5_D_R"] = run(
        "H5DR",
        [4] * 5 + [5] + [2] * 12 + [4] * 10,
    )

    # Cleaner: R5 to head, L4 back to start (no A5 death), then D down
    result["head_L_D"] = run(
        "HLD",
        [4] * 5 + [3] * 5 + [2] * 12 + [4] * 10,
    )

    # No head: just D and see
    result["just_D"] = run("JD", [2] * 16 + [4] * 10)

    # Head then immediately D without A5 (buffer will exec R first)
    result["head_D"] = run("HD", [4] * 5 + [2] * 14 + [4] * 10)

    # Best continuation if we reach (16,40): need D to 46/52 then R to goal
    # From successful H5DR log, craft extended
    result["long"] = run(
        "LONG",
        [4] * 5 + [5] + [2] * 16 + [4] * 12 + [2] * 4 + [4] * 4,
    )

    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print("wrote", OUT)
    # summarize levels
    for k, log in result.items():
        lv = max(e["levels"] or 0 for e in log)
        reached = [e for e in log if e["play"] and e["play"][0]["cy"] >= 40]
        print(k, "max_lv", lv, "deep_steps", len(reached), "last", log[-1]["play"], log[-1]["e8"])

    s.post(
        f"{BASE}/api/scorecard/close",
        headers=H(key, True),
        json={"card_id": card},
        timeout=15,
    )


if __name__ == "__main__":
    main()
