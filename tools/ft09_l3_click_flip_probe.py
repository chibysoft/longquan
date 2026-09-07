"""ft09 L3 mask-flip closed-loop probe.

Reach true L3 (clear L1+L2 + ACTION1 sync each time), discover 0/2 instruction
patches from the frame (no canned coords), polarity-aware union-flip, ask only
whether levels_completed 2->3.

Empirical rules:
  L1/L2: 0=flip, 2=keep; flip_to == fixed token; base often 9.
  L3 lock: base=8, flip_to=12; four overlapping 3x3s on a plus-shaped lattice.
    fixed_color == flip_to  -> normal polarity (0=flip)
    fixed_color == base     -> inverted polarity (2=flip)
  After level-up: stale frame; ACTION1 syncs next level.
  Shared blocks: absolute union, click each once.

Usage:
  python tools/ft09_l3_click_flip_probe.py
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
    frame_diff,
    read_instruction,
)
from tools.ls20_online_validate import _api_key  # noqa: E402

FIXTURE_FRAME = ROOT / "tests" / "fixtures" / "ft09_l3_frame_live.json"
FIXTURE_TRAJ = ROOT / "tests" / "fixtures" / "ft09_l3_click_flip_trajectory.json"
REPORT = ROOT / "docs" / "ft09-l3-click-flip-probe.md"

BLOCK, GAP = 6, 8


def color_hist(g: np.ndarray) -> dict:
    return {int(k): int(v) for k, v in Counter(g.flatten().tolist()).items()}


def summarize_diff(d) -> dict:
    pairs = Counter((a, b) for _, _, a, b in d)
    return {f"{a}->{b}": n for (a, b), n in pairs.most_common(8)}


def read_instr_at(g: np.ndarray, ix: int, iy: int) -> dict:
    macro = {}
    for r in range(3):
        for c in range(3):
            cell = g[iy + 2 * r:iy + 2 * r + 2, ix + 2 * c:ix + 2 * c + 2]
            if cell.shape != (2, 2):
                macro[(r, c)] = "oob"
            elif np.all(cell == 0):
                macro[(r, c)] = "0"
            elif np.all(cell == 2):
                macro[(r, c)] = "2"
            elif np.all(cell == 8) or np.all(cell == 12) or np.all(cell == 9):
                macro[(r, c)] = "fixed"
            else:
                vals = sorted({int(v) for v in cell.flatten().tolist()})
                macro[(r, c)] = f"mixed{vals}"
    return macro


def find_instr_patches(g: np.ndarray) -> list[dict]:
    """6x6 windows over {0,2,8,9,12} containing both 0 and 2; even origins only."""
    H, W = g.shape
    out = []
    seen = set()
    for y in range(0, H - 5, 2):
        for x in range(0, W - 5, 2):
            p = g[y:y + 6, x:x + 6]
            vals = {int(v) for v in p.flatten().tolist()}
            if not vals <= {0, 2, 8, 9, 12}:
                continue
            if 0 not in vals or 2 not in vals:
                continue
            if (x, y) in seen:
                continue
            seen.add((x, y))
            macro = read_instr_at(g, x, y)
            if macro.get((1, 1)) != "fixed":
                continue
            fcol = int(g[y + 2, x + 2])
            if fcol not in (8, 9, 12):
                continue
            out.append({
                "origin": [x, y],
                "hist": color_hist(p),
                "macro": {f"{r},{c}": macro[(r, c)] for r in range(3) for c in range(3)},
                "fixed_color": fcol,
            })
    out.sort(key=lambda t: (t["origin"][1], t["origin"][0]))
    return out


def infer_base_and_flip(g: np.ndarray, patches: list[dict]) -> tuple[int, int]:
    """Infer unflipped base and flip landing color from histogram + fixed tokens.

    L1/L4: base9, flip_to8 (8 present as examples or legend swatch).
    L2: base9, flip_to12 (no color8; fixed glyphs are 12).
    L3: base8, flip_to12 (fixed mix 8/12; polarity uses base vs flip_to).
    """
    n9 = int(np.sum(g == 9))
    n8 = int(np.sum(g == 8))
    base = 9 if n9 >= n8 else 8
    fixeds = {int(p["fixed_color"]) for p in patches}
    if 12 in fixeds and (n8 == 0 or base == 8):
        flip_to = 12
    elif base == 9:
        flip_to = 8
    else:
        flip_to = 12
    return base, flip_to


def union_plan_from_patches(
    patches: list[dict],
    *,
    base_color: int,
    flip_to: int,
) -> list[dict]:
    """Polarity-aware union of absolute flip cells.

    fixed == flip_to -> normal: macro 0 means flip
    fixed == base    -> inverted: macro 2 means flip
    """
    abs_flips: dict[tuple[int, int], dict] = {}
    for p in patches:
        ix, iy = p["origin"]
        ox, oy = ix - GAP, iy - GAP
        fixed = int(p["fixed_color"])
        inverted = fixed == base_color and fixed != flip_to
        polarity = "inverted" if inverted else "normal"
        for r in range(3):
            for c in range(3):
                if (r, c) == (1, 1):
                    continue
                lab = p["macro"].get(f"{r},{c}")
                if inverted:
                    should_flip = lab == "2"
                else:
                    should_flip = lab == "0"
                if not should_flip:
                    continue
                ax = ox + GAP * c
                ay = oy + GAP * r
                abs_flips.setdefault((ax, ay), {
                    "ax": ax, "ay": ay,
                    "ox": ox, "oy": oy,
                    "block": [r, c],
                    "instr": [ix, iy],
                    "fixed_color": fixed,
                    "polarity": polarity,
                    "cx": ax + BLOCK // 2,
                    "cy": ay + BLOCK // 2,
                })
    return sorted(abs_flips.values(), key=lambda t: (t["ay"], t["ax"]))


def clear_l1(sess: Ft09Session) -> int:
    reset = sess.reset()
    frame = reset["frame"]
    lv0 = int(reset.get("levels_completed") or 0)
    instr = read_instruction(frame)
    clicks = [
        (r, c) for r in range(3) for c in range(3)
        if (r, c) != (1, 1) and instr.get((r, c)) == "flip"
    ]
    print(f"L1 flips={clicks}")
    for r, c in clicks:
        resp = sess.click(*block_center(r, c))
        lv = int(resp.get("levels_completed") or 0)
        print(f"  L1 ({r},{c}) -> lv={lv}")
        if lv > lv0:
            return lv
    raise RuntimeError("L1 clear failed")


def clear_level_discovered(sess: Ft09Session, frame, lv_expect: int, label: str):
    g = _plane(frame)
    patches = find_instr_patches(g)
    base, flip_to = infer_base_and_flip(g, patches)
    plan = union_plan_from_patches(patches, base_color=base, flip_to=flip_to)
    print(
        f"{label} discover: patches={len(patches)} unique_flips={len(plan)} "
        f"base={base} flip_to={flip_to} hist={color_hist(g)}"
    )
    for i, p in enumerate(patches):
        inv = p["fixed_color"] == base and p["fixed_color"] != flip_to
        print(
            f"  patch[{i}] @{p['origin']} fixed={p['fixed_color']} "
            f"polarity={'inverted' if inv else 'normal'} macro={p['macro']}"
        )

    info = {
        "label": label,
        "hist": color_hist(g),
        "patches": patches,
        "plan": plan,
        "base": base,
        "flip_to": flip_to,
        "trajectory": [],
    }
    if not plan:
        raise RuntimeError(f"{label}: no flip plan discovered")

    cur = frame
    lv0 = lv_expect
    for i, step in enumerate(plan, start=1):
        gg = _plane(cur)
        ax, ay = step["ax"], step["ay"]
        patch = gg[ay:ay + BLOCK, ax:ax + BLOCK]
        if patch.size and int(np.median(patch)) == flip_to:
            print(f"  skip already-flipped block @({ax},{ay})")
            continue
        resp = sess.click(step["cx"], step["cy"])
        nf = resp["frame"]
        lv = int(resp.get("levels_completed") or 0)
        summary = summarize_diff(frame_diff(cur, nf))
        print(
            f"  click {i}/{len(plan)} ({step['cx']},{step['cy']}) "
            f"pol={step['polarity']} lv={lv} diff={summary}"
        )
        info["trajectory"].append({
            "step": i,
            "pixel": [step["cx"], step["cy"]],
            "block_origin": [ax, ay],
            "polarity": step["polarity"],
            "levels_completed": lv,
            "diff_summary": summary,
        })
        cur = nf
        if lv > lv0:
            print(f"  >>> {label} LEVEL {lv0} -> {lv}")
            info["cleared"] = True
            info["levels_end"] = lv
            return cur, lv, info

    info["cleared"] = False
    info["levels_end"] = int(
        info["trajectory"][-1]["levels_completed"] if info["trajectory"] else lv0
    )
    return cur, info["levels_end"], info


def analyze_level(frame, label: str) -> dict:
    g = _plane(frame)
    patches = find_instr_patches(g)
    base, flip_to = infer_base_and_flip(g, patches)
    plan = union_plan_from_patches(patches, base_color=base, flip_to=flip_to)
    return {
        "label": label,
        "hist": color_hist(g),
        "n0": int(np.sum(g == 0)),
        "n2": int(np.sum(g == 2)),
        "n8": int(np.sum(g == 8)),
        "n9": int(np.sum(g == 9)),
        "n12": int(np.sum(g == 12)),
        "patches": patches,
        "plan_n": len(plan),
        "base": base,
        "flip_to": flip_to,
        "plan": plan,
    }


def write_report(l3_analysis: dict, clear_info: dict, meta: dict) -> Path:
    cleared = bool(clear_info.get("cleared"))
    lv0 = meta.get("levels_start", 2)
    lv1 = clear_info.get("levels_end", lv0)
    if cleared:
        headline = (
            f"**PASS** — L3 发现 {len(l3_analysis['patches'])} 枚图案，"
            f"极性感知并集 {l3_analysis['plan_n']} 点，`levels` {lv0}→{lv1}。"
            f" base=`{l3_analysis['base']}` flip_to=`{l3_analysis['flip_to']}`；"
            "fixed==flip_to 时 0=翻；fixed==base 时 **2=翻（极性反转）**。"
        )
        verdict = "l3_mask_flip_pass"
    else:
        headline = (
            f"**FAIL** — L3 plan_n={l3_analysis['plan_n']}，levels 仍为 {lv1}。"
        )
        verdict = "l3_mask_flip_fail"

    lines = [
        "# ft09 L3 点击闭环探针",
        "",
        "> 脚本：`tools/ft09_l3_click_flip_probe.py`",
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
        "## L3 新坐实（相对 L1/L2）",
        "",
        "| 项 | L1 | L2 | L3 |",
        "|----|----|----|----|",
        "| base（未翻） | 9 | 9 | **8** |",
        "| flip_to | 8 | 12 | **12** |",
        "| 图案数 | 1（中谜题） | 2（上下） | **4**（十字） |",
        "| 极性 | 恒 0=翻 | 恒 0=翻 | **fixed==base 时反转** |",
        "",
        "## L3 帧摘要",
        "",
        f"- hist: `{l3_analysis['hist']}`",
        f"- base/flip_to = `{l3_analysis['base']}` / `{l3_analysis['flip_to']}`",
        f"- plan_n = `{l3_analysis['plan_n']}`",
        "",
    ]
    for i, p in enumerate(l3_analysis["patches"]):
        inv = p["fixed_color"] == l3_analysis["base"] and p["fixed_color"] != l3_analysis["flip_to"]
        lines.append(
            f"- patch[{i}] origin=`{p['origin']}` fixed=`{p['fixed_color']}` "
            f"polarity=`{'inverted' if inv else 'normal'}` macro=`{p['macro']}`"
        )
    lines += ["", "## 轨迹", ""]
    for step in clear_info.get("trajectory", []):
        lines.append(
            f"- step {step['step']} @{step['pixel']} "
            f"block={step['block_origin']} pol={step.get('polarity')} "
            f"lv={step['levels_completed']} diff={step['diff_summary']}"
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
        sess.open(tags=["ft09_l3_click"])
        lv = clear_l1(sess)
        frame = sess.action("ACTION1")["frame"]
        print(f"synced to L2 lv={lv}")

        frame, lv, l2_info = clear_level_discovered(sess, frame, lv, "L2")
        if not l2_info.get("cleared"):
            raise RuntimeError("L2 clear via discovery failed — abort before L3")
        synced = sess.action("ACTION1")
        frame = synced["frame"]
        meta = {k: synced.get(k) for k in (
            "levels_completed", "state", "available_actions", "win_levels",
        )}
        print(
            f"synced to L3 lv={meta.get('levels_completed')} "
            f"actions={meta.get('available_actions')}"
        )

        l3_analysis = analyze_level(frame, "L3")
        FIXTURE_FRAME.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE_FRAME.write_text(json.dumps({
            "game_id": sess.game_id,
            "meta": meta,
            "frame": np.asarray(_plane(frame)).tolist(),
            "analysis": {
                **{k: v for k, v in l3_analysis.items() if k != "plan"},
                "plan": l3_analysis["plan"],
            },
        }, indent=2), encoding="utf-8")
        print("saved L3 frame", FIXTURE_FRAME)

        frame, lv, l3_clear = clear_level_discovered(
            sess, frame, int(meta.get("levels_completed") or 2), "L3"
        )
        payload = {
            "game_id": sess.game_id,
            "l2_clear": {
                "cleared": l2_info.get("cleared"),
                "levels_end": l2_info.get("levels_end"),
                "base": l2_info.get("base"),
                "flip_to": l2_info.get("flip_to"),
                "trajectory": l2_info.get("trajectory"),
            },
            "l3_levels_start": int(meta.get("levels_completed") or 2),
            "l3_levels_end": l3_clear.get("levels_end"),
            "cleared": l3_clear.get("cleared"),
            "base": l3_analysis.get("base"),
            "flip_to": l3_analysis.get("flip_to"),
            "analysis": {
                **{k: v for k, v in l3_analysis.items() if k != "plan"},
                "plan": l3_analysis["plan"],
            },
            "trajectory": l3_clear.get("trajectory"),
        }
        FIXTURE_TRAJ.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        path = write_report(
            l3_analysis,
            l3_clear,
            {"levels_start": int(meta.get("levels_completed") or 2)},
        )
        print("saved traj", FIXTURE_TRAJ)
        print("report", path)
        return 0 if l3_clear.get("cleared") else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
