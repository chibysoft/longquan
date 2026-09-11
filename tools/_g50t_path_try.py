"""g50t L1 path try with 1-step command buffer model."""
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
OUT = ROOT / "tests/fixtures/g50t_l1_path_try.json"


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
    cands = [b for b in ccs(g, 9, 7, 48) if 10 <= b["n"] <= 40]
    return max(cands, key=lambda b: b["n"]) if cands else None


def goal(g):
    cands = [b for b in ccs(g, 9, 45, 62)]
    return max(cands, key=lambda b: b["n"]) if cands else None


def body_ndiff(a, b):
    return int(np.sum(a[1:63] != b[1:63]))


def hud(g):
    # top-left icons and bottom bar
    return {
        "bar_n1": int(np.sum(g[63] == 1)),
        "top_hist": {int(k): int(v) for k, v in zip(*np.unique(g[0:6, 0:12], return_counts=True))},
        "c1_n": int(np.sum(g == 1)),
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

    def run_seq(name, seq):
        d = reset()
        g = plane(d)
        guid = d["guid"]
        log = []
        for i, aid in enumerate(seq):
            d = act(guid, aid)
            guid = d["guid"]
            g2 = plane(d)
            a = actor(g2)
            entry = {
                "i": i,
                "a": aid,
                "body": body_ndiff(g, g2),
                "actor": a,
                "goal": goal(g2),
                "n8": int(np.sum(g2 == 8)),
                "hud": hud(g2),
                "levels": d.get("levels_completed"),
                "state": d.get("state"),
            }
            log.append(entry)
            g = g2
            if (d.get("levels_completed") or 0) >= 1:
                break
            # detect respawn to start after having moved
            if (
                i > 2
                and a
                and a["cx"] == 16.0
                and a["cy"] == 10.0
                and entry["body"] > 60
            ):
                entry["respawn"] = True
        print(
            name,
            "lv",
            log[-1]["levels"],
            "end",
            log[-1]["actor"],
            "n8",
            log[-1]["n8"],
            "bar",
            log[-1]["hud"]["bar_n1"],
            "moves",
            sum(1 for e in log if e["body"] >= 48),
        )
        return {
            "seq": seq,
            "levels": log[-1]["levels"],
            "end": log[-1],
            "log": log,
            "respawns": sum(1 for e in log if e.get("respawn")),
        }

    result = {"card": card, "game": gid}

    # Buffer-aware paths. Step=6. Start (16,10). Goal ~(47,52).
    # Down 4 steps -> (16,34); Right 4 -> (40,34); need more routing.
    paths = {
        # 4 effective downs from reset: 5x A2
        "D4": [2] * 5,
        # 4 down + 4 right: after downs queue=D; first R executes D (5th down!), then R...
        # Careful: want exactly 4D then 4R.
        # From reset empty: D,D,D,D,D = 4 moves down, queue D
        # Then R: executes 5th D!, queue R — overshoot
        # To stop vertical: need a flush. A5 as STOP?
        # After 4D with queue D: press A5 -> exec D (5th), queue STOP
        # Then A5 -> exec STOP, queue STOP
        # Then R,R,... 
        "D4_stop_R4": [2] * 5 + [5, 5] + [4] * 5,
        # Simpler greedy without stop: just D5 R8 D8 R4
        "D5_R8_D8_R6": [2] * 6 + [4] * 9 + [2] * 9 + [4] * 7,
        # Go down to gap y~28 (3 steps: cy 10->28), right through mid
        "D3_R5_D4_R3": [2] * 4 + [4] * 6 + [2] * 5 + [4] * 4,
        # Stay high: R3 to (34,10), D toward lower — may hit 8s
        "R3_D6_R3_D6": [4] * 4 + [2] * 7 + [4] * 4 + [2] * 7,
        # Left shaft all the way then right along bottom openness
        "D6_R7_D4": [2] * 7 + [4] * 8 + [2] * 5,
        # Probe A5 as stop only once
        "D4_R1flush_R4": [2] * 5 + [4] + [4] * 5,  # first R flushes extra D
    }

    out = {}
    for name, seq in paths.items():
        out[name] = run_seq(name, seq)
    result["paths"] = {k: {kk: vv for kk, vv in v.items() if kk != "log"} | {"log_tail": v["log"][-8:], "move_steps": [e for e in v["log"] if e["body"] >= 40][:20]} for k, v in out.items()}

    # Closed-loop controller: maintain desired dir with buffer awareness
    # State: pending intent. Each press sets next intent; physics applies previous.
    d = reset()
    g = plane(d)
    guid = d["guid"]
    gl = goal(g)
    ctrl_log = []
    pending = None  # last commanded
    # target cells in actor-center space (multiples of 6 from start)
    # waypoints: (16,34) -> (40,34) -> (40,52) -> (46,52)
    waypoints = [(16, 34), (40, 34), (46, 52)]
    wp_i = 0
    for step in range(50):
        a = actor(g)
        if not a or not gl:
            break
        tx, ty = waypoints[wp_i]
        if abs(a["cx"] - tx) < 1 and abs(a["cy"] - ty) < 1:
            wp_i = min(wp_i + 1, len(waypoints) - 1)
            tx, ty = waypoints[wp_i]
        dx = tx - a["cx"]
        dy = ty - a["cy"]
        if abs(dx) < 1 and abs(dy) < 1 and wp_i == len(waypoints) - 1:
            # at final WP — try more downs/rights toward goal center
            dx = gl["cx"] - a["cx"]
            dy = gl["cy"] - a["cy"]
        if abs(dx) >= abs(dy) and abs(dx) >= 1:
            want = 4 if dx > 0 else 3
        elif abs(dy) >= 1:
            want = 2 if dy > 0 else 1
        else:
            want = 5  # idle
        d = act(guid, want)
        guid = d["guid"]
        g2 = plane(d)
        entry = {
            "step": step,
            "want": want,
            "body": body_ndiff(g, g2),
            "actor": actor(g2),
            "wp": waypoints[wp_i],
            "n8": int(np.sum(g2 == 8)),
            "hud": hud(g2),
            "levels": d.get("levels_completed"),
            "state": d.get("state"),
        }
        ctrl_log.append(entry)
        g = g2
        if (d.get("levels_completed") or 0) >= 1:
            break
        # abort on repeated respawn
        if entry["actor"] and entry["body"] > 60 and entry["actor"]["cy"] == 10 and entry["actor"]["cx"] == 16 and step > 5:
            # one respawn ok; count
            pass
    print(
        "CTRL lv",
        ctrl_log[-1]["levels"] if ctrl_log else None,
        "end",
        ctrl_log[-1]["actor"] if ctrl_log else None,
        "steps",
        len(ctrl_log),
    )
    result["controller"] = {
        "levels": ctrl_log[-1]["levels"] if ctrl_log else 0,
        "end": ctrl_log[-1] if ctrl_log else None,
        "log": ctrl_log,
    }

    # Full dump of best-looking path logs
    result["raw_paths"] = out

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
