"""ft09 L2 click-flip closed-loop probe.

WHY
  L2 frame grab showed layout/alphabet migration (5x3 @ (20,14), fixed token
  color12 not 8). This probe asks only: does 0=flip / 2=keep still hold on the
  true L2 board when clicks are DERIVED from in-frame 0/2 patterns?

  Hypotheses under test (falsifiable):
    H1: Two stacked 3x3 puzzles share the 5x3 grid; each has a center 0/2/12
        instruction (upper @ (28,22), lower @ (28,38)).
    H2: Same mask-flip semantics as L1: 0 -> flip the corresponding 6x6 block,
        2 -> keep, 12 -> fixed center (L1's 8 role).
    H3: Pass = levels_completed 1 -> 2 only (not pixel beauty).

  No canned click table. Clear L1 via L1 instruction, ACTION1 sync, then derive
  L2 clicks from L2 patches.

Usage:
  python tools/ft09_l2_click_flip_probe.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ft09_click_flip_probe import (  # noqa: E402
    Ft09Session,
    _plane,
    block_center,
    frame_diff,
    read_instruction,
)
from tools.ls20_online_validate import _api_key  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "ft09_l2_click_flip_trajectory.json"
REPORT = ROOT / "docs" / "ft09-l2-click-flip-probe.md"

L2_OX, L2_OY = 20, 14
BLOCK, GAP = 6, 8

PUZZLES = (
    {"name": "upper", "ox": L2_OX, "oy": L2_OY, "instr": (28, 22)},
    {"name": "lower", "ox": L2_OX, "oy": L2_OY + 2 * GAP, "instr": (28, 38)},
)


def l2_block_center(puzzle_ox: int, puzzle_oy: int, r: int, c: int):
    x0 = puzzle_ox + GAP * c
    y0 = puzzle_oy + GAP * r
    return x0 + BLOCK // 2, y0 + BLOCK // 2


def read_instr_at(frame, ix: int, iy: int) -> dict:
    """Decode 6x6 at (ix,iy): 0=flip, 2=keep, 12|8=fixed."""
    g = _plane(frame)
    macro = {}
    for r in range(3):
        for c in range(3):
            cell = g[iy + 2 * r:iy + 2 * r + 2, ix + 2 * c:ix + 2 * c + 2]
            if np.all(cell == 12) or np.all(cell == 8):
                macro[(r, c)] = "fixed"
            elif np.all(cell == 0):
                macro[(r, c)] = "flip"
            elif np.all(cell == 2):
                macro[(r, c)] = "keep"
            else:
                vals = sorted({int(v) for v in cell.flatten().tolist()})
                macro[(r, c)] = f"mixed{vals}"
    return macro


def print_macro(instr: dict, label: str) -> None:
    print(f"{label}:")
    for r in range(3):
        print("  " + " ".join(f"{instr[(r, c)]:>5}" for c in range(3)))


def clear_l1(sess: Ft09Session) -> dict:
    reset = sess.reset()
    frame = reset["frame"]
    lv0 = int(reset.get("levels_completed") or 0)
    instr = read_instruction(frame)
    clicks = [
        (r, c) for r in range(3) for c in range(3)
        if (r, c) != (1, 1) and instr.get((r, c)) == "flip"
    ]
    print(f"L1 clear flips={clicks}")
    for r, c in clicks:
        resp = sess.click(*block_center(r, c))
        frame = resp["frame"]
        lv = int(resp.get("levels_completed") or 0)
        print(f"  L1 click ({r},{c}) -> lv={lv}")
        if lv > lv0:
            return {"frame_stale": frame, "lv": lv}
    raise RuntimeError("L1 clear failed")


def summarize_diff(d):
    from collections import Counter
    pairs = Counter((a, b) for _, _, a, b in d)
    return {f"{a}->{b}": n for (a, b), n in pairs.most_common(8)}


def write_report(payload: dict) -> Path:
    lv_start = payload["l2_levels_start"]
    lv_end = payload["l2_levels_end"]
    cleared = lv_end > lv_start
    lines = [
        "# ft09 L2 点击闭环探针",
        "",
        "> 脚本：`tools/ft09_l2_click_flip_probe.py`",
        f"> 轨迹：`{FIXTURE.as_posix()}`",
        f"> 判据：`levels_completed` `{lv_start}` → `{lv_end}`",
        "",
        "## 结论",
        "",
    ]
    if cleared:
        lines.append(
            "**PASS** — 按帧内 0/2/12 图案推导点击（双层 3×3 取并集、共享格只点一次），"
            f"`levels_completed` {lv_start}→{lv_end}。"
            "L2：**0=翻、2=留**；翻转色为 **9→12**（L1 为 9→8）；固定格 color12。"
        )
        verdict = "l2_mask_flip_pass"
    else:
        lines.append(
            "**FAIL / 未过关** — 双 3×3 并集点击后 "
            f"levels 仍为 {lv_end}。已确认单块点击为 9→12 可逆；见轨迹。"
        )
        verdict = "l2_mask_flip_fail"

    lines += [
        "",
        f"> verdict=`{verdict}`",
        "",
        "## 假设",
        "",
        "- H1：`(20,14)` 起 5×3 块阵内，上下各一枚 3×3（中心为 0/2/12 图案）",
        "- H2：0=flip、2=keep、12=fixed；翻转落地色为 **9→12**（非 L1 的 9→8）",
        "- H3：两图案目标在共享行一致 → 对绝对块坐标取 **并集** 各点一次",
        "- H4：通关只看 levels 递增",
        "",
        "## 推导出的点击",
        "",
    ]
    for puz in payload["puzzles"]:
        lines.append(
            f"- **{puz['name']}** instr@{puz['instr']} macro=`{puz['macro']}` "
            f"flips=`{puz['flips']}`"
        )
    lines += ["", "## 轨迹摘要", ""]
    for step in payload["trajectory"]:
        lines.append(
            f"- step {step['step']} {step['puzzle']} block{step['block']} "
            f"@ {step['pixel']} lv={step['levels_completed']} "
            f"diff={step['diff_summary']}"
        )
    lines += ["", "## 产物", "", f"- `{FIXTURE.as_posix()}`", ""]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT


def main() -> int:
    key = _api_key()
    if not key:
        raise RuntimeError("no ARC_API_KEY")
    sess = Ft09Session(key)
    trajectory = []
    try:
        sess.open(tags=["ft09_l2_click"])
        cleared = clear_l1(sess)
        synced = sess.action("ACTION1")
        frame = synced["frame"]
        lv0 = int(synced.get("levels_completed") or 0)
        print(f"L2 start lv={lv0} actions={synced.get('available_actions')}")

        puzzles_info = []
        # Absolute block keys (ax, ay) top-left of 6x6 — union so shared
        # middle row of the 5x3 is not toggled twice (second click undoes 12→9).
        abs_flips: dict[tuple[int, int], tuple] = {}
        for puz in PUZZLES:
            ix, iy = puz["instr"]
            instr = read_instr_at(frame, ix, iy)
            print_macro(instr, f"{puz['name']} instr@{puz['instr']}")
            flips = [
                (r, c) for r in range(3) for c in range(3)
                if (r, c) != (1, 1) and instr.get((r, c)) == "flip"
            ]
            print(f"  derived flips: {flips}")
            puzzles_info.append({
                "name": puz["name"],
                "ox": puz["ox"],
                "oy": puz["oy"],
                "instr": list(puz["instr"]),
                "macro": {f"{a},{b}": v for (a, b), v in instr.items()},
                "flips": flips,
            })
            for r, c in flips:
                ax = puz["ox"] + GAP * c
                ay = puz["oy"] + GAP * r
                abs_flips.setdefault((ax, ay), (puz["name"], puz["ox"], puz["oy"], r, c))

        plan = list(abs_flips.values())
        # Stable order: top-to-bottom, left-to-right by absolute block origin
        plan.sort(key=lambda t: (t[2] + GAP * t[3], t[1] + GAP * t[4]))
        print(f"unique planned clicks (union): {len(plan)} {[(n, r, c) for n, _, _, r, c in plan]}")
        step = 0
        leveled = False
        for name, ox, oy, r, c in plan:
            step += 1
            cx, cy = l2_block_center(ox, oy, r, c)
            resp = sess.click(cx, cy)
            nf = resp["frame"]
            lv = int(resp.get("levels_completed") or 0)
            d = frame_diff(frame, nf)
            summary = summarize_diff(d)
            print(
                f"click {step} {name}({r},{c})@({cx},{cy}) "
                f"lv={lv} diff={summary}"
            )
            trajectory.append({
                "step": step,
                "puzzle": name,
                "block": [r, c],
                "pixel": [cx, cy],
                "levels_completed": lv,
                "diff_summary": summary,
                "diff_n": len(d),
            })
            frame = nf
            if lv > lv0:
                print(f"  >>> LEVEL INCREMENT {lv0} -> {lv}")
                leveled = True
                break

        lv_end = trajectory[-1]["levels_completed"] if trajectory else lv0
        payload = {
            "game_id": sess.game_id,
            "l2_levels_start": lv0,
            "l2_levels_end": lv_end,
            "cleared": leveled,
            "puzzles": puzzles_info,
            "plan": [
                {"puzzle": n, "ox": ox, "oy": oy, "block": [r, c]}
                for n, ox, oy, r, c in plan
            ],
            "trajectory": trajectory,
        }
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        path = write_report(payload)
        print("saved", FIXTURE)
        print("report", path)
        return 0 if leveled else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
