"""ft09 L5 probe: climb L1–L4, then clear L5.

L5 seated rules:
  - Legend 14/15; solid click toggles 14↔15.
  - Macro labs {0,2,3,14,15}; 3=skip.
  - Target: L4-like on binary palette — 0→fixed, 2→other
    (≡ L3 polarity: fixed==15 → 0=flip; fixed==14 → 2=flip).
  - Color-6 checker blocks are operators: click XORs plus (center+NSEW);
    skip an arm if that neighbor is a 0/2 glyph block. Checker itself
    toggles phase 6/14 ↔ 6/15.
  - Multi-patch targets are consistent; solve solid+checker clicks in GF(2).
  - Win oracle: levels_completed only (progress bar is farmable).

Usage:
  python tools/ft09_l5_click_flip_probe.py
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
CHECKER_COLOR = 6


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


def is_glyph_block(g: np.ndarray, ax: int, ay: int) -> bool:
    patch = g[ay:ay + BLOCK, ax:ax + BLOCK]
    if patch.shape != (BLOCK, BLOCK):
        return False
    return bool(np.any(np.isin(patch, [0, 2])))


def is_checker_block(g: np.ndarray, ax: int, ay: int) -> bool:
    patch = g[ay:ay + BLOCK, ax:ax + BLOCK]
    if patch.shape != (BLOCK, BLOCK):
        return False
    return bool(np.any(patch == CHECKER_COLOR) and np.all(np.isin(patch, [CHECKER_COLOR, BASE_COLOR, FLIP_TO])))


def checker_phase(g: np.ndarray, ax: int, ay: int) -> int:
    """14 = base phase (6/14), 15 = flipped phase (6/15)."""
    patch = g[ay:ay + BLOCK, ax:ax + BLOCK]
    n14 = int(np.sum(patch == BASE_COLOR))
    n15 = int(np.sum(patch == FLIP_TO))
    return FLIP_TO if n15 > n14 else BASE_COLOR


def find_checker_blocks(g: np.ndarray) -> list[tuple[int, int]]:
    """Scan even origins — L5 grid offset is (6,4), not (0,0)."""
    out = []
    for ay in range(0, g.shape[0] - BLOCK + 1, 2):
        for ax in range(0, g.shape[1] - BLOCK + 1, 2):
            if is_checker_block(g, ax, ay):
                out.append((ax, ay))
    return out


def checker_plus_arms(g: np.ndarray, cx: int, cy: int) -> list[tuple[int, int]]:
    """Plus neighborhood; skip glyph arms (0/2 instruction cells)."""
    arms = [(cx, cy)]
    for dx, dy in ((0, -GAP), (0, GAP), (-GAP, 0), (GAP, 0)):
        nx, ny = cx + dx, cy + dy
        if nx < 0 or ny < 0 or nx + BLOCK > g.shape[1] or ny + BLOCK > g.shape[0]:
            continue
        if is_glyph_block(g, nx, ny):
            continue
        arms.append((nx, ny))
    return arms


def l4_like_targets(patches: list[dict]) -> dict[tuple[int, int], int]:
    """0→fixed, 2→other; require multi-patch agreement."""
    votes: dict[tuple[int, int], list[int]] = {}
    for p in patches:
        ix, iy = p["origin"]
        ox, oy = ix - GAP, iy - GAP
        fixed = int(p["fixed_color"])
        other = FLIP_TO if fixed == BASE_COLOR else BASE_COLOR
        for r in range(3):
            for c in range(3):
                if (r, c) == (1, 1):
                    continue
                lab = p["macro"].get(f"{r},{c}")
                if lab == SKIP_LAB:
                    continue
                ax, ay = ox + GAP * c, oy + GAP * r
                des = fixed if lab == 0 else other
                votes.setdefault((ax, ay), []).append(des)
    want = {}
    for cell, cols in votes.items():
        if len(set(cols)) != 1:
            raise RuntimeError(f"L5 target conflict at {cell}: {cols}")
        want[cell] = cols[0]
    return want


def gf2_solve(A: np.ndarray, b: np.ndarray) -> np.ndarray | None:
    """Return one particular solution over GF(2), or None if inconsistent."""
    A = (A.copy() % 2).astype(int)
    b = (b.copy() % 2).astype(int)
    m, n = A.shape
    M = np.concatenate([A, b.reshape(-1, 1)], axis=1)
    row = 0
    pivots = [-1] * n
    for col in range(n):
        piv = None
        for i in range(row, m):
            if M[i, col] == 1:
                piv = i
                break
        if piv is None:
            continue
        M[[row, piv]] = M[[piv, row]]
        for i in range(m):
            if i != row and M[i, col] == 1:
                M[i] = (M[i] + M[row]) % 2
        pivots[col] = row
        row += 1
    for i in range(row, m):
        if M[i, -1] == 1 and not np.any(M[i, :-1]):
            return None
    x = np.zeros(n, dtype=int)
    for col in range(n):
        if pivots[col] >= 0:
            x[col] = M[pivots[col], -1]
    return x


def plan_l5_gf2(g: np.ndarray) -> dict:
    patches = find_l5_instr_patches(g)
    want = l4_like_targets(patches)
    checkers = find_checker_blocks(g)
    plus = {c: checker_plus_arms(g, c[0], c[1]) for c in checkers}

    affected = set(want)
    for arms in plus.values():
        affected.update(arms)
    solids = sorted(c for c in affected if c not in set(checkers))
    vars_list = [("S", c) for c in solids] + [("C", c) for c in checkers]
    idx = {v: i for i, v in enumerate(vars_list)}
    n = len(vars_list)

    rows = []
    bb = []
    for t, w in sorted(want.items()):
        row = [0] * n
        if ("S", t) in idx:
            row[idx[("S", t)]] = 1
        for c, arms in plus.items():
            if t in arms:
                row[idx[("C", c)]] = 1
        rows.append(row)
        bb.append(1 if w == FLIP_TO else 0)

    A = np.array(rows, dtype=int)
    x = gf2_solve(A, np.array(bb, dtype=int))
    if x is None:
        raise RuntimeError("L5 GF(2) system inconsistent")

    plan_s = [c for (k, c), bit in zip(vars_list, x) if k == "S" and bit]
    plan_c = [c for (k, c), bit in zip(vars_list, x) if k == "C" and bit]
    return {
        "patches": patches,
        "want": {f"{a},{b}": v for (a, b), v in want.items()},
        "checkers": [[a, b] for a, b in checkers],
        "plus": {f"{a},{b}": [[x, y] for x, y in arms] for (a, b), arms in plus.items()},
        "plan_solids": [[a, b] for a, b in plan_s],
        "plan_checkers": [[a, b] for a, b in plan_c],
        "ordered": [("S", c) for c in plan_s] + [("C", c) for c in plan_c],
    }


def clear_l5_binary(sess: Ft09Session, frame, lv_expect: int = 4):
    g = _plane(frame)
    planned = plan_l5_gf2(g)
    patches = planned["patches"]
    ordered = planned["ordered"]
    print(
        f"L5 GF2: patches={len(patches)} "
        f"solids={len(planned['plan_solids'])} "
        f"checkers={len(planned['plan_checkers'])} "
        f"hist={color_hist(g)} legend={legend_swatches(g)}"
    )
    for p in patches:
        print(
            f"  patch @{p['origin']} fixed={p['fixed_color']} "
            f"macro={p['macro']}"
        )
    print("  plan_S:", planned["plan_solids"])
    print("  plan_C:", planned["plan_checkers"])
    print("  plus:", planned["plus"])

    trajectory = []
    cur = frame
    step = 0
    lv = lv_expect
    for kind, (ax, ay) in ordered:
        step += 1
        before = (
            checker_phase(_plane(cur), ax, ay)
            if kind == "C"
            else block_majority(_plane(cur), ax, ay)
        )
        resp = sess.click(ax + BLOCK // 2, ay + BLOCK // 2)
        nf = resp["frame"]
        lv = int(resp.get("levels_completed") or 0)
        after = (
            checker_phase(_plane(nf), ax, ay)
            if kind == "C"
            else block_majority(_plane(nf), ax, ay)
        )
        print(f"  click {step} {kind} ({ax},{ay}) {before}->{after} lv={lv}")
        trajectory.append({
            "step": step,
            "kind": kind,
            "block_origin": [ax, ay],
            "before": before,
            "after": after,
            "levels_completed": lv,
        })
        cur = nf
        if lv > lv_expect:
            print(f"  >>> L5 LEVEL {lv_expect} -> {lv}")
            return cur, lv, {
                "cleared": True,
                "levels_end": lv,
                "patches": patches,
                "plan": planned,
                "trajectory": trajectory,
                "legend": legend_swatches(g),
                "hist": color_hist(g),
                "rule": "l4_like_targets_gf2_checker_plus",
            }

    return cur, lv, {
        "cleared": False,
        "levels_end": lv,
        "patches": patches,
        "plan": planned,
        "trajectory": trajectory,
        "legend": legend_swatches(g),
        "hist": color_hist(g),
        "rule": "l4_like_targets_gf2_checker_plus",
    }


def climb_to_level(sess: Ft09Session, target_lv: int):
    """Reach synced frame for level index target_lv (levels_completed == target_lv)."""
    lv = clear_l1(sess)
    frame = sess.action("ACTION1")["frame"]
    history = []
    while lv < target_lv:
        label = f"L{lv + 1}"
        if lv < 3:
            frame, lv, info = clear_level_discovered(sess, frame, lv, label)
        elif lv == 3:
            frame, lv, info = clear_l4_ternary(sess, frame, lv)
            info = {**info, "label": label}
        elif lv == 4:
            frame, lv, info = clear_l5_binary(sess, frame, lv)
            info = {**info, "label": label}
        else:
            raise RuntimeError(f"climb_to_level: no clearer for lv={lv} (want {target_lv})")
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
    plan = clear_info.get("plan") or {}
    if cleared:
        headline = (
            f"**PASS** — L5：`0→fixed` / `2→other`（二元图例 14/15）+ "
            f"色6 checker 十字 XOR；GF(2) 求解后执行；"
            f"`levels` {lv0}→{lv1}；点击 {nclick}。"
        )
        verdict = "l5_gf2_checker_plus_pass"
    else:
        headline = (
            f"**FAIL** — L5 GF(2) 未通关（levels 仍 {lv1}）。"
            f" patches={len(clear_info.get('patches') or [])} "
            f"legend=`{clear_info.get('legend')}` hist=`{clear_info.get('hist')}`。"
        )
        verdict = "l5_gf2_checker_plus_fail"

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
        "## L5 坐实规则",
        "",
        "1. 图例 `14 / 15`：solid 点击二元切换 `14↔15`。",
        "2. 宏格 `{0,2,3,14,15}`；**3=跳过**。",
        "3. 目标语义（L4 二元化）：**`0→fixed`，`2→other`**"
        "（等价 L3 极性：fixed=15→0=翻；fixed=14→2=翻）。",
        "4. **色6 棋盘格**不是装饰：点击对十字邻域做 XOR；臂落在 0/2 字形则跳过；"
        "自身在 `6/14 ↔ 6/15` 间切换。",
        "5. 多图案目标一致；固体点击 + checker 算子 → **GF(2)** 求解。",
        "6. 进度条可刷，**不能**当通关判据；只认 `levels_completed`。",
        "",
        "## 帧摘要",
        "",
        f"- hist: `{clear_info.get('hist')}`",
        f"- legend: `{clear_info.get('legend')}`",
        f"- patches: {len(clear_info.get('patches') or [])}",
        f"- plan_solids: `{plan.get('plan_solids')}`",
        f"- plan_checkers: `{plan.get('plan_checkers')}`",
        f"- plus: `{plan.get('plus')}`",
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
            f"- step {step['step']} {step.get('kind')} "
            f"block={step['block_origin']} "
            f"{step['before']}→{step['after']} "
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
        sess.open(tags=["ft09_l5_gf2"])
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
                "plan": {
                    k: v for k, v in plan_l5_gf2(g).items()
                    if k != "ordered"
                },
            },
        }, indent=2), encoding="utf-8")
        print("saved", FIXTURE_FRAME)

        frame2, lv2, clear_info = clear_l5_binary(sess, frame, lv)
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
            "l5_levels_start": 4,
            "l5_levels_end": clear_info.get("levels_end"),
            "cleared": clear_info.get("cleared"),
            "plan": plan_out,
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
