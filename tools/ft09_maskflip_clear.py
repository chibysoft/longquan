"""ft09 clear via structure-induction library (goal decode + GF2 + transitions).

Climb L1–L4 with seated probes, then clear L5/L6 using
`longquan.interactive.maskflip` (no canned click tables).

Usage:
  python tools/ft09_maskflip_clear.py           # L5+L6 → WIN
  python tools/ft09_maskflip_clear.py --upto 5  # stop after L5
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive.maskflip.goal import (  # noqa: E402
    decode_l4_like_targets,
    effect_l5_solid_and_checker,
    effect_xor_north,
    find_instr_patches,
    plan_clicks_gf2,
)
from longquan.interactive.maskflip.grid import (  # noqa: E402
    BLOCK,
    as_plane,
    is_checker_block,
    is_pip_block,
    plus_arms,
)
from tools.ft09_click_flip_probe import Ft09Session  # noqa: E402
from tools.ft09_l3_click_flip_probe import color_hist  # noqa: E402
from tools.ft09_l5_click_flip_probe import climb_to_level  # noqa: E402
from tools.ls20_online_validate import _api_key  # noqa: E402

REPORT = ROOT / "docs" / "ft09-maskflip-clear-report.md"


def _plan_l5(g: np.ndarray) -> list[tuple[int, int]]:
    patches = find_instr_patches(g, palette=(14, 15))
    for p in patches:
        p["macro"] = {
            f"{r},{c}": p["macro"][(r, c)] for r in range(3) for c in range(3)
        }
    want = decode_l4_like_targets(patches, base_color=14, flip_to=15)
    checkers = [
        (ax, ay)
        for ay in range(0, g.shape[0] - BLOCK + 1, 2)
        for ax in range(0, g.shape[1] - BLOCK + 1, 2)
        if is_checker_block(g, ax, ay, 14, 15)
    ]
    affected = set(want)
    for c in checkers:
        affected.update(plus_arms(g, c[0], c[1]))
    solids = sorted(c for c in affected if c not in set(checkers))
    clickables = solids + checkers
    return plan_clicks_gf2(
        g,
        want,
        flip_to=15,
        clickables=clickables,
        effect_fn=effect_l5_solid_and_checker(g, checkers),
    )


def _plan_l6(g: np.ndarray) -> list[tuple[int, int]]:
    patches = find_instr_patches(g, palette=(11, 14))
    for p in patches:
        p["macro"] = {
            f"{r},{c}": p["macro"][(r, c)] for r in range(3) for c in range(3)
        }
    want_all = decode_l4_like_targets(patches, base_color=11, flip_to=14)
    tiles = [
        (ax, ay)
        for ay in range(0, g.shape[0] - BLOCK + 1, 2)
        for ax in range(0, g.shape[1] - BLOCK + 1, 2)
        if is_pip_block(g, ax, ay, 11, 14)
    ]
    want = {c: w for c, w in want_all.items() if c in set(tiles)}
    return plan_clicks_gf2(
        g,
        want,
        flip_to=14,
        clickables=tiles,
        effect_fn=effect_xor_north(g, 11, 14),
    )


def _exec_plan(sess: Ft09Session, frame, plan, lv_expect: int, label: str):
    cur = frame
    lv = lv_expect
    traj = []
    # Solids / unit clicks first, then operators that couple (stable for L5)
    for step, (ax, ay) in enumerate(plan, 1):
        resp = sess.click(ax + BLOCK // 2, ay + BLOCK // 2)
        cur = resp["frame"]
        lv = int(resp.get("levels_completed") or 0)
        state = resp.get("state")
        print(f"  {label} {step}/{len(plan)} ({ax},{ay}) lv={lv} state={state}")
        traj.append({"step": step, "block": [ax, ay], "levels": lv, "state": state})
        if lv > lv_expect:
            print(f"  >>> {label} LEVEL {lv_expect} -> {lv}")
            return cur, lv, True, traj, resp
    return cur, lv, False, traj, None


def clear_l5_lib(sess, frame, lv_expect=4):
    g = as_plane(frame)
    # Order: solids then checkers (same as seated probe)
    plan = _plan_l5(g)
    checkers = {
        (ax, ay)
        for ay in range(0, 59, 2)
        for ax in range(0, 59, 2)
        if is_checker_block(g, ax, ay, 14, 15)
    }
    solids = [c for c in plan if c not in checkers]
    chks = [c for c in plan if c in checkers]
    ordered = solids + chks
    print(f"L5 lib: plan={len(ordered)} solids={len(solids)} checkers={len(chks)} hist={color_hist(g)}")
    return _exec_plan(sess, frame, ordered, lv_expect, "L5")


def clear_l6_lib(sess, frame, lv_expect=5):
    g = as_plane(frame)
    plan = _plan_l6(g)
    print(f"L6 lib: plan={len(plan)} hist={color_hist(g)}")
    return _exec_plan(sess, frame, plan, lv_expect, "L6")


def write_report(meta: dict) -> Path:
    lines = [
        "# ft09 maskflip 库通关（结构归纳路径B）",
        "",
        "> 脚本：`tools/ft09_maskflip_clear.py`",
        "> 库：`longquan/interactive/maskflip/`",
        "",
        "## 结论",
        "",
    ]
    if meta.get("win"):
        lines.append(
            f"**PASS** — 库规划通关：`levels`→`{meta.get('levels_end')}`，"
            f"`state={meta.get('state')}`（win_levels=6）。"
        )
        lines.append("")
        lines.append("> verdict=`maskflip_lib_full_clear_win`")
    else:
        lines.append(
            f"**PARTIAL/FAIL** — levels_end=`{meta.get('levels_end')}` "
            f"state=`{meta.get('state')}`。"
        )
        lines.append("")
        lines.append("> verdict=`maskflip_lib_clear_incomplete`")
    lines += [
        "",
        "## 轨迹摘要",
        "",
        f"- L5 cleared: `{meta.get('l5_cleared')}` clicks=`{meta.get('l5_clicks')}`",
        f"- L6 cleared: `{meta.get('l6_cleared')}` clicks=`{meta.get('l6_clicks')}`",
        "",
        "## 方法",
        "",
        "1. 转移层：`flip_block` / `xor_plus` / `xor_north`（`induce_transition` 可从样例归纳）。",
        "2. 目标层：`decode_l4_like_targets` + `plan_clicks_gf2`。",
        "3. 通关判据仅 `levels_completed` / `state=WIN`。",
        "",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upto", type=int, default=6, help="stop after reaching this levels_completed")
    args = ap.parse_args()

    key = _api_key()
    if not key:
        raise RuntimeError("no ARC_API_KEY")
    sess = Ft09Session(key)
    meta = {
        "l5_cleared": False,
        "l6_cleared": False,
        "l5_clicks": 0,
        "l6_clicks": 0,
        "win": False,
        "levels_end": 0,
        "state": None,
    }
    try:
        sess.open(tags=["ft09_maskflip_lib"])
        frame, lv, _ = climb_to_level(sess, target_lv=4)
        frame, lv, ok, traj, last = clear_l5_lib(sess, frame, 4)
        meta["l5_cleared"] = ok
        meta["l5_clicks"] = len(traj)
        meta["levels_end"] = lv
        if not ok:
            write_report(meta)
            return 1
        if args.upto <= 5:
            write_report(meta)
            return 0
        synced = sess.action("ACTION1")
        frame = synced["frame"]
        frame, lv, ok, traj, last = clear_l6_lib(sess, frame, 5)
        meta["l6_cleared"] = ok
        meta["l6_clicks"] = len(traj)
        meta["levels_end"] = lv
        if last:
            meta["state"] = last.get("state")
            meta["win"] = last.get("state") == "WIN" or lv >= 6
        write_report(meta)
        print("report", REPORT)
        return 0 if meta["win"] else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
