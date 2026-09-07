"""ft09 L4 ternary mask-flip closed-loop probe.

L4 lock (2026-09-07):
  - Top-right legend stack 9/8/12 = click cycle order: 9→8→12→9.
  - Each instr patch: macro 0 → target=fixed_color; macro 2 → target=8.
  - Overlapping 3x3s: targets are consistent under this map; click each cell
    enough times to reach target (0–2 clicks).
  - Pass = levels_completed 3→4 only.

Climb L1–L3 with polarity-aware binary solver, ACTION1 sync, then L4 ternary.

Usage:
  python tools/ft09_l4_click_flip_probe.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ft09_click_flip_probe import Ft09Session  # noqa: E402
from tools.ft09_l3_click_flip_probe import (  # noqa: E402
    GAP,
    BLOCK,
    _plane,
    analyze_level,
    clear_l1,
    clear_level_discovered,
    find_instr_patches,
    frame_diff,
    summarize_diff,
)
from tools.ls20_online_validate import _api_key  # noqa: E402

FIXTURE_FRAME = ROOT / "tests" / "fixtures" / "ft09_l4_frame_live.json"
FIXTURE_TRAJ = ROOT / "tests" / "fixtures" / "ft09_l4_click_flip_trajectory.json"
REPORT = ROOT / "docs" / "ft09-l4-click-flip-probe.md"

CYCLE = {9: 8, 8: 12, 12: 9}


def clicks_needed(cur: int, target: int) -> int | None:
    n = 0
    while cur != target and n < 3:
        cur = CYCLE[cur]
        n += 1
    return n if cur == target else None


def l4_targets(patches: list[dict]) -> dict[tuple[int, int], int]:
    """0 → fixed_color; 2 → 8. Raises on conflict."""
    cell_t: dict[tuple[int, int], int] = {}
    for p in patches:
        ix, iy = p["origin"]
        ox, oy = ix - GAP, iy - GAP
        fixed = int(p["fixed_color"])
        for r in range(3):
            for c in range(3):
                if (r, c) == (1, 1):
                    continue
                lab = p["macro"][f"{r},{c}"]
                if lab == "0":
                    tgt = fixed
                elif lab == "2":
                    tgt = 8
                else:
                    continue
                ax, ay = ox + GAP * c, oy + GAP * r
                prev = cell_t.get((ax, ay))
                if prev is not None and prev != tgt:
                    raise RuntimeError(
                        f"L4 target conflict at {(ax, ay)}: {prev} vs {tgt} "
                        f"from patch {p['origin']}"
                    )
                cell_t[(ax, ay)] = tgt
    return cell_t


def clear_l4_ternary(sess: Ft09Session, frame, lv_expect: int = 3):
    g = _plane(frame)
    patches = find_instr_patches(g)
    targets = l4_targets(patches)
    need: dict[tuple[int, int], int] = {}
    for (ax, ay), tgt in targets.items():
        patch = g[ay:ay + BLOCK, ax:ax + BLOCK]
        if patch.shape != (BLOCK, BLOCK):
            continue
        vals, cnts = np.unique(patch, return_counts=True)
        maj = int(vals[np.argmax(cnts)])
        if maj not in CYCLE:
            continue
        n = clicks_needed(maj, tgt)
        if n is None:
            raise RuntimeError(f"cannot reach {tgt} from {maj} at {(ax, ay)}")
        if n:
            need[(ax, ay)] = n

    print(
        f"L4 ternary: patches={len(patches)} cells={len(need)} "
        f"total_clicks={sum(need.values())}"
    )
    for p in patches:
        print(
            f"  patch @{p['origin']} fixed={p['fixed_color']} macro={p['macro']}"
        )

    trajectory = []
    cur = frame
    step = 0
    for (ax, ay), n in sorted(need.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        for _ in range(n):
            step += 1
            before = int(np.median(_plane(cur)[ay:ay + BLOCK, ax:ax + BLOCK]))
            resp = sess.click(ax + BLOCK // 2, ay + BLOCK // 2)
            nf = resp["frame"]
            lv = int(resp.get("levels_completed") or 0)
            after = int(np.median(_plane(nf)[ay:ay + BLOCK, ax:ax + BLOCK]))
            summary = summarize_diff(frame_diff(cur, nf))
            print(
                f"  click {step} ({ax},{ay}) {before}->{after} "
                f"lv={lv} diff={summary}"
            )
            trajectory.append({
                "step": step,
                "block_origin": [ax, ay],
                "pixel": [ax + BLOCK // 2, ay + BLOCK // 2],
                "before": before,
                "after": after,
                "target": targets[(ax, ay)],
                "levels_completed": lv,
                "diff_summary": summary,
            })
            cur = nf
            if lv > lv_expect:
                print(f"  >>> L4 LEVEL {lv_expect} -> {lv}")
                return cur, lv, {
                    "cleared": True,
                    "levels_end": lv,
                    "patches": patches,
                    "targets": {f"{a},{b}": t for (a, b), t in targets.items()},
                    "need": {f"{a},{b}": n for (a, b), n in need.items()},
                    "trajectory": trajectory,
                    "rule": "0->fixed_color; 2->8; cycle 9->8->12->9",
                }

    return cur, lv_expect, {
        "cleared": False,
        "levels_end": trajectory[-1]["levels_completed"] if trajectory else lv_expect,
        "patches": patches,
        "targets": {f"{a},{b}": t for (a, b), t in targets.items()},
        "need": {f"{a},{b}": n for (a, b), n in need.items()},
        "trajectory": trajectory,
        "rule": "0->fixed_color; 2->8; cycle 9->8->12->9",
    }


def climb_to_l4(sess: Ft09Session):
    lv = clear_l1(sess)
    frame = sess.action("ACTION1")["frame"]
    history = []
    while lv < 3:
        label = f"L{lv + 1}"
        frame, lv, info = clear_level_discovered(sess, frame, lv, label)
        history.append(info)
        if not info.get("cleared"):
            raise RuntimeError(f"{label} clear failed")
        synced = sess.action("ACTION1")
        frame = synced["frame"]
        print(
            f"synced after {label}: lv={synced.get('levels_completed')} "
            f"actions={synced.get('available_actions')}"
        )
    return frame, lv, history


def write_report(analysis: dict, clear_info: dict, meta: dict) -> Path:
    cleared = bool(clear_info.get("cleared"))
    lv0 = meta.get("levels_start", 3)
    lv1 = clear_info.get("levels_end", lv0)
    if cleared:
        headline = (
            f"**PASS** — L4 三态 mask-flip：`0→fixed色`，`2→8`，"
            f"点击沿 `9→8→12→9` 循环到位；`levels` {lv0}→{lv1}；"
            f"总点击 {sum(clear_info.get('need', {}).values())}。"
        )
        verdict = "l4_ternary_mask_flip_pass"
    else:
        headline = f"**FAIL** — L4 ternary 未使 levels {lv0}→4（仍为 {lv1}）。"
        verdict = "l4_ternary_mask_flip_fail"

    lines = [
        "# ft09 L4 点击闭环探针",
        "",
        "> 脚本：`tools/ft09_l4_click_flip_probe.py`",
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
        "## L4 坐实规则",
        "",
        "1. **右上图例** `9 / 8 / 12`（各 4×4）= 点击循环次序。",
        "2. **宏格语义**：`0 → 该图案 fixed 色`；`2 → 8`。",
        "3. **多图案**：三枚 3×3（fixed 12 / 9 / 12）目标在共享格上一致；按格点击 0–2 次到位。",
        "4. 二进制「只点一次 9→8」**不够**；此前失败原因在此。",
        "",
        "## 帧摘要",
        "",
        f"- hist: `{analysis.get('hist')}`",
        f"- patches: {len(analysis.get('patches') or [])}",
        f"- need: `{clear_info.get('need')}`",
        "",
        "## 轨迹",
        "",
    ]
    for step in clear_info.get("trajectory", []):
        lines.append(
            f"- step {step['step']} block={step['block_origin']} "
            f"{step['before']}→{step['after']} (tgt {step['target']}) "
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
        sess.open(tags=["ft09_l4_ternary"])
        frame, lv, history = climb_to_l4(sess)
        analysis = analyze_level(frame, "L4")
        FIXTURE_FRAME.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE_FRAME.write_text(json.dumps({
            "game_id": sess.game_id,
            "meta": {"levels_completed": lv},
            "frame": np.asarray(_plane(frame)).tolist(),
            "analysis": {
                **{k: v for k, v in analysis.items() if k != "plan"},
                "plan": analysis.get("plan"),
            },
        }, indent=2), encoding="utf-8")
        print("saved", FIXTURE_FRAME)

        frame, lv, clear_info = clear_l4_ternary(sess, frame, lv)
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
            "l4_levels_start": 3,
            "l4_levels_end": clear_info.get("levels_end"),
            "cleared": clear_info.get("cleared"),
            "rule": clear_info.get("rule"),
            "need": clear_info.get("need"),
            "targets": clear_info.get("targets"),
            "trajectory": clear_info.get("trajectory"),
        }
        FIXTURE_TRAJ.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        path = write_report(analysis, clear_info, {"levels_start": 3})
        print("saved", FIXTURE_TRAJ)
        print("report", path)
        return 0 if clear_info.get("cleared") else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
