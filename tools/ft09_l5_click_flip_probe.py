"""ft09 L5 probe: climb L1–L4, then clear L5 with binary 14↔15 + polarity.

L5 rules (discovered):
  - Legend top-right (x≈56): 14 then 15 — click toggles solid blocks 14↔15.
  - Instruction 6×6 macros use {0,2,3,14,15}; color 3 = skip (bg / OOB / other glyph).
  - Polarity (L3-style): fixed==15 → normal (0=flip); fixed==14 → inverted (2=flip).
  - Only click solid majority-14 blocks once (union).

Usage:
  python tools/ft09_l5_click_flip_probe.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ft09_click_flip_probe import Ft09Session  # noqa: E402
from tools.ft09_l3_click_flip_probe import (  # noqa: E402
    BLOCK,
    GAP,
    _plane,
    clear_l1,
    clear_level_discovered,
    color_hist,
)
from tools.ft09_l4_click_flip_probe import clear_l4_ternary  # noqa: E402
from tools.ls20_online_validate import _api_key  # noqa: E402

FIXTURE_FRAME = ROOT / "tests" / "fixtures" / "ft09_l5_frame_live.json"
FIXTURE_TRAJ = ROOT / "tests" / "fixtures" / "ft09_l5_click_flip_trajectory.json"
REPORT = ROOT / "docs" / "ft09-l5-click-flip-probe.md"

BASE_COLOR = 14
FLIP_TO = 15
SKIP_LAB = 3


def legend_swatches(g: np.ndarray) -> list[dict]:
    """Detect top-right legend stack (L4 at x=60; L5 at x=56)."""
    out = []
    for x0 in (56, 60):
        for y0 in range(0, 16, 4):
            patch = g[y0:y0 + 4, x0:x0 + 4]
            if patch.shape != (4, 4):
                continue
            if np.all(patch == patch[0, 0]) and int(patch[0, 0]) != 4:
                out.append({"x0": x0, "y0": y0, "color": int(patch[0, 0])})
        if out:
            break
    return out


def find_l5_instr_patches(g: np.ndarray) -> list[dict]:
    """6×6 even-origin macros with 0+2, uniform center in {14,15}."""
    out = []
    seen = set()
    for y in range(0, g.shape[0] - 5, 2):
        for x in range(0, g.shape[1] - 5, 2):
            p = g[y:y + 6, x:x + 6]
            vals = {int(v) for v in p.flatten().tolist()}
            if 4 in vals or 0 not in vals or 2 not in vals:
                continue
            center = p[2:4, 2:4]
            if not np.all(center == center[0, 0]):
                continue
            fcol = int(center[0, 0])
            if fcol not in (BASE_COLOR, FLIP_TO):
                continue
            macro = {}
            ok = True
            for r in range(3):
                for c in range(3):
                    cell = p[2 * r:2 * r + 2, 2 * c:2 * c + 2]
                    if not np.all(cell == cell[0, 0]):
                        ok = False
                        break
                    macro[(r, c)] = int(cell[0, 0])
                if not ok:
                    break
            if not ok or (x, y) in seen:
                continue
            seen.add((x, y))
            out.append({
                "origin": [x, y],
                "fixed_color": fcol,
                "macro": {f"{r},{c}": macro[(r, c)] for r in range(3) for c in range(3)},
                "hist": color_hist(p),
            })
    out.sort(key=lambda t: (t["origin"][1], t["origin"][0]))
    return out


def block_majority(g: np.ndarray, ax: int, ay: int) -> int | None:
    patch = g[ay:ay + BLOCK, ax:ax + BLOCK]
    if patch.shape != (BLOCK, BLOCK):
        return None
    vals, cnts = np.unique(patch, return_counts=True)
    return int(vals[np.argmax(cnts)])


def is_solid_color(g: np.ndarray, ax: int, ay: int, color: int) -> bool:
    patch = g[ay:ay + BLOCK, ax:ax + BLOCK]
    if patch.shape != (BLOCK, BLOCK):
        return False
    return bool(np.all(patch == color))


def union_flip_cells(patches: list[dict]) -> list[dict]:
    """L3 polarity on L5 palette; skip lab==3."""
    flips: dict[tuple[int, int], dict] = {}
    for p in patches:
        ix, iy = p["origin"]
        ox, oy = ix - GAP, iy - GAP
        fixed = int(p["fixed_color"])
        inverted = fixed == BASE_COLOR and fixed != FLIP_TO
        polarity = "inverted" if inverted else "normal"
        for r in range(3):
            for c in range(3):
                if (r, c) == (1, 1):
                    continue
                lab = p["macro"].get(f"{r},{c}")
                if lab == SKIP_LAB:
                    continue
                if inverted:
                    should = lab == 2
                else:
                    should = lab == 0
                if not should:
                    continue
                ax, ay = ox + GAP * c, oy + GAP * r
                flips.setdefault((ax, ay), {
                    "ax": ax, "ay": ay,
                    "cx": ax + BLOCK // 2,
                    "cy": ay + BLOCK // 2,
                    "polarity": polarity,
                    "fixed_color": fixed,
                    "instr": [ix, iy],
                })
    return sorted(flips.values(), key=lambda t: (t["ay"], t["ax"]))


def clear_l5_binary(sess: Ft09Session, frame, lv_expect: int = 4):
    g = _plane(frame)
    patches = find_l5_instr_patches(g)
    plan = union_flip_cells(patches)
    # Prefer solid base blocks; keep non-solid as optional (checkers) after solids.
    solids = [c for c in plan if is_solid_color(g, c["ax"], c["ay"], BASE_COLOR)]
    others = [c for c in plan if c not in solids]
    ordered = solids + others
    print(
        f"L5 binary: patches={len(patches)} plan={len(plan)} "
        f"solid14={len(solids)} other={len(others)} "
        f"hist={color_hist(g)} legend={legend_swatches(g)}"
    )
    for p in patches:
        print(
            f"  patch @{p['origin']} fixed={p['fixed_color']} "
            f"macro={p['macro']}"
        )
    print("  flips:", [(c["ax"], c["ay"], c["polarity"]) for c in ordered])

    trajectory = []
    cur = frame
    step = 0
    for cell in ordered:
        ax, ay = cell["ax"], cell["ay"]
        maj = block_majority(_plane(cur), ax, ay)
        if maj != BASE_COLOR:
            print(f"  skip ({ax},{ay}) maj={maj}")
            continue
        step += 1
        before = maj
        resp = sess.click(cell["cx"], cell["cy"])
        nf = resp["frame"]
        lv = int(resp.get("levels_completed") or 0)
        after = block_majority(_plane(nf), ax, ay)
        print(f"  click {step} ({ax},{ay}) {before}->{after} lv={lv}")
        trajectory.append({
            "step": step,
            "block_origin": [ax, ay],
            "before": before,
            "after": after,
            "target": FLIP_TO,
            "polarity": cell["polarity"],
            "levels_completed": lv,
        })
        cur = nf
        if lv > lv_expect:
            print(f"  >>> L5 LEVEL {lv_expect} -> {lv}")
            return cur, lv, {
                "cleared": True,
                "levels_end": lv,
                "patches": patches,
                "plan": [
                    {"ax": c["ax"], "ay": c["ay"], "polarity": c["polarity"]}
                    for c in ordered
                ],
                "trajectory": trajectory,
                "legend": legend_swatches(g),
                "hist": color_hist(g),
                "rule": "binary_14_15_polarity",
            }

    return cur, lv_expect, {
        "cleared": False,
        "levels_end": (
            trajectory[-1]["levels_completed"] if trajectory else lv_expect
        ),
        "patches": patches,
        "plan": [
            {"ax": c["ax"], "ay": c["ay"], "polarity": c["polarity"]}
            for c in ordered
        ],
        "trajectory": trajectory,
        "legend": legend_swatches(g),
        "hist": color_hist(g),
        "rule": "binary_14_15_polarity",
    }


def climb_to_level(sess: Ft09Session, target_lv: int):
    """Reach synced frame for level index target_lv (levels_completed == target_lv)."""
    lv = clear_l1(sess)
    frame = sess.action("ACTION1")["frame"]
    history = []
    while lv < target_lv:
        if lv < 3:
            label = f"L{lv + 1}"
            frame, lv, info = clear_level_discovered(sess, frame, lv, label)
        else:
            label = f"L{lv + 1}"
            frame, lv, info = clear_l4_ternary(sess, frame, lv)
            info = {**info, "label": label}
        history.append(info)
        if not info.get("cleared"):
            raise RuntimeError(f"{label} clear failed during climb")
        synced = sess.action("ACTION1")
        frame = synced["frame"]
        print(
            f"synced after {label}: lv={synced.get('levels_completed')} "
            f"actions={synced.get('available_actions')}"
        )
    return frame, lv, history


def write_report(clear_info: dict, meta: dict) -> Path:
    cleared = bool(clear_info.get("cleared"))
    lv0 = meta.get("levels_start", 4)
    lv1 = clear_info.get("levels_end", lv0)
    nclick = len(clear_info.get("trajectory") or [])
    if cleared:
        headline = (
            f"**PASS** — L5 二元 mask-flip：`14↔15`，极性同 L3"
            f"（fixed=15→0=翻；fixed=14→2=翻；lab=3 跳过）；"
            f"`levels` {lv0}→{lv1}；点击 {nclick}。"
        )
        verdict = "l5_binary_polarity_pass"
    else:
        headline = (
            f"**FAIL** — L5 二元极性未通关（levels 仍 {lv1}）。"
            f" patches={len(clear_info.get('patches') or [])} "
            f"legend=`{clear_info.get('legend')}` hist=`{clear_info.get('hist')}`。"
        )
        verdict = "l5_binary_polarity_fail"

    lines = [
        "# ft09 L5 点击闭环探针",
        "",
        "> 脚本：`tools/ft09_l5_click_flip_probe.py`",
        f"> 真帧：`{FIXTURE_FRAME.as_posix()}`",
        f"> 轨迹：`{FIXTURE_TRAJ.as_posix()}`",
        f"> 判据：`levels_completed` `{lv0}` → `{lv1}`",
        "",
        "## 结论",
        "",
        headline,
        "",
        f"> verdict=`{verdict}`",
        "",
        "## L5 坐实 / 候选规则",
        "",
        "1. 右上图例 `14 / 15`（x≈56）= 点击二元切换。",
        "2. 指令宏格字母表 `{0,2,3,14,15}`；**3 = 跳过**（背景/越界/邻接字形）。",
        "3. 极性：`fixed==15` → 正常 0=翻；`fixed==14` → 反转 2=翻。",
        "4. 多图案并集，只点 solid-14 一次。",
        "",
        "## 帧摘要",
        "",
        f"- hist: `{clear_info.get('hist')}`",
        f"- legend: `{clear_info.get('legend')}`",
        f"- patches: {len(clear_info.get('patches') or [])}",
        f"- plan: `{clear_info.get('plan')}`",
        "",
    ]
    for i, p in enumerate(clear_info.get("patches") or []):
        lines.append(
            f"- patch[{i}] origin=`{p['origin']}` fixed=`{p['fixed_color']}` "
            f"macro=`{p['macro']}`"
        )
    lines += ["", "## 轨迹", ""]
    for step in clear_info.get("trajectory", []):
        lines.append(
            f"- step {step['step']} block={step['block_origin']} "
            f"{step['before']}→{step['after']} ({step.get('polarity')}) "
            f"lv={step['levels_completed']}"
        )
    lines += [
        "",
        "## 产物",
        "",
        f"- `{FIXTURE_FRAME.as_posix()}`",
        f"- `{FIXTURE_TRAJ.as_posix()}`",
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
        sess.open(tags=["ft09_l5_binary"])
        frame, lv, history = climb_to_level(sess, target_lv=4)
        g = _plane(frame)
        FIXTURE_FRAME.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE_FRAME.write_text(json.dumps({
            "game_id": sess.game_id,
            "meta": {"levels_completed": lv},
            "frame": np.asarray(g).tolist(),
            "analysis": {
                "hist": color_hist(g),
                "legend": legend_swatches(g),
                "patches": find_l5_instr_patches(g),
            },
        }, indent=2), encoding="utf-8")
        print("saved", FIXTURE_FRAME)

        frame2, lv2, clear_info = clear_l5_binary(sess, frame, lv)
        payload = {
            "game_id": sess.game_id,
            "climb": [
                {
                    "label": h.get("label"),
                    "cleared": h.get("cleared"),
                    "levels_end": h.get("levels_end"),
                }
                for h in history
            ],
            "l5_levels_start": 4,
            "l5_levels_end": clear_info.get("levels_end"),
            "cleared": clear_info.get("cleared"),
            "plan": clear_info.get("plan"),
            "legend": clear_info.get("legend"),
            "trajectory": clear_info.get("trajectory"),
            "rule": clear_info.get("rule"),
        }
        FIXTURE_TRAJ.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        path = write_report(clear_info, {"levels_start": 4})
        print("saved", FIXTURE_TRAJ)
        print("report", path)
        return 0 if clear_info.get("cleared") else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
