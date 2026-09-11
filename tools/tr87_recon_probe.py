"""tr87 closed-book recon bootstrap: open game, RESET, dump L1 frame facts.

Independent scorecard tags=["tr87_recon"]. Do NOT share sessions with r11l/vc33.
No engine source. No canned trajectories.

Usage:
  python tools/tr87_recon_probe.py
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

GAME = "tr87"
TAGS = ["tr87_recon"]
OUT = ROOT / "tests/fixtures/tr87_l1_frame_live.json"
REPORT = ROOT / "docs/tr87-recon.md"
HYPO = ROOT / "docs/tr87-hypotheses.md"


def headers(key: str, json_body: bool = False) -> dict:
    h = {"X-API-Key": key, "Accept": "application/json"}
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def plane(frame) -> np.ndarray:
    a = np.asarray(frame, dtype=np.int64)
    return a[0] if a.ndim == 3 else a


def components(g: np.ndarray, color: int, min_n: int = 1, max_n: int = 10**9):
    H, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(H):
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
                        and 0 <= ny < H
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
                    "cx": sum(xs) / len(xs),
                    "cy": sum(ys) / len(ys),
                    "color": color,
                })
    out.sort(key=lambda b: (b["y0"], b["x0"]))
    return out


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


def summarize(g: np.ndarray, d: dict) -> dict:
    h = {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))}
    comps = {}
    for c in sorted(h):
        cs = components(g, c, 1, 10**6)
        comps[str(c)] = [
            {k: (round(v, 2) if isinstance(v, float) else v)
             for k, v in b.items()}
            for b in cs[:12]
        ]
        if len(cs) > 12:
            comps[str(c)].append({"_more": len(cs) - 12})
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


def write_docs(summary: dict, game_id: str, card_id: str):
    preview = "\n".join(summary.get("preview_lines", [])[:40])
    REPORT.write_text(
        f"""# tr87 探路（闭卷）

> 2026-09-10 · game_id=`{game_id}` · tags=`{TAGS}`

## 总览

| 关 | 状态 | 要点 |
|----|------|------|
| L1 | 探路中 | 首帧已抓；机制待坐实 |
| L2+ | — | — |

## L1 首帧事实

- `win_levels` = `{summary.get("win_levels")}`
- `levels_completed` = `{summary.get("levels_completed")}`
- `available_actions` = `{summary.get("available_actions")}`
- `state` = `{summary.get("state")}`
- shape = `{summary.get("shape")}`
- hist = `{summary.get("hist")}`
- n_comps = `{summary.get("n_comps")}`

### ASCII（非空行）

```
{preview}
```

### 连通块样本

见 `tests/fixtures/tr87_l1_frame_live.json`。

## 卡点 / 下一刀

枚举 `available_actions` 每步效应；识别可点目标 vs 装饰；建立 levels 递增判据。

## 红线

不读引擎；tags=`["tr87_recon"]`；只认 `levels_completed`；**勿抢 r11l / vc33 会话**。
""",
        encoding="utf-8",
    )
    HYPO.write_text(
        f"""# tr87 假设账本

> 2026-09-10 · tags=`{TAGS}` · card=`{card_id}`

| ID | 假设 | 预期观察 | 状态 | 证据 |
|----|------|----------|------|------|
| H1 | 主导原语是序列/匹配（非 translate） | 动作改变序列/高亮/对齐，非整图平移 | **OPEN** | verify-games 标注；待帧证 |
| H2 | `available_actions` 含点击或离散选择 | RESET 后 acts 非空且可复现 | **OPEN** | 首帧 acts={summary.get("available_actions")} |
| H3 | 通关只认 levels 严格递增 | levels 0→1 伴随可复现动作序列 | **OPEN** | — |

脚本：`tools/tr87_recon_probe.py`
""",
        encoding="utf-8",
    )


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        d = sess.reset()
        g = plane(d["frame"])
        summary = summarize(g, d)
        summary["preview_lines"] = ascii_preview(g)
        summary["game_id"] = sess.game_id
        summary["card_id"] = sess.card_id
        summary["tags"] = TAGS
        # also store raw frame for later
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
        OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        write_docs(summary, sess.game_id, sess.card_id)
        print("hist", summary["hist"])
        print("acts", summary["available_actions"], "lv", summary["levels_completed"],
              "win", summary["win_levels"], "state", summary["state"])
        print("n_comps", summary["n_comps"])
        print("wrote", OUT)
        print("wrote", REPORT)
        print("wrote", HYPO)
        for line in summary["preview_lines"][:30]:
            print(line)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
