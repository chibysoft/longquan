"""ft09 L6 probe: climb L1–L5, then clear L6.

L6 seated rules:
  - Legend 11/14; pip-tiles (11 body + top-center color-6 mark) toggle 11↔14
    (color 6 stays).
  - Click flips self; if the north neighbor (ay-GAP) is also a pip-tile, flip it too.
  - Instruction macros {0,2,3,14}; 3=skip; fixed=14.
  - Targets (L4-like): 0→fixed(14), 2→other(11).
  - Multi-patch consistent; solve pip-tile clicks in GF(2) under north-coupling.
  - Win oracle: levels_completed only.

Usage:
  python tools/ft09_l6_click_flip_probe.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ft09_click_flip_probe import Ft09Session  # noqa: E402
from tools.ft09_l3_click_flip_probe import GAP, BLOCK, _plane, color_hist  # noqa: E402
from tools.ft09_l5_click_flip_probe import (  # noqa: E402
    climb_to_level,
    gf2_solve,
    legend_swatches,
)
from tools.ls20_online_validate import _api_key  # noqa: E402

FIXTURE_FRAME = ROOT / "tests" / "fixtures" / "ft09_l6_frame_live.json"
FIXTURE_TRAJ = ROOT / "tests" / "fixtures" / "ft09_l6_click_flip_trajectory.json"
REPORT = ROOT / "docs" / "ft09-l6-click-flip-probe.md"

BASE_COLOR = 11
FLIP_TO = 14
SKIP_LAB = 3
PIP_COLOR = 6


def find_pip_tiles(g: np.ndarray) -> list[tuple[int, int]]:
    """6×6 tiles: only {11,14,6}, exactly one 2×2 of color-6."""
    out = []
    for ay in range(0, g.shape[0] - BLOCK + 1, 2):
        for ax in range(0, g.shape[1] - BLOCK + 1, 2):
            p = g[ay:ay + BLOCK, ax:ax + BLOCK]
            if p.shape != (BLOCK, BLOCK):
                continue
            if int(np.sum(p == PIP_COLOR)) != 4:
                continue
            if not np.all(np.isin(p, [BASE_COLOR, FLIP_TO, PIP_COLOR])):
                continue
            out.append((ax, ay))
    return out


def tile_phase(g: np.ndarray, ax: int, ay: int) -> int:
    p = g[ay:ay + BLOCK, ax:ax + BLOCK]
    n_base = int(np.sum(p == BASE_COLOR))
    n_flip = int(np.sum(p == FLIP_TO))
    return FLIP_TO if n_flip > n_base else BASE_COLOR


def find_l6_instr_patches(g: np.ndarray) -> list[dict]:
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
                "macro": {
                    f"{r},{c}": macro[(r, c)] for r in range(3) for c in range(3)
                },
            })
    out.sort(key=lambda t: (t["origin"][1], t["origin"][0]))
    return out


def l4_like_targets(patches: list[dict]) -> dict[tuple[int, int], int]:
    votes: dict[tuple[int, int], list[int]] = defaultdict(list)
    for p in patches:
        ix, iy = p["origin"]
        ox, oy = ix - GAP, iy - GAP
        fixed = int(p["fixed_color"])
        other = BASE_COLOR if fixed == FLIP_TO else FLIP_TO
        for r in range(3):
            for c in range(3):
                if (r, c) == (1, 1):
                    continue
                lab = p["macro"].get(f"{r},{c}")
                if lab == SKIP_LAB:
                    continue
                ax, ay = ox + GAP * c, oy + GAP * r
                des = fixed if lab == 0 else other
                votes[(ax, ay)].append(des)
    want = {}
    for cell, cols in votes.items():
        if len(set(cols)) != 1:
            raise RuntimeError(f"L6 target conflict at {cell}: {cols}")
        want[cell] = cols[0]
    return want


def click_effect(tile: tuple[int, int], tile_set: set[tuple[int, int]]) -> list[tuple[int, int]]:
    ax, ay = tile
    eff = [tile]
    north = (ax, ay - GAP)
    if north in tile_set:
        eff.append(north)
    return eff


def plan_l6_gf2(g: np.ndarray) -> dict:
    tiles = find_pip_tiles(g)
    tile_set = set(tiles)
    patches = find_l6_instr_patches(g)
    want_all = l4_like_targets(patches)
    want = {c: w for c, w in want_all.items() if c in tile_set}

    vars_list = list(tiles)
    idx = {c: i for i, c in enumerate(vars_list)}
    n = len(vars_list)
    rows = []
    bb = []
    for t, w in sorted(want.items()):
        row = [0] * n
        for src in vars_list:
            if t in click_effect(src, tile_set):
                row[idx[src]] = 1
        rows.append(row)
        bb.append(1 if w == FLIP_TO else 0)

    x = gf2_solve(np.array(rows, dtype=int), np.array(bb, dtype=int))
    if x is None:
        raise RuntimeError("L6 GF(2) system inconsistent")
    plan = [c for c, bit in zip(vars_list, x) if bit]

    effects = {
        f"{a},{b}": [[x, y] for x, y in click_effect((a, b), tile_set)]
        for a, b in tiles
    }
    return {
        "patches": patches,
        "tiles": [[a, b] for a, b in tiles],
        "want": {f"{a},{b}": v for (a, b), v in want.items()},
        "effects": effects,
        "plan": [[a, b] for a, b in plan],
        "ordered": plan,
    }


def clear_l6(sess: Ft09Session, frame, lv_expect: int = 5):
    g = _plane(frame)
    planned = plan_l6_gf2(g)
    print(
        f"L6 GF2: patches={len(planned['patches'])} "
        f"tiles={len(planned['tiles'])} plan={len(planned['plan'])} "
        f"hist={color_hist(g)} legend={legend_swatches(g)}"
    )
    for p in planned["patches"]:
        print(
            f"  patch @{p['origin']} fixed={p['fixed_color']} "
            f"macro={p['macro']}"
        )
    print("  plan:", planned["plan"])

    trajectory = []
    cur = frame
    lv = lv_expect
    for step, (ax, ay) in enumerate(planned["ordered"], 1):
        before = tile_phase(_plane(cur), ax, ay)
        resp = sess.click(ax + BLOCK // 2, ay + BLOCK // 2)
        nf = resp["frame"]
        lv = int(resp.get("levels_completed") or 0)
        after = tile_phase(_plane(nf), ax, ay)
        print(f"  click {step} ({ax},{ay}) {before}->{after} lv={lv}")
        trajectory.append({
            "step": step,
            "block_origin": [ax, ay],
            "before": before,
            "after": after,
            "levels_completed": lv,
        })
        cur = nf
        if lv > lv_expect:
            print(f"  >>> L6 LEVEL {lv_expect} -> {lv}")
            return cur, lv, {
                "cleared": True,
                "levels_end": lv,
                "plan": planned,
                "trajectory": trajectory,
                "legend": legend_swatches(g),
                "hist": color_hist(g),
                "rule": "l4_like_north_couple_gf2",
            }

    return cur, lv, {
        "cleared": False,
        "levels_end": lv,
        "plan": planned,
        "trajectory": trajectory,
        "legend": legend_swatches(g),
        "hist": color_hist(g),
        "rule": "l4_like_north_couple_gf2",
    }


def write_report(clear_info: dict, meta: dict) -> Path:
    cleared = bool(clear_info.get("cleared"))
    lv0 = meta.get("levels_start", 5)
    lv1 = clear_info.get("levels_end", lv0)
    nclick = len(clear_info.get("trajectory") or [])
    plan = clear_info.get("plan") or {}
    if cleared:
        headline = (
            f"**PASS** — L6：pip 砖 `11↔14` + 北邻耦合 XOR；"
            f"目标 `0→fixed`/`2→other`；GF(2) 求解；"
            f"`levels` {lv0}→{lv1}；点击 {nclick}。"
        )
        verdict = "l6_north_couple_gf2_pass"
    else:
        headline = (
            f"**FAIL** — L6 未通关（levels 仍 {lv1}）。"
            f" hist=`{clear_info.get('hist')}` legend=`{clear_info.get('legend')}`。"
        )
        verdict = "l6_north_couple_gf2_fail"

    lines = [
        "# ft09 L6 点击闭环探针",
        "",
        "> 脚本：`tools/ft09_l6_click_flip_probe.py`",
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
        "## L6 坐实规则",
        "",
        "1. 图例 `11 / 14`：pip 砖（主体 11/14 + 顶中色6 标记）二元切换；色6 保留。",
        "2. **北邻耦合**：点击翻转自身；若正北 `ay-GAP` 也是 pip 砖，则一并翻转。",
        "3. 宏格 `{0,2,3,14}`；**3=跳过**；本关 fixed 均为 14。",
        "4. 目标（L4 二元化）：**`0→fixed`，`2→other(11)`**。",
        "5. 多图案一致；在北邻耦合下 **GF(2)** 求解点击集。",
        "6. 只认 `levels_completed`。",
        "",
        "## 帧摘要",
        "",
        f"- hist: `{clear_info.get('hist')}`",
        f"- legend: `{clear_info.get('legend')}`",
        f"- tiles: {len(plan.get('tiles') or [])}",
        f"- plan: `{plan.get('plan')}`",
        "",
    ]
    for i, p in enumerate(plan.get("patches") or []):
        lines.append(
            f"- patch[{i}] origin=`{p['origin']}` fixed=`{p['fixed_color']}` "
            f"macro=`{p['macro']}`"
        )
    lines += ["", "## 轨迹", ""]
    for step in clear_info.get("trajectory", []):
        lines.append(
            f"- step {step['step']} block={step['block_origin']} "
            f"{step['before']}→{step['after']} lv={step['levels_completed']}"
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
        sess.open(tags=["ft09_l6_gf2"])
        frame, lv, history = climb_to_level(sess, target_lv=5)
        g = _plane(frame)
        FIXTURE_FRAME.parent.mkdir(parents=True, exist_ok=True)
        planned = plan_l6_gf2(g)
        FIXTURE_FRAME.write_text(json.dumps({
            "game_id": sess.game_id,
            "meta": {"levels_completed": lv},
            "frame": np.asarray(g).tolist(),
            "analysis": {
                "hist": color_hist(g),
                "legend": legend_swatches(g),
                "tiles": planned["tiles"],
                "patches": planned["patches"],
                "plan": planned["plan"],
            },
        }, indent=2), encoding="utf-8")
        print("saved", FIXTURE_FRAME)

        _frame2, _lv2, clear_info = clear_l6(sess, frame, lv)
        plan_out = {
            k: v for k, v in (clear_info.get("plan") or {}).items()
            if k != "ordered"
        }
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
            "l6_levels_start": 5,
            "l6_levels_end": clear_info.get("levels_end"),
            "cleared": clear_info.get("cleared"),
            "plan": plan_out,
            "legend": clear_info.get("legend"),
            "trajectory": clear_info.get("trajectory"),
            "rule": clear_info.get("rule"),
        }
        FIXTURE_TRAJ.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        path = write_report(clear_info, {"levels_start": 5})
        print("saved", FIXTURE_TRAJ)
        print("report", path)
        return 0 if clear_info.get("cleared") else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
