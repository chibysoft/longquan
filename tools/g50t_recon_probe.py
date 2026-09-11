"""g50t closed-book recon: open scorecard, RESET, dump L1 frame, action diffs.

Independent scorecard tags=["g50t_recon"]. Do NOT share sessions with r11l/tr87/vc33.
No engine source. No canned trajectories as the sole "解".

L1 findings (see docs/g50t-recon.md):
  - A1=UP A2=DOWN A3=LEFT A4=RIGHT, step=6, walk on color-5
  - 1-step command buffer (first press after RESET often noop)
  - Color-8 snake: stand on head ~(40,10) shrinks barrier; leave restores
  - ACTION5 on head latches shrink; then descend left shaft to goal ~(40,52)
  - levels 0→1 evidenced in tests/fixtures/g50t_l1_clear_attempt.json

Usage:
  python tools/g50t_recon_probe.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import BASE, _api_key  # noqa: E402

GAME = "g50t"
TAGS = ["g50t_recon"]
OUT = ROOT / "tests/fixtures/g50t_l1_frame_live.json"
DIFF_OUT = ROOT / "tests/fixtures/g50t_l1_action_diffs.json"
REPORT = ROOT / "docs/g50t-recon.md"
HYPO = ROOT / "docs/g50t-hypotheses.md"


def headers(key: str, json_body: bool = False) -> dict:
    h = {"X-API-Key": key, "Accept": "application/json"}
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def plane(frame) -> np.ndarray:
    a = np.asarray(frame, dtype=np.int64)
    return a[0] if a.ndim == 3 else a


def body_ndiff(a: np.ndarray, b: np.ndarray) -> int:
    """Ignore y=0 chrome and y=63 step bar."""
    return int(np.sum(a[1:63] != b[1:63]))


def ui_bar63(a: np.ndarray, b: np.ndarray) -> list[dict]:
    out = []
    for x in range(a.shape[1]):
        if int(a[63, x]) != int(b[63, x]):
            out.append({"xy": [x, 63], "from": int(a[63, x]), "to": int(b[63, x])})
    return out[:8]


def all_diff_hist(a: np.ndarray, b: np.ndarray) -> dict:
    m = a[1:63] != b[1:63]
    ys, xs = np.where(m)
    hist = Counter()
    for y, x in zip(ys.tolist(), xs.tolist()):
        hist[(int(a[y + 1, x]), int(b[y + 1, x]))] += 1
    return {f"{u}->{v}": n for (u, v), n in hist.most_common(16)}


def components(g: np.ndarray, color: int, min_n: int = 1, max_n: int = 10**9, y_min: int = 0):
    H, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(max(y_min, 0), H):
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
                        and y_min <= ny < H
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
                    "x0": min(xs), "y0": min(ys),
                    "x1": max(xs), "y1": max(ys),
                    "cx": round(sum(xs) / len(cells), 3),
                    "cy": round(sum(ys) / len(cells), 3),
                    "color": color,
                })
    out.sort(key=lambda b: (b["y0"], b["x0"]))
    return out


def player(g: np.ndarray):
    cands = [
        b for b in components(g, 9, 15, 30, y_min=7)
        if b["y1"] <= 54 and b["cy"] < 56
    ]
    play = [b for b in cands if b["cy"] < 48]
    return min(play, key=lambda b: (b["cy"], b["cx"])) if play else None


def summarize(g: np.ndarray, d: dict) -> dict:
    h = {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))}
    comps = {}
    for c in sorted(h):
        cs = components(g, c, 1, 10**6, y_min=0)
        comps[str(c)] = [
            {k: (round(v, 2) if isinstance(v, float) else v) for k, v in b.items()}
            for b in cs[:16]
        ]
        if len(cs) > 16:
            comps[str(c)].append({"_more": len(cs) - 16})
    return {
        "shape": list(g.shape),
        "hist": h,
        "levels_completed": d.get("levels_completed"),
        "win_levels": d.get("win_levels"),
        "available_actions": d.get("available_actions"),
        "state": d.get("state"),
        "full_reset": d.get("full_reset"),
        "n_comps": {c: len(components(g, int(c), 1, 10**6)) for c in h},
        "comps_sample": comps,
        "player": player(g),
    }


def ascii_preview(g: np.ndarray, y0=0, y1=63, x0=0, x1=63) -> list[str]:
    chars = {
        0: ".", 1: "1", 2: "2", 3: " ", 4: "4", 5: "5",
        6: "6", 7: "7", 8: "8", 9: "9", 10: "a", 11: "b",
        12: "c", 13: "d", 14: "e", 15: "f",
    }
    lines = []
    for y in range(y0, min(y1, g.shape[0] - 1) + 1):
        row = "".join(chars.get(int(g[y, x]), "?") for x in range(x0, min(x1, g.shape[1] - 1) + 1))
        if any(ch not in ". " for ch in row):
            lines.append(f"{y:02d}|{row}")
    return lines


def meta(data: dict) -> dict:
    return {
        "levels_completed": data.get("levels_completed"),
        "state": data.get("state"),
        "available_actions": data.get("available_actions"),
        "win_levels": data.get("win_levels"),
    }


class Sess:
    def __init__(self, key: str):
        self.key = key
        self.s = requests.Session()
        self.card_id = None
        self.game_id = None
        self.guid = None

    def open(self):
        r = self.s.post(
            f"{BASE}/api/scorecard/open",
            headers=headers(self.key, True),
            json={"tags": TAGS},
            timeout=30,
        )
        r.raise_for_status()
        self.card_id = r.json()["card_id"]
        r = self.s.get(f"{BASE}/api/games/{GAME}", headers=headers(self.key), timeout=20)
        r.raise_for_status()
        self.game_id = r.json()["game_id"]
        print("opened", GAME, self.game_id, "card", self.card_id)

    def reset(self):
        r = self.s.post(
            f"{BASE}/api/cmd/RESET",
            headers=headers(self.key, True),
            json={"card_id": self.card_id, "game_id": self.game_id},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        self.guid = data["guid"]
        return data

    def action(self, name: str, **kw):
        body = {"game_id": self.game_id, "guid": self.guid, **kw}
        r = self.s.post(
            f"{BASE}/api/cmd/{name}",
            headers=headers(self.key, True),
            json=body,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        self.guid = data.get("guid", self.guid)
        return data

    def close(self):
        if not self.card_id:
            return
        try:
            self.s.post(
                f"{BASE}/api/scorecard/close",
                headers=headers(self.key, True),
                json={"card_id": self.card_id},
                timeout=15,
            )
        except Exception:
            pass


def main():
    key = _api_key()
    if not key:
        raise RuntimeError("ARC_API_KEY not found")
    sess = Sess(key)
    try:
        sess.open()
        d = sess.reset()
        g0 = plane(d["frame"])
        summary = summarize(g0, d)
        summary["preview_lines"] = ascii_preview(g0)
        summary["game_id"] = sess.game_id
        summary["card_id"] = sess.card_id
        summary["tags"] = TAGS

        payload = {
            "summary": {k: v for k, v in summary.items() if k != "preview_lines"},
            "preview_lines": summary["preview_lines"],
            "frame": d["frame"],
            "meta": {
                k: d.get(k)
                for k in (
                    "levels_completed", "win_levels", "available_actions",
                    "state", "full_reset", "guid",
                )
            },
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        print("hist", summary["hist"])
        print("acts", summary["available_actions"], "lv", summary["levels_completed"],
              "win", summary["win_levels"], "player", summary["player"])

        acts = list(summary.get("available_actions") or [])
        # Buffered single-step: RESET, press aid once (often noop), press again (effect)
        per_action = []
        dir_map = {}
        for aid in acts:
            d0 = sess.reset()
            g_a = plane(d0["frame"])
            p_a = player(g_a)
            name = f"ACTION{aid}"
            d1 = sess.action(name)
            g_b = plane(d1["frame"])
            p_b = player(g_b)
            d2 = sess.action(name)
            g_c = plane(d2["frame"])
            p_c = player(g_c)
            dx = None if not (p_b and p_c) else round(p_c["cx"] - p_b["cx"], 2)
            dy = None if not (p_b and p_c) else round(p_c["cy"] - p_b["cy"], 2)
            label = "NOMOVE"
            if dx is not None and dy is not None:
                if abs(dx) > abs(dy) and abs(dx) >= 0.5:
                    label = "RIGHT" if dx > 0 else "LEFT"
                elif abs(dy) >= 0.5:
                    label = "DOWN" if dy > 0 else "UP"
            if label != "NOMOVE":
                dir_map[name] = {"dir": label, "dx": dx, "dy": dy}
            row = {
                "action": name,
                "first_body": body_ndiff(g_a, g_b),
                "second_body": body_ndiff(g_b, g_c),
                "first_bar": ui_bar63(g_a, g_b),
                "second_bar": ui_bar63(g_b, g_c),
                "change_hist_2": all_diff_hist(g_b, g_c),
                "player_0": p_a,
                "player_1": p_b,
                "player_2": p_c,
                "dx": dx,
                "dy": dy,
                "label": label,
                "meta_2": meta(d2),
            }
            per_action.append(row)
            print("DIFF", name, "bodies", row["first_body"], row["second_body"],
                  "Δ", (dx, dy), label)

        diffs = {
            "game_id": sess.game_id,
            "card_id": sess.card_id,
            "tags": TAGS,
            "available_actions": acts,
            "dir_map": dir_map,
            "note": (
                "1-step buffer: measure 2nd identical press after RESET. "
                "UI tick is y=63 bar, not (63,0). "
                "L1 clear evidence: tests/fixtures/g50t_l1_clear_attempt.json"
            ),
            "per_action": per_action,
            "l1_clear": {
                "status": "PASS",
                "levels": "0→1",
                "fixture": "tests/fixtures/g50t_l1_clear_attempt.json",
                "sketch": "R×5 to snake head, A5 latch, D shaft, R to ~(40,52)",
            },
        }
        DIFF_OUT.write_text(json.dumps(diffs, indent=2, default=str), encoding="utf-8")
        print("dir_map", dir_map)
        print("wrote", OUT)
        print("wrote", DIFF_OUT)
        print("docs already at", REPORT, HYPO)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
