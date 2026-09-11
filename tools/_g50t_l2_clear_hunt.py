"""g50t L2 clear hunt: L to snake head ~(40,28), A5 latch, path to mid goal ~(29,22)."""
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


def ccs(g, color, y0=7, y1=56, min_n=15, max_n=30):
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
            if min_n <= len(cells) <= max_n:
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
    rings = [b for b in ccs(g, 9, 7, 56, 20, 28) if b["n"] == 24]
    if not rings:
        rings = ccs(g, 9, 7, 56, 15, 30)
    if not rings:
        return None
    # prefer right-spawn / movable: largest cx among n=24, or closest to last
    return max(rings, key=lambda b: b["cx"])


def goal(g):
    rings = [b for b in ccs(g, 9, 7, 56, 15, 22) if b["n"] == 19]
    return rings[0] if rings else None


def e8(g):
    ys, xs = np.where(g[1:63] == 8)
    if len(xs) == 0:
        return {"n": 0}
    ys = ys + 1
    return {
        "n": int(len(xs)),
        "xmin": int(xs.min()),
        "xmax": int(xs.max()),
        "ymin": int(ys.min()),
        "ymax": int(ys.max()),
        "shaft_L": int(np.sum(g[38:43, 14:19] == 8)),
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

    def to_l2():
        d = reset()
        guid = d["guid"]
        g = plane(d)
        for aid in L1_SEQ + [2] * 4 + [4] * 8:
            d = act(guid, aid)
            guid = d["guid"]
            g = plane(d)
            if (d.get("levels_completed") or 0) >= 1:
                break
        else:
            raise RuntimeError("L1 fail")
        # transition into L2
        d = act(guid, 3)  # LEFT enter — queues toward head
        return d["guid"], plane(d), d

    def run(name, seq):
        guid, g, d = to_l2()
        log = []
        print(name, "start", actor(g), "goal", goal(g), "e8", e8(g), "lv", d.get("levels_completed"))
        for i, aid in enumerate(seq):
            d = act(guid, aid)
            guid = d["guid"]
            g2 = plane(d)
            entry = {
                "i": i,
                "a": aid,
                "body": body_ndiff(g, g2),
                "actor": actor(g2),
                "goal": goal(g2),
                "e8": e8(g2),
                "levels": d.get("levels_completed"),
                "state": d.get("state"),
            }
            log.append(entry)
            a = entry["actor"]
            print(
                f"  {i} A{aid} b={entry['body']} act={a} e8={entry['e8'].get('n')} "
                f"shaft={entry['e8'].get('shaft_L')} lv={entry['levels']}"
            )
            g = g2
            if (d.get("levels_completed") or 0) >= 2:
                print(name, "PASS levels 1→2")
                break
        return log

    trials = {}
    # After enter A3: at L2, first L may exec transition leftover / move
    # Target head ~(40,28): from ~(52,28) need 2 lefts effective → ~3 L presses + buffer
    # L1 style: reach head, A5, then death-exec A5 via next key, then navigate

    trials["L_head_A5_D"] = run(
        "L_head_A5_D",
        # enter already sent A3; continue L to head, A5, then explore
        [3, 3, 3, 5] + [2] * 2 + [3] * 6 + [1] * 4 + [3] * 4 + [2] * 4 + [4] * 4,
    )

    trials["L_head_A5_L1style"] = run(
        "L_head_A5_L1style",
        # reach head, A5, next action triggers latch death, then path
        [3, 3, 3, 5, 2] + [3] * 8 + [1] * 6 + [3] * 4 + [2] * 6 + [4] * 6,
    )

    # Hold on head: L to head, A5 once (stay), probe U/D/L
    trials["hold_U"] = run("hold_U", [3, 3, 3, 5, 1, 1, 1, 1, 3, 3, 3, 2, 2])
    trials["hold_L"] = run("hold_L", [3, 3, 3, 5, 3, 3, 3, 3, 1, 1, 2, 2, 4, 4])
    trials["hold_D"] = run("hold_D", [3, 3, 3, 5, 2, 2, 2, 2, 3, 3, 1, 1])

    # U first to y=22 then L toward goal x
    trials["U_L_to_goal"] = run(
        "U_L_to_goal",
        [1, 1, 1, 3, 3, 3, 3, 3, 3, 5, 3, 3, 2, 2, 3, 3, 1, 1],
    )

    # D to bottom then L
    trials["D_L"] = run("D_L", [2, 2, 2, 2, 3, 3, 3, 3, 3, 5, 3, 3, 1, 1, 1, 3, 3])

    # After head shrink without A5, leave and return (oscillate)
    trials["stomp"] = run("stomp", [3, 3, 3, 4, 4, 3, 3, 5, 2, 3, 3, 3, 1, 1, 3, 3])

    # Long latch: head A5, death, then left corridor
    trials["latch_long"] = run(
        "latch_long",
        [3, 3, 3, 5, 1]  # death via A5 exec on U?
        + [3] * 10
        + [1] * 4
        + [3] * 6
        + [2] * 8
        + [4] * 6
        + [1] * 4
        + [3] * 4,
    )

    cleared = any(max(e["levels"] for e in log) >= 2 for log in trials.values())
    best = max(trials.items(), key=lambda kv: max(e["levels"] for e in kv[1]))

    # Detailed log for best approach to head
    detail = {}
    for name, log in trials.items():
        detail[name] = {
            "max_lv": max(e["levels"] for e in log),
            "end": log[-1],
            "at_head": [e for e in log if e["actor"] and abs(e["actor"]["cx"] - 40) < 1 and abs(e["actor"]["cy"] - 28) < 1],
            "shrink": [e for e in log if e["e8"].get("n", 99) < 98],
            "moved": [e for e in log if e["body"] > 20][:20],
            "log": log,
        }

    OUT.write_text(json.dumps({
        "cleared": cleared,
        "best": best[0],
        "trials": detail,
    }, indent=2, default=str), encoding="utf-8")
    print("CLEARED", cleared, "best", best[0], "lv", detail[best[0]]["max_lv"])

    s.post(
        f"{BASE}/api/scorecard/close",
        headers=H(key, True),
        json={"card_id": card},
        timeout=15,
    )


if __name__ == "__main__":
    main()
