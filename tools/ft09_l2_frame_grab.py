"""ft09 L2 frame grab + offline mask-flip generalization check.

Purpose (handoff 2026-09-07):
  After L1 locked mask-flip (0=flip-to-8, 2=keep-9), pull the L2 start frame
  cheaply and ask only: does the same 0/2 encoding + dual 3x3 layout still hold?

  NOT a clear attempt for L2. No canned click table. Clear L1 only by deriving
  flips from the L1 center 0/2 pattern (same as ft09_click_flip_probe).

  Critical: after levels_completed increments, the response frame is still the
  SOLVED L1 board (same as ls20). Send ACTION1 once to sync into the true L2
  start frame before analyzing.

Usage:
  python tools/ft09_l2_frame_grab.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ft09_click_flip_probe import (  # noqa: E402
    Ft09Session,
    _plane,
    block_center,
    read_instruction,
)
from tools.ls20_online_validate import _api_key  # noqa: E402

FIXTURE_L2 = ROOT / "tests" / "fixtures" / "ft09_l2_frame_live.json"
REPORT = ROOT / "docs" / "ft09-l2-mask-flip-check.md"


def color_hist(g: np.ndarray) -> dict:
    return {int(k): int(v) for k, v in Counter(g.flatten().tolist()).items()}


def ui_bar(g: np.ndarray) -> dict:
    row = g[63] if g.shape[0] > 63 else g[-1]
    return {
        "n12": int(np.sum(row == 12)),
        "n11": int(np.sum(row == 11)),
        "row_hist": color_hist(row),
    }


def decode_6x6_macro(patch: np.ndarray) -> dict:
    """Decode a 6x6 patch of 2x2 macro-cells into labels by majority color."""
    macro = {}
    for r in range(3):
        for c in range(3):
            cell = patch[2 * r:2 * r + 2, 2 * c:2 * c + 2]
            vals = sorted({int(v) for v in cell.flatten().tolist()})
            if vals == [0]:
                macro[(r, c)] = "0"
            elif vals == [2]:
                macro[(r, c)] = "2"
            elif vals == [8]:
                macro[(r, c)] = "8"
            elif vals == [12]:
                macro[(r, c)] = "12"
            else:
                macro[(r, c)] = f"mixed{vals}"
    return macro


def find_instr_patches(g: np.ndarray) -> list[dict]:
    """Find 6x6 windows whose colors are subset of {0,2,8,12} and contain 0+2."""
    H, W = g.shape
    out = []
    seen = set()
    for y in range(H - 5):
        for x in range(W - 5):
            p = g[y:y + 6, x:x + 6]
            vals = {int(v) for v in p.flatten().tolist()}
            if not vals <= {0, 2, 8, 12}:
                continue
            if 0 not in vals or 2 not in vals:
                continue
            # snap to even coords to avoid sliding duplicates
            key = (x - x % 2, y - y % 2)
            if key in seen:
                continue
            # prefer exact top-left of a solid 6x6 aligned patch
            if x % 2 or y % 2:
                continue
            seen.add(key)
            macro = decode_6x6_macro(p)
            out.append({
                "origin": [x, y],
                "hist": color_hist(p),
                "macro": {f"{r},{c}": macro[(r, c)] for r in range(3) for c in range(3)},
                "patch": p.tolist(),
            })
    out.sort(key=lambda t: (t["origin"][1], t["origin"][0]))
    return out


def block_grid_summary(g: np.ndarray, ox: int, oy: int, rows: int, cols: int) -> list:
    """Majority color per 6x6 block on an 8-stride grid."""
    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            p = g[oy + 8 * r:oy + 8 * r + 6, ox + 8 * c:ox + 8 * c + 6]
            if p.shape != (6, 6):
                row.append(None)
                continue
            vals, cnts = np.unique(p, return_counts=True)
            row.append(int(vals[np.argmax(cnts)]))
        grid.append(row)
    return grid


def clear_l1(sess: Ft09Session) -> dict:
    reset = sess.reset()
    frame = reset["frame"]
    lv0 = int(reset.get("levels_completed") or 0)
    actions = reset.get("available_actions")
    instr = read_instruction(frame)
    clicks = [(r, c) for r in range(3) for c in range(3)
              if (r, c) != (1, 1) and instr.get((r, c)) == "flip"]
    print(f"L1 start lv={lv0} actions={actions} flips={clicks}")
    last = reset
    for (r, c) in clicks:
        cx, cy = block_center(r, c)
        resp = sess.click(cx, cy)
        last = resp
        frame = resp["frame"]
        lv = int(resp.get("levels_completed") or 0)
        print(f"  click ({r},{c})@({cx},{cy}) -> lv={lv}")
        if lv > lv0:
            return {
                "frame_stale": frame,
                "meta_stale": {k: resp.get(k) for k in (
                    "levels_completed", "state", "available_actions", "win_levels",
                )},
                "l1_clicks": clicks,
                "l1_instruction": {f"{a},{b}": v for (a, b), v in instr.items()},
            }
    raise RuntimeError("L1 clear failed — mask-flip derivation did not level-up")


def analyze_l2(frame) -> dict:
    g = _plane(frame)
    instrs = find_instr_patches(g)
    # L2 observed layout: 5x3 of 6x6 blocks starting ~ (20,14)
    grid_5x3 = block_grid_summary(g, 20, 14, 5, 3)
    # L1-style coords still readable?
    l1_center = None
    try:
        l1_center = {f"{r},{c}": v for (r, c), v in read_instruction(frame).items()}
    except Exception as e:
        l1_center = {"error": str(e)}
    return {
        "shape": list(g.shape),
        "hist": color_hist(g),
        "ui_bar": ui_bar(g),
        "n0": int(np.sum(g == 0)),
        "n2": int(np.sum(g == 2)),
        "n8": int(np.sum(g == 8)),
        "n9": int(np.sum(g == 9)),
        "n12": int(np.sum(g == 12)),
        "instr_patches": instrs,
        "block_grid_5x3_at_20_14": grid_5x3,
        "l1_center_instr_at_44_44": l1_center,
        "uses_color8_in_instr": any(8 in p["hist"] for p in instrs),
        "uses_color12_in_instr": any(12 in p["hist"] for p in instrs),
    }


def write_report(l2: dict, meta: dict, sync_diff: int) -> Path:
    same_action = meta.get("available_actions") == [6]
    has_02 = l2["n0"] > 0 and l2["n2"] > 0
    layout_l1_dual = False  # L2 is not the L1 dual-3x3 at (36,36)
    encoding_l1 = (
        has_02
        and not l2["uses_color12_in_instr"]
        and l2["uses_color8_in_instr"]
    )
    # True L2: 0/2 still present, but fixed-token is 12 not 8; layout is 5x3
    if same_action and has_02 and l2["uses_color12_in_instr"] and not encoding_l1:
        verdict = "layout_encoding_migrated"
        headline = (
            "**FAIL（L1 mask-flip 不能直接锁死）** — 过关后需 ACTION1 sync 才拿到真 L2。"
            "L2 仍是 ACTION6 + 含 0/2 的压缩图案，但："
            "（1）布局从双 3×3 变为约 `(20,14)` 起的 **5×3** 块阵；"
            "（2）图案中心“固定格”从 color**8** 换成 color**12**；"
            "（3）开局无 color8 已翻转块。同族机制，**非** L1 坐标/字母表的 drop-in。"
        )
    elif same_action and encoding_l1 and layout_l1_dual:
        verdict = "structure_pass"
        headline = (
            "**PASS（结构一致）** — L2 与 L1 同布局同 0/2/8 字母表；"
            "mask-flip 可固化（仍未做 L2 点击通关）。"
        )
    else:
        verdict = "inconclusive"
        headline = "**INCONCLUSIVE** — 见下文摘要，需人工核对 fixture。"

    lines = [
        "# ft09 L2 mask-flip 泛化检查",
        "",
        "> 脚本：`tools/ft09_l2_frame_grab.py`",
        f"> levels_completed = `{meta.get('levels_completed')}`（L1 已过，真 L2 帧）",
        f"> available_actions = `{meta.get('available_actions')}`",
        f"> ACTION1 sync pixel-diff from stale post-clear = `{sync_diff}`",
        "",
        "## 结论",
        "",
        headline,
        "",
        f"> verdict=`{verdict}`",
        "",
        "## 操作发现",
        "",
        "- L1 通关当帧仍是**已解 L1**（中部 9→8 残留，0/2 图案未换）。",
        "- 必须再发一次 **ACTION1**（即使 available_actions 仍只列 `[6]`）才切入真 L2。",
        "- 与 ls20「过关陋帧 + sync ACTION1」同型。",
        "",
        "## L2 帧摘要",
        "",
        f"- hist: `{l2['hist']}`",
        f"- n0/n2/n8/n9/n12 = {l2['n0']}/{l2['n2']}/{l2['n8']}/{l2['n9']}/{l2['n12']}",
        f"- UI bar: `{l2['ui_bar']}`",
        f"- 5×3 block majority @ (20,14): `{l2['block_grid_5x3_at_20_14']}`",
        f"- instr patches: {len(l2['instr_patches'])}",
        "",
    ]
    for i, p in enumerate(l2["instr_patches"]):
        lines.append(
            f"- instr[{i}] origin=`{p['origin']}` hist=`{p['hist']}` macro=`{p['macro']}`"
        )
    lines += [
        "",
        "## 与 L1 对照",
        "",
        "| 项 | L1 | L2（真帧） |",
        "|----|----|------------|",
        "| 动作 | ACTION6 | ACTION6 |",
        "| 背景主色 | 5 | 4 |",
        "| 布局 | 左示例 3×3 + 中谜题 3×3 @ (36,36) | 5×3 块阵 @ ~(20,14)，两枚 0/2 图案在中列 |",
        "| 图案字母 | 0 / 2 / **8** | 0 / 2 / **12** |",
        "| 开局 color8 | 有（已翻示例） | **0** |",
        "| 底栏 UI | color12 | color12（含少量 11） |",
        "",
        "## 对 mask-flip 的裁决",
        "",
        "- **不能**把 L1 的「读 (44,44) 的 0/2/8 → 点中部 3×3」直接固化为全 ft09 solver。",
        "- **可以**保留工作假说：仍是「图案 mask + 点击重着色」，但坐标、字母表、网格尺寸需按关重解析。",
        "- 下一步（若继续）：在真 L2 上用帧内图案推导点击做**一次**闭环，验证 0→翻 / 2→留 是否仍成立（本报告未做）。",
        "",
        "## 产物",
        "",
        f"- fixture: `{FIXTURE_L2.as_posix()}`",
        "",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT


def main() -> int:
    key = _api_key()
    if not key:
        raise RuntimeError("no ARC_API_KEY")
    sess = Ft09Session(key)
    try:
        sess.open(tags=["ft09_l2_grab"])
        cleared = clear_l1(sess)
        stale = _plane(cleared["frame_stale"])
        print(
            "after L1 clear (STALE): lv=",
            cleared["meta_stale"].get("levels_completed"),
            "actions=", cleared["meta_stale"].get("available_actions"),
        )

        synced = sess.action("ACTION1")
        frame = synced["frame"]
        meta = {k: synced.get(k) for k in (
            "levels_completed", "state", "available_actions", "win_levels",
        )}
        g = _plane(frame)
        sync_diff = int(np.sum(g != stale))
        print(
            f"after ACTION1 sync: lv={meta.get('levels_completed')} "
            f"actions={meta.get('available_actions')} diff={sync_diff} "
            f"n0={int(np.sum(g == 0))} n2={int(np.sum(g == 2))} n8={int(np.sum(g == 8))}"
        )

        l2 = analyze_l2(frame)
        print(
            "instr patches", len(l2["instr_patches"]),
            "grid", l2["block_grid_5x3_at_20_14"],
            "ui", l2["ui_bar"],
        )

        FIXTURE_L2.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE_L2.write_text(json.dumps({
            "game_id": sess.game_id,
            "meta": meta,
            "sync": {"action": "ACTION1", "pixel_diff_from_stale": sync_diff},
            "l1_instruction": cleared["l1_instruction"],
            "l1_clicks": cleared["l1_clicks"],
            "frame": g.tolist(),
            "analysis": l2,
        }, indent=2), encoding="utf-8")
        print("saved", FIXTURE_L2)

        path = write_report(l2, meta, sync_diff)
        print("report", path)

        # exit 0 = grab succeeded; verdict may still be migrated
        ok = (
            meta.get("available_actions") == [6]
            and sync_diff > 200
            and l2["n0"] > 0 and l2["n2"] > 0
        )
        return 0 if ok else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
