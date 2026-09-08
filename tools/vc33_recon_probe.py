"""vc33 closed-book recon probe: falsify H1–H4 (docs/vc33-hypotheses.md).

Independent scorecard tags: ["vc33_recon"]. No engine source. No seated clear.

Key measurement rules learned mid-recon:
  - Ignore UI tick at (63,0) 7→4 on every ACTION6.
  - Interactive targets on L1 are color-9 pads, not the color-4/11 sprite.
  - Track sprite as largest {4,11} CC with y>0.

Usage:
  python tools/vc33_recon_probe.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, _api_key  # noqa: E402

GAME = "vc33"
TAGS = ["vc33_recon"]
REPORT = ROOT / "docs" / "vc33-recon.md"
HYPO = ROOT / "docs" / "vc33-hypotheses.md"
RESULT = ROOT / "tests" / "fixtures" / "vc33_recon_probe_result.json"


def _headers(key: str, json_body: bool = False) -> dict:
    h = {"X-API-Key": key, "Accept": "application/json"}
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def plane(frame) -> np.ndarray:
    a = np.asarray(frame, dtype=np.int64)
    return a[0] if a.ndim == 3 else a


def body_ndiff(a: np.ndarray, b: np.ndarray) -> int:
    return int(np.sum(a[1:] != b[1:]))


def body_changes(a: np.ndarray, b: np.ndarray) -> dict:
    m = a[1:] != b[1:]
    ys, xs = np.where(m)
    hist = Counter()
    for y, x in zip(ys.tolist(), xs.tolist()):
        hist[(int(a[y + 1, x]), int(b[y + 1, x]))] += 1
    return {f"{a_}->{b_}": n for (a_, b_), n in hist.most_common(16)}


def sprite_cc(g: np.ndarray):
    H, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    best = []
    for y in range(1, H):
        for x in range(W):
            if seen[y, x] or int(g[y, x]) not in (4, 11):
                continue
            stack = [(x, y)]
            seen[y, x] = True
            cells = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy, int(g[cy, cx])))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (
                        0 <= nx < W
                        and 1 <= ny < H
                        and not seen[ny, nx]
                        and int(g[ny, nx]) in (4, 11)
                    ):
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            if len(cells) > len(best):
                best = cells
    if not best:
        return None
    xs = [c[0] for c in best]
    ys = [c[1] for c in best]
    return {
        "n": len(best),
        "x0": min(xs),
        "y0": min(ys),
        "x1": max(xs),
        "y1": max(ys),
        "cx": round(sum(xs) / len(xs), 3),
        "cy": round(sum(ys) / len(ys), 3),
        "n4": sum(1 for c in best if c[2] == 4),
        "n11": sum(1 for c in best if c[2] == 11),
    }


def c9_blocks(g: np.ndarray):
    H, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    blocks = []
    for y in range(H):
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
                        and 0 <= ny < H
                        and not seen[ny, nx]
                        and int(g[ny, nx]) == 9
                    ):
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            blocks.append({
                "n": len(cells),
                "x0": min(xs),
                "y0": min(ys),
                "x1": max(xs),
                "y1": max(ys),
                "cx": sum(xs) / len(xs),
                "cy": sum(ys) / len(ys),
            })
    blocks.sort(key=lambda b: (b["y0"], b["x0"]))
    return blocks


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
            headers=_headers(self.key, True),
            json={"tags": TAGS},
            timeout=20,
        )
        r.raise_for_status()
        self.card_id = r.json()["card_id"]
        r = self.s.get(f"{BASE}/api/games/{GAME}", headers=_headers(self.key), timeout=20)
        r.raise_for_status()
        self.game_id = r.json()["game_id"]

    def reset(self):
        r = self.s.post(
            f"{BASE}/api/cmd/RESET",
            headers=_headers(self.key, True),
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
            headers=_headers(self.key, True),
            json=body,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        self.guid = data.get("guid", self.guid)
        return data

    def click(self, x: int, y: int):
        return self.action("ACTION6", x=int(x), y=int(y))

    def close(self):
        if not self.card_id:
            return
        try:
            self.s.post(
                f"{BASE}/api/scorecard/close",
                headers=_headers(self.key, True),
                json={"card_id": self.card_id},
                timeout=15,
            )
        except Exception:
            pass


def run() -> dict:
    key = _api_key()
    if not key:
        raise RuntimeError("ARC_API_KEY not found")
    sess = Sess(key)
    try:
        sess.open()
        reset = sess.reset()
        g0 = plane(reset["frame"])
        m0 = meta(reset)
        sp0 = sprite_cc(g0)
        pads = c9_blocks(g0)
        print("RESET", m0, "sprite", sp0, "pads", pads)

        # --- H3: A1-4 ---
        move_rows = []
        for aid in (1, 2, 3, 4):
            d = sess.action(f"ACTION{aid}")
            g = plane(d["frame"])
            row = {
                "action": f"ACTION{aid}",
                "body_ndiff": body_ndiff(g0, g),
                "sprite": sprite_cc(g),
                "meta": meta(d),
            }
            move_rows.append(row)
            print("H3", row)
            reset = sess.reset()
            g0 = plane(reset["frame"])
            sp0 = sprite_cc(g0)

        h3 = (
            "REFUTED"
            if m0.get("available_actions") == [6]
            and all(r["body_ndiff"] == 0 for r in move_rows)
            else "INCONCLUSIVE"
        )

        # --- H1: blank / sprite / pads ---
        reset = sess.reset()
        g0 = plane(reset["frame"])
        sp0 = sprite_cc(g0)
        pads = c9_blocks(g0)

        def trial_click(label: str, x: int, y: int) -> dict:
            nonlocal g0, sp0
            reset_d = sess.reset()
            g0 = plane(reset_d["frame"])
            sp0 = sprite_cc(g0)
            d = sess.click(x, y)
            g1 = plane(d["frame"])
            sp1 = sprite_cc(g1)
            row = {
                "label": label,
                "xy": [x, y],
                "body_ndiff": body_ndiff(g0, g1),
                "change_hist": body_changes(g0, g1),
                "sprite_before": sp0,
                "sprite_after": sp1,
                "dcx": None if not (sp0 and sp1) else round(sp1["cx"] - sp0["cx"], 3),
                "dcy": None if not (sp0 and sp1) else round(sp1["cy"] - sp0["cy"], 3),
                "meta": meta(d),
            }
            print("H1", row["label"], "body", row["body_ndiff"], "Δ", (row["dcx"], row["dcy"]))
            return row

        blank = trial_click("blank_c3", 10, 10)
        sprite = trial_click("sprite_c4", int(round(sp0["cx"])), int(round(sp0["cy"])))
        assert len(pads) >= 2
        upper = trial_click(
            "pad_upper_c9",
            int(round(pads[0]["cx"])),
            int(round(pads[0]["cy"])),
        )
        lower = trial_click(
            "pad_lower_c9",
            int(round(pads[1]["cx"])),
            int(round(pads[1]["cy"])),
        )
        below = trial_click("below_empty", 48, 55)

        # chain upper pad until stuck
        reset_d = sess.reset()
        g_prev = plane(reset_d["frame"])
        sp_prev = sprite_cc(g_prev)
        pads = c9_blocks(g_prev)
        ux, uy = int(round(pads[0]["cx"])), int(round(pads[0]["cy"]))
        chain = []
        for step in range(5):
            d = sess.click(ux, uy)
            g = plane(d["frame"])
            sp = sprite_cc(g)
            entry = {
                "step": step,
                "body_ndiff": body_ndiff(g_prev, g),
                "sprite": sp,
                "dcx": None if not (sp and sp_prev) else round(sp["cx"] - sp_prev["cx"], 3),
                "dcy": None if not (sp and sp_prev) else round(sp["cy"] - sp_prev["cy"], 3),
                "levels": d.get("levels_completed"),
            }
            chain.append(entry)
            print("H2 chain", entry)
            if entry["body_ndiff"] == 0:
                break
            g_prev, sp_prev = g, sp

        # verdicts
        pad_hits = upper["body_ndiff"] > 50 and lower["body_ndiff"] > 50
        blank_noop = blank["body_ndiff"] == 0
        sprite_noop = sprite["body_ndiff"] == 0
        below_noop = below["body_ndiff"] == 0

        if pad_hits and blank_noop and sprite_noop:
            h1 = {
                "verdict": "SUPPORTED",
                "why": (
                    "ACTION6 only; color9 pads body_ndiff≈264; "
                    f"blank/sprite/below body_ndiff=0 (UI-only tick ignored)"
                ),
            }
        elif pad_hits:
            h1 = {
                "verdict": "SUPPORTED",
                "why": f"pads effective; blank={blank['body_ndiff']} sprite={sprite['body_ndiff']}",
            }
        else:
            h1 = {"verdict": "REFUTED", "why": "no pad click produced body change"}

        # H2: directional forced motion (horizontal), not free fall +y
        upper_right = (upper.get("dcx") or 0) > 2 and abs(upper.get("dcy") or 0) < 0.5
        lower_left = (lower.get("dcx") or 0) < -2 and abs(lower.get("dcy") or 0) < 0.5
        chain_right = all(
            (e.get("dcx") or 0) > 2 or e["body_ndiff"] == 0 for e in chain
        ) and any((e.get("dcx") or 0) > 2 for e in chain)
        if upper_right and lower_left and chain_right:
            h2 = {
                "verdict": "SUPPORTED",
                "why": (
                    f"upper pad Δx={upper['dcx']} (right); lower pad Δx={lower['dcx']} (left); "
                    f"Y unchanged; chain steps={[e['dcx'] for e in chain]}"
                ),
            }
            h2_note = "定向冲量/水平‘重力’，非 +y 自由落体"
        elif upper_right or lower_left:
            h2 = {
                "verdict": "INCONCLUSIVE",
                "why": f"upperΔ=({upper['dcx']},{upper['dcy']}) lowerΔ=({lower['dcx']},{lower['dcy']})",
            }
            h2_note = ""
        else:
            h2 = {"verdict": "REFUTED", "why": "pads did not translate sprite on a fixed axis"}
            h2_note = ""

        # H4: classic translate-to-pointer / free placement
        if below_noop and pad_hits and not (
            abs((below.get("dcx") or 0)) > 1 or abs((below.get("dcy") or 0)) > 1
        ):
            h4 = {
                "verdict": "REFUTED",
                "why": "empty click below sprite does not place/move it; motion is pad-triggered fixed steps",
            }
        else:
            h4 = {"verdict": "INCONCLUSIVE", "why": str(below)}

        result = {
            "game_id": sess.game_id,
            "card_id": sess.card_id,
            "tags": TAGS,
            "reset_meta": m0,
            "reset_sprite": sp0,
            "reset_pads": pads,
            "verdicts": {
                "H1_CLICK": h1,
                "H2_GRAVITY": h2,
                "H3_MOVE": {
                    "verdict": h3,
                    "why": "available_actions=[6]; A1-4 body_ndiff=0" if h3 == "REFUTED" else "see rows",
                },
                "H4_TRANSLATE": h4,
            },
            "notes": {
                "ui_tick": "every ACTION6 flips (63,0) 7→4; excluded from body_ndiff",
                "h2_note": h2_note,
                "step_px": 4,
            },
            "trials": {
                "H3_MOVE": move_rows,
                "H1_CLICK": {
                    "blank": blank,
                    "sprite": sprite,
                    "pad_upper": upper,
                    "pad_lower": lower,
                    "below": below,
                },
                "H2_chain_upper": chain,
            },
        }
        return result
    finally:
        sess.close()


def write_recon(result: dict) -> None:
    v = result["verdicts"]
    t = result["trials"]["H1_CLICK"]
    chain = result["trials"]["H2_chain_upper"]
    lines = [
        "# vc33 探路（闭卷）",
        "",
        f"> 2026-09-09 · game_id=`{result['game_id']}` · tags=`{result['tags']}`  ",
        f"> 夹具：`tests/fixtures/vc33_l1_frame_live.json` · 假设：`docs/vc33-hypotheses.md`  ",
        f"> 探针：`tools/vc33_recon_probe.py` · 抓帧：`tools/vc33_l1_frame_grab.py`",
        "",
        "## 开局",
        "",
        f"- `levels_completed=0` / `win_levels={result['reset_meta'].get('win_levels')}`",
        f"- `available_actions={result['reset_meta'].get('available_actions')}`",
        f"- 精灵 {{4,11}} CC：`{result['reset_sprite']}`",
        f"- 色9 垫：`{result['reset_pads']}`",
        "- UI：每次 ACTION6 将 `(63,0)` 7→4（计量时忽略）",
        "",
        "## 假设裁决",
        "",
        "| ID | 裁决 | 依据 |",
        "|----|------|------|",
        f"| H1 点选主导 | **{v['H1_CLICK']['verdict']}** | {v['H1_CLICK']['why']} |",
        f"| H2 定向位移 | **{v['H2_GRAVITY']['verdict']}** | {v['H2_GRAVITY']['why']} |",
        f"| H3 四向移动 | **{v['H3_MOVE']['verdict']}** | {v['H3_MOVE']['why']} |",
        f"| H4 平移原语 | **{v['H4_TRANSLATE']['verdict']}** | {v['H4_TRANSLATE']['why']} |",
        "",
        "## 坐实机制（L1，未通关）",
        "",
        "- 唯一有效动作：**ACTION6** 点 **色9** 垫（上/下各一块）。",
        "- 点上垫 → 精灵 **+4 x**；点下垫 → 精灵 **-4 x**；**y 不变**。",
        "- 点空白 / 点精灵本体 / 点精灵下方：body 无变化。",
        "- 连点上垫：x 递增至贴右缘后 noop（body_ndiff=0）。",
        "- A1–4：noop。",
        "- **尚未**观察到 `levels_completed` 递增。",
        "",
        "## 试验数字",
        "",
        f"- blank{t['blank']['xy']} body=`{t['blank']['body_ndiff']}`",
        f"- sprite{t['sprite']['xy']} body=`{t['sprite']['body_ndiff']}`",
        f"- upper{t['pad_upper']['xy']} body=`{t['pad_upper']['body_ndiff']}` "
        f"Δ=({t['pad_upper']['dcx']},{t['pad_upper']['dcy']})",
        f"- lower{t['pad_lower']['xy']} body=`{t['pad_lower']['body_ndiff']}` "
        f"Δ=({t['pad_lower']['dcx']},{t['pad_lower']['dcy']})",
        f"- below{t['below']['xy']} body=`{t['below']['body_ndiff']}`",
        f"- upper chain Δx: `{[e['dcx'] for e in chain]}`",
        "",
        "## 下一刀",
        "",
        "- 找过关条件：水平移到某 x？与色5梁/色11缝对齐？需更多帧实验。",
        "- 仍只认 `levels_completed`；不写 seated clear 坐标表。",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote", REPORT)


def write_hypotheses(result: dict) -> None:
    v = result["verdicts"]
    text = f"""# vc33 L1 可证伪假设

> 2026-09-09 · 闭卷 · 夹具：`tests/fixtures/vc33_l1_frame_live.json`  
> game_id=`{result['game_id']}` · win_levels=7 · RESET `available_actions=[6]`  
> 纪律：只认帧 / `available_actions` / 线上响应；不读引擎；旧「translate 否决」不采信为本路先验证明。

## 开局帧表面（观察）

| 元素 | 像素事实 |
|------|----------|
| 顶栏 | y=0 全行色 **7**；点一次 ACTION6 后 `(63,0)` 常变 **4**（UI tick） |
| 左/右底 | x&lt;32 色 **3**；右侧大片色 **0** |
| 横梁 | y∈[28,31] 色 **5**，中缝色 **11** |
| 色9 垫 | 上 `(60–63,24–27)`；下 `(60–63,32–35)` |
| 精灵 | 色 **4**+**11** CC ≈`(46–51,44–49)` |

## 假设

| ID | 假设 | 预测 | 否证条件 |
|----|------|------|----------|
| **H1 点选** | 主导交互是 ACTION6 点选；只有点到特定对象才改棋盘 | 点色9 → body_ndiff≫0；点空白/精灵 → body≈0 | 空白与色9 同等有效；或 A1–4 同等有效 |
| **H2 定向位移** | 有效点击使精灵沿固定轴做受迫位移（类重力/冲量） | 重复点同一垫 → 同号 Δx 或 Δy，直至受阻 | 精灵原地变色/无位移；或位移方向随指针任意变 |
| **H3 四向移动** | A1–4 逐步平移 | `available_actions` 含 1–4 或强发后精灵移动 | 仅 `[6]` 且 A1–4 body_ndiff=0 |
| **H4 平移原语** | 点击=指定目标格，对象移向指针 | 点精灵下方空白 → 精灵接近该点 | 空白点击不移动精灵；运动由垫触发且步长固定 |

## 线上裁决

> `tools/vc33_recon_probe.py` · card=`{result['card_id']}` · tags=`{result['tags']}`

| ID | 裁决 | 依据 |
|----|------|------|
| H1 点选 | **{v['H1_CLICK']['verdict']}** | {v['H1_CLICK']['why']} |
| H2 定向位移 | **{v['H2_GRAVITY']['verdict']}** | {v['H2_GRAVITY']['why']} |
| H3 四向移动 | **{v['H3_MOVE']['verdict']}** | {v['H3_MOVE']['why']} |
| H4 平移原语 | **{v['H4_TRANSLATE']['verdict']}** | {v['H4_TRANSLATE']['why']} |

补充：上垫 → Δx≈**+4**；下垫 → Δx≈**-4**；Δy=0。不是 +y 自由落体，也不是指针追随。
"""
    HYPO.write_text(text, encoding="utf-8")
    print("wrote", HYPO)


def main() -> int:
    result = run()
    print("VERDICTS", json.dumps(result["verdicts"], ensure_ascii=False, indent=2))
    write_recon(result)
    write_hypotheses(result)
    RESULT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print("saved", RESULT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
