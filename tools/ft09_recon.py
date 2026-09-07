"""ft09 recon probe: pull the initial frame + action space, pure observation.

WHY
  ft09 is the terminal acceptance target (6 levels, baseline [43,12,23,28,65,37]).
  Before committing to "keep pushing ls20 vs pivot to ft09", we need one cheap
  fact: what does ft09's board look like, what is its action space, and does it
  obviously fall outside the current primitive library (move / match / reflect)?

  This probe is PURE OBSERVATION: open a scorecard, GET the game descriptor,
  POST RESET, and dump the frame + available_actions. NO moves, no solving, no
  engine source. Red lines respected: frames only, no canned tables, no
  "looks right" as a pass criterion (we are not scoring — just describing).

USAGE
  python tools/ft09_recon.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, _api_key

FIXTURE = ROOT / "tests" / "fixtures" / "ft09_frame_initial.json"
REPORT = ROOT / "docs" / "ft09-recon-report.md"

GAME = "ft09"

COLCHAR = {
    0: "0", 1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
    8: "8", 9: "9", 10: "a", 11: "b", 12: "c", 13: "d", 14: "e", 15: "f",
}


def _headers(key, json_body=False):
    h = {"X-API-Key": key, "Accept": "application/json"}
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def main() -> int:
    key = _api_key()
    if not key:
        raise RuntimeError("ARC_API_KEY not found")
    s = requests.Session()

    # 1. open scorecard
    r = s.post(f"{BASE}/api/scorecard/open", headers=_headers(key, True),
               json={"tags": ["ft09_recon"]}, timeout=20)
    r.raise_for_status()
    card_id = r.json()["card_id"]

    # 2. game descriptor
    r = s.get(f"{BASE}/api/games/{GAME}", headers=_headers(key), timeout=20)
    r.raise_for_status()
    game_desc = r.json()
    game_id = game_desc["game_id"]

    # 3. RESET -> initial frame
    r = s.post(f"{BASE}/api/cmd/RESET", headers=_headers(key, True),
               json={"card_id": card_id, "game_id": game_id}, timeout=20)
    r.raise_for_status()
    reset = r.json()
    guid = reset.get("guid")

    # 4. close
    try:
        s.post(f"{BASE}/api/scorecard/close", headers=_headers(key, True),
               json={"card_id": card_id}, timeout=15)
    except Exception:
        pass

    # ---- analyze ----
    frame = reset.get("frame")
    arr = np.asarray(frame, dtype=np.int64)
    out = {
        "game_id": game_id,
        "card_id": card_id,
        "game_desc_keys": sorted(game_desc.keys()),
        "game_desc": {k: game_desc[k] for k in game_desc
                      if k not in ("frame",)},
        "reset_keys": sorted(reset.keys()),
        "state": reset.get("state"),
        "levels_completed": reset.get("levels_completed"),
        "win_levels": reset.get("win_levels"),
        "available_actions": reset.get("available_actions"),
        "frame_shape": list(arr.shape),
        "frame_dtype": str(arr.dtype),
    }

    print("=== ft09 game descriptor ===")
    for k, v in game_desc.items():
        print(f"  {k} = {v}")
    print("=== RESET response keys ===", sorted(reset.keys()))
    print("  state =", reset.get("state"))
    print("  levels_completed =", reset.get("levels_completed"))
    print("  win_levels =", reset.get("win_levels"))
    print("  available_actions =", reset.get("available_actions"))
    print("  frame shape =", arr.shape, "dtype =", arr.dtype)

    # color histogram (flatten layers)
    flat = arr.reshape(-1)
    hist = {}
    for v in np.unique(flat):
        hist[int(v)] = int((flat == v).sum())
    print("  color histogram (all layers):", hist)

    # render each layer if small enough
    if arr.ndim == 3:
        for i in range(arr.shape[0]):
            print(f"  --- layer {i} ---")
            render(arr[i])
    else:
        render(arr)

    # save frame + report
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps({"frame": arr.tolist(), **out}),
                       encoding="utf-8")
    _write_report(out, hist)
    print(f"\nsaved frame -> {FIXTURE}")
    print(f"report -> {REPORT}")
    return 0


def render(g):
    H, W = g.shape
    print(f"    shape {H}x{W}")
    if H > 64 or W > 64:
        print("    (too large to render full; showing histogram only)")
        return
    for y in range(H):
        row = "".join(COLCHAR.get(int(g[y, x]), "?") for x in range(W))
        print(f"    {y:02d} {row}")


def _write_report(out, hist):
    lines = [
        "# ft09 快速探路报告（纯观测）",
        "",
        "> 脚本：`tools/ft09_recon.py`",
        "> 性质：拉初始帧 + 动作空间，纯观测，不求解、不读引擎源码、不发多余动作",
        "",
        "---",
        "",
        "## 结论",
        "",
        f"- game_id = `{out['game_id']}`",
        f"- 帧 shape = `{out['frame_shape']}` dtype = `{out['frame_dtype']}`",
        f"- 颜色直方图 = `{hist}`",
        f"- state = `{out['state']}` · levels_completed = `{out['levels_completed']}`",
        f"  · win_levels = `{out['win_levels']}`",
        f"- available_actions = `{out['available_actions']}`",
        "",
        "---",
        "",
        "## 原始返回字段",
        "",
        f"- game_desc keys = `{out['game_desc_keys']}`",
        f"- reset keys = `{out['reset_keys']}`",
        "",
        "```json",
        json.dumps({k: out[k] for k in ("game_desc",) }, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 判读（待人工）",
        "",
        "- 动作空间是否仍是 ACTION1-4（方向）+ 可能的 INTERACT？",
        "- 颜色语义是否与 ls20（12=移动体、9=盖印、14=环、11=补给）同族？",
        "- 是否明显超出当前原语库（move / match / reflect）？",
        "",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
