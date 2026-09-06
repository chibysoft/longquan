"""ls20 match probe: falsify match/win hypotheses online.

Rounds:
  --round 2  H5 H6 H7 (marker clear / carrying)
  --round 3  H10 H8 H12 H11 (levels+1)   [default]

Hypotheses: docs/ls20-match-hypotheses.md, docs/ls20-match-hypotheses-h8.md
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20, move, search  # noqa: E402
from longquan.interactive.state import Action  # noqa: E402
from tools.ls20_online_validate import (  # noqa: E402
    ACTION_NAME,
    DIR_TO_ACTION,
    OnlineSession,
    _api_key,
)
from tools.ls20_probe_lib import (  # noqa: E402
    fixed_playfield_9,
    nearest_walkable,
    plane,
    playfield_9,
    playfield_color5_blocks,
    snap,
    windows_5x5_paint,
)

REPORT = ROOT / "docs" / "ls20-match-probe-report.md"


@dataclass
class Case:
    name: str
    verdict: str
    detail: str
    logs: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)


def plan_to(state, target):
    found, path = search.bfs(state, move.actions, move.step, lambda s: s.cursor == target)
    if not found:
        raise RuntimeError(f"cannot reach {target}")
    return path


def go(sess, frame, meta, path: List[Action]):
    logs = []
    for i, a in enumerate(path, start=1):
        aid = DIR_TO_ACTION[a]
        resp = sess.action(aid)
        frame, meta = resp["frame"], resp
        logs.append({
            "i": i,
            "a": ACTION_NAME[aid],
            "levels": meta.get("levels_completed"),
            "bbox12": ls20.locate_mover(frame),
        })
    return frame, meta, logs


def do_interact(sess, frame, meta):
    resp = sess.action(5)
    return resp["frame"], resp


def carrying_of(frame):
    return ls20.carrying_near_mover(frame)


# ----- round 2 -----

def case_h5(sess: OnlineSession) -> Case:
    reset = sess.reset()
    frame, meta = reset["frame"], reset
    before = snap(frame, meta)
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    g = plane(frame)
    ys, xs = np.where(np.isin(g, [0, 1]))
    if len(xs) == 0:
        return Case("H5", "INCONCLUSIVE", "no color0/1")
    cx, cy = int(xs.mean()), int(ys.mean())
    target, dist = nearest_walkable(state, offset, cx, cy)
    path = plan_to(state, target)
    frame, meta, logs = go(sess, frame, meta, path)
    mid = snap(frame, meta)
    frame, meta = do_interact(sess, frame, meta)
    after = snap(frame, meta)
    detail = (
        f"target={target} dist={dist} path_len={len(path)} "
        f"n01 {before.n01}->{mid.n01}->{after.n01} levels {before.levels}->{after.levels}"
    )
    v = "SUPPORTED" if after.n01 == 0 and before.n01 > 0 else (
        "REFUTED" if after.n01 > 0 else "INCONCLUSIVE"
    )
    return Case("H5", v, detail, logs)


def case_h6(sess: OnlineSession) -> Case:
    reset = sess.reset()
    frame, meta = reset["frame"], reset
    before = snap(frame, meta)
    from tools.ls20_probe_lib import blob_near_mover
    near0 = blob_near_mover(before.blobs9, before.bbox12)
    if not near0:
        return Case("H6", "INCONCLUSIVE", "no color9 near mover")
    origin = near0[0][1]
    state = ls20.init(frame)
    acts = move.actions(state)
    action = (0, -1) if (0, -1) in acts else acts[0]
    resp = sess.action(DIR_TO_ACTION[action])
    after = snap(resp["frame"], resp)
    near1 = blob_near_mover(after.blobs9, after.bbox12)
    g = plane(resp["frame"])
    ox0, oy0, ox1, oy1 = origin
    still = int(np.count_nonzero(g[oy0:oy1 + 1, ox0:ox1 + 1] == 9))

    def rel(bb12, blob):
        mx = (bb12[0] + bb12[2]) // 2
        my = bb12[3]
        bx = (blob[0] + blob[2]) // 2
        by = (blob[1] + blob[3]) // 2
        return (bx - mx, by - my)

    if not near1:
        return Case("H6", "REFUTED", f"no follow; origin9_left={still}")
    r0, r1 = rel(before.bbox12, near0[0][1]), rel(after.bbox12, near1[0][1])
    drift = abs(r0[0] - r1[0]) + abs(r0[1] - r1[1])
    detail = f"rel_before={r0} rel_after={r1} drift={drift} origin9_left={still}"
    return Case("H6", "SUPPORTED" if drift <= 2 else "REFUTED", detail)


def case_h7(sess: OnlineSession) -> Case:
    reset = sess.reset()
    frame, meta = reset["frame"], reset
    before = snap(frame, meta)
    fixed = fixed_playfield_9(before.blobs9, before.bbox12)
    if not fixed:
        return Case("H7", "INCONCLUSIVE", "no fixed color9")
    mx, my, _, _ = before.bbox12
    fixed.sort(
        key=lambda t: (-t[0], abs((t[1][0] + t[1][2]) // 2 - mx) + abs((t[1][1] + t[1][3]) // 2 - my))
    )
    n, b = fixed[0]
    cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    target, dist = nearest_walkable(state, offset, cx, cy)
    path = plan_to(state, target)
    frame, meta, logs = go(sess, frame, meta, path)
    frame, meta = do_interact(sess, frame, meta)
    after = snap(frame, meta)
    detail = (
        f"fixed n={n} bbox={b} target={target} dist={dist} "
        f"levels {before.levels}->{after.levels} n01 {before.n01}->{after.n01}"
    )
    return Case("H7", "SUPPORTED" if after.levels > before.levels else "REFUTED", detail, logs)


# ----- round 3 -----

def case_h10a(sess: OnlineSession) -> Case:
    reset = sess.reset()
    frame, meta = reset["frame"], reset
    g = plane(frame)
    blocks = playfield_color5_blocks(g)
    wins = windows_5x5_paint(g)
    if not blocks:
        return Case("H10a", "REFUTED", f"no playfield color5; wins={wins[:3]}")
    n, b = blocks[0]
    cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    target, dist = nearest_walkable(state, offset, cx, cy)
    path = plan_to(state, target)
    car0 = carrying_of(frame)
    frame, meta, logs = go(sess, frame, meta, path)
    frame, meta = do_interact(sess, frame, meta)
    lv = int(meta.get("levels_completed") or 0)
    blocks_after = playfield_color5_blocks(plane(frame))
    detail = (
        f"block n={n} bbox={b} target={target} dist={dist} path_len={len(path)} "
        f"carrying={car0} levels={lv} blocks_after={blocks_after} wins={wins[:3]}"
    )
    logs.append({"ACTION5": True, "levels": lv, "carrying": car0})
    return Case("H10a", "SUPPORTED" if lv >= 1 else "REFUTED", detail, logs,
                {"blocks": blocks, "wins": wins[:5]})


def case_h10b(sess: OnlineSession) -> Case:
    reset = sess.reset()
    frame, meta = reset["frame"], reset
    levels0 = int(meta.get("levels_completed") or 0)
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    g = plane(frame)
    ys, xs = np.where(np.isin(g, [0, 1]))
    if len(xs) == 0:
        return Case("H10b", "INCONCLUSIVE", "no color0/1")
    target, _ = nearest_walkable(state, offset, int(xs.mean()), int(ys.mean()))
    path = plan_to(state, target)
    frame, meta, logs = go(sess, frame, meta, path)
    frame, meta = do_interact(sess, frame, meta)
    mid_lv = int(meta.get("levels_completed") or 0)
    n01 = int(np.count_nonzero(np.isin(plane(frame), [0, 1])))
    logs.append({"after_H5": True, "levels": mid_lv, "n01": n01})

    g2 = plane(frame)
    blocks = playfield_color5_blocks(g2)
    wins = windows_5x5_paint(g2)
    cand_pixels = []
    for n, b in blocks:
        cand_pixels.append(("block", n, (b[0] + b[2]) // 2, (b[1] + b[3]) // 2, b))
    for paint, n5, n9, x, y in wins[:5]:
        cand_pixels.append(("win", paint, x + 2, y + 2, (x, y, x + 4, y + 4)))

    tried = []
    seen = set()
    max_lv = mid_lv
    for kind, score, px, py, bbox in cand_pixels:
        state = ls20.init(frame)
        offset = ls20.grid_offset(frame)
        tcell, dist = nearest_walkable(state, offset, px, py)
        if tcell in seen:
            continue
        seen.add(tcell)
        try:
            path = plan_to(state, tcell)
        except RuntimeError as e:
            tried.append({"cand": (kind, bbox), "error": str(e)})
            continue
        car = carrying_of(frame)
        frame, meta, step_logs = go(sess, frame, meta, path)
        frame, meta = do_interact(sess, frame, meta)
        lv = int(meta.get("levels_completed") or 0)
        max_lv = max(max_lv, lv)
        entry = {
            "cand": kind, "bbox": bbox, "target": tcell, "dist": dist,
            "path_len": len(path), "carrying": car, "levels": lv,
        }
        tried.append(entry)
        logs.extend(step_logs)
        logs.append({"ACTION5_on_cand": entry})
        if lv > levels0:
            return Case("H10b", "SUPPORTED", f"levels {levels0}->{lv} via {entry}", logs,
                        {"tried": tried, "blocks": blocks, "wins": wins[:5]})

    only_start = len(blocks) == 1 and blocks[0][1][1] < 20
    detail = (
        f"after_H5 n01={n01} levels={mid_lv} blocks={blocks} wins={wins[:3]} "
        f"tried={len(tried)} max_levels={max_lv} only_start_like={only_start}"
    )
    return Case("H10b", "REFUTED", detail, logs, {"tried": tried, "blocks": blocks})


def case_h8(sess: OnlineSession) -> Case:
    reset = sess.reset()
    frame, meta = reset["frame"], reset
    before = snap(frame, meta)
    fixed = fixed_playfield_9(before.blobs9, before.bbox12)
    if not fixed:
        return Case("H8", "INCONCLUSIVE", "no fixed playfield color9")
    results = []
    levels0 = before.levels
    max_lv = levels0
    for n, b in sorted(fixed, key=lambda t: -t[0]):
        state = ls20.init(frame)
        offset = ls20.grid_offset(frame)
        cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
        target, dist = nearest_walkable(state, offset, cx, cy)
        path = plan_to(state, target)
        car = carrying_of(frame)
        frame, meta, _ = go(sess, frame, meta, path)
        g = plane(frame)
        n9_before = int(np.count_nonzero(g[b[1]:b[3] + 1, b[0]:b[2] + 1] == 9))
        frame, meta = do_interact(sess, frame, meta)
        g2 = plane(frame)
        n9_after = int(np.count_nonzero(g2[b[1]:b[3] + 1, b[0]:b[2] + 1] == 9))
        lv = int(meta.get("levels_completed") or 0)
        max_lv = max(max_lv, lv)
        results.append({
            "blob": (n, b), "target": target, "dist": dist, "path_len": len(path),
            "carrying": car, "n9_in_bbox": f"{n9_before}->{n9_after}", "levels": lv,
        })
        if lv > levels0:
            return Case("H8", "SUPPORTED", f"levels+1 via {results[-1]}", extra={"results": results})
    return Case(
        "H8", "REFUTED",
        f"tried {len(results)} fixed blobs; max_levels={max_lv}; {results}",
        extra={"results": results},
    )


def case_h12(sess: OnlineSession) -> Case:
    reset = sess.reset()
    frame, meta = reset["frame"], reset
    levels0 = int(meta.get("levels_completed") or 0)
    timeline = []
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    g = plane(frame)
    ys, xs = np.where(np.isin(g, [0, 1]))
    if len(xs):
        target, _ = nearest_walkable(state, offset, int(xs.mean()), int(ys.mean()))
        path = plan_to(state, target)
        frame, meta, _ = go(sess, frame, meta, path)
        frame, meta = do_interact(sess, frame, meta)
        timeline.append({
            "op": "clear_01",
            "levels": meta.get("levels_completed"),
            "n01": int(np.count_nonzero(np.isin(plane(frame), [0, 1]))),
            "carrying": carrying_of(frame),
        })

    s = snap(frame, meta)
    fixed = fixed_playfield_9(s.blobs9, s.bbox12)
    for n, b in sorted(fixed, key=lambda t: -t[0]):
        state = ls20.init(frame)
        offset = ls20.grid_offset(frame)
        cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
        target, _ = nearest_walkable(state, offset, cx, cy)
        try:
            path = plan_to(state, target)
        except RuntimeError:
            timeline.append({"op": "skip_blob", "blob": b})
            continue
        frame, meta, _ = go(sess, frame, meta, path)
        frame, meta = do_interact(sess, frame, meta)
        timeline.append({
            "op": "clear_9",
            "blob": b,
            "levels": meta.get("levels_completed"),
            "n9_play": sum(nn for nn, _ in playfield_9(plane(frame))),
            "carrying": carrying_of(frame),
        })

    final = int(meta.get("levels_completed") or 0)
    return Case(
        "H12",
        "SUPPORTED" if final > levels0 else "REFUTED",
        f"timeline={timeline} levels {levels0}->{final}",
        extra={"timeline": timeline},
    )


def case_h11_note(cases: List[Case]) -> Case:
    cars = []
    leveled = False
    for c in cases:
        if c.verdict == "SUPPORTED" and c.name in ("H10a", "H10b", "H8", "H12"):
            leveled = True
        for row in c.logs:
            if isinstance(row, dict) and row.get("carrying") is not None:
                cars.append(row["carrying"])
        for key in ("tried", "results", "timeline"):
            for item in (c.extra or {}).get(key, []) or []:
                if isinstance(item, dict) and item.get("carrying") is not None:
                    cars.append(item["carrying"])
                if isinstance(item, dict) and int(item.get("levels") or 0) >= 1:
                    leveled = True
    uniq = []
    for c in cars:
        if c not in uniq:
            uniq.append(c)
    detail = f"distinct_carrying_seen={uniq}; any_levels_plus={leveled}"
    if len(uniq) <= 1 and not leveled:
        v = "INCONCLUSIVE"
    elif leveled and len(uniq) >= 2:
        v = "INCONCLUSIVE"  # would need controlled contrast to SUPPORT
    else:
        v = "INCONCLUSIVE"
    return Case("H11", v, detail, extra={"carryings": uniq})


def write_report(cases: List[Case], game_id: str, round_id: int) -> Path:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        f"# ls20 match 探路报告（round {round_id}）",
        "",
        f"> 生成时间：{now}",
        f"> game_id=`{game_id}`",
        "",
        "| 假设 | 裁决 | 详情（截断） |",
        "|------|------|-------------|",
    ]
    for c in cases:
        short = c.detail.replace("|", "/").replace("\n", " ")[:160]
        lines.append(f"| {c.name} | **{c.verdict}** | {short} |")

    win_names = ("H10a", "H10b", "H8", "H12", "H13", "H14", "H15", "H16", "H17", "H18")
    win = [c for c in cases if c.verdict == "SUPPORTED" and c.name in win_names]
    lines += ["", "## 通关条件（levels+1）", ""]
    if win:
        lines.append("SUPPORTED: " + ", ".join(c.name for c in win))
        lines.append("→ 可实现 match.done")
    else:
        lines.append("**仍未坐实** — 不实现 done→True。")

    for c in cases:
        lines += ["", f"## {c.name}: **{c.verdict}**", "", c.detail, ""]
        if c.extra:
            lines.append(f"extra: `{c.extra}`")

    lines += ["", "## 纪律", "", "- 色0/1 清除 ≠ 过关", "- 无 levels+1 不写 done", ""]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT


# ----- round 4: H13 H14 H15 -----

def _interest_points(frame) -> list:
    """Auto interest points for ACTION6 (label, x, y)."""
    g = plane(frame)
    pts = []
    ys, xs = np.where(np.isin(g, [0, 1]))
    if len(xs):
        pts.append(("color01", int(xs.mean()), int(ys.mean())))
    blocks = playfield_color5_blocks(g)
    if blocks:
        n, b = blocks[0]
        pts.append(("color5", (b[0] + b[2]) // 2, (b[1] + b[3]) // 2))
    bb12 = ls20.locate_mover(frame)
    if bb12:
        pts.append(("mover", (bb12[0] + bb12[2]) // 2, (bb12[1] + bb12[3]) // 2))
    car = ls20.carrying_near_mover(frame, bb12)
    if car:
        _, b = car
        pts.append(("carrying9", (b[0] + b[2]) // 2, (b[1] + b[3]) // 2))
    return pts


def _non_ui_change(f0, f1) -> tuple:
    """Pixels that changed and are not color 11/12 in either frame. Returns (count, blobs)."""
    a, b = plane(f0), plane(f1)
    changed = a != b
    mask = changed & (a != 11) & (a != 12) & (b != 11) & (b != 12)
    n = int(np.count_nonzero(mask))
    # connected components on mask, label by after-color
    H, W = b.shape
    vis = np.zeros_like(mask, dtype=bool)
    blobs = []
    ys, xs = np.where(mask)
    for y, x in zip(ys.tolist(), xs.tolist()):
        if vis[y, x]:
            continue
        from collections import deque
        q = deque([(x, y)])
        vis[y, x] = True
        cells = []
        while q:
            cx, cy = q.popleft()
            cells.append((cx, cy))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < W and 0 <= ny < H and mask[ny, nx] and not vis[ny, nx]:
                    vis[ny, nx] = True
                    q.append((nx, ny))
        if len(cells) < 3:
            continue
        xs_ = [c[0] for c in cells]
        ys_ = [c[1] for c in cells]
        bbox = (min(xs_), min(ys_), max(xs_), max(ys_))
        # dominant after-color
        colors = [int(b[cy, cx]) for cx, cy in cells]
        dom = max(set(colors), key=colors.count)
        blobs.append((len(cells), dom, bbox))
    blobs.sort(reverse=True)
    return n, blobs


def case_h13(sess: OnlineSession) -> Case:
    """ACTION6 with x,y on interest points => levels+1?"""
    results = []
    tech = {}
    # tech: bare ACTION6 should fail
    reset = sess.reset()
    frame, meta = reset["frame"], reset
    levels0 = int(meta.get("levels_completed") or 0)
    try:
        sess.action(6)
        tech["bare_ACTION6"] = "unexpected_200"
    except Exception as e:
        tech["bare_ACTION6"] = f"failed:{type(e).__name__}"

    # fresh reset for clicks
    reset = sess.reset()
    frame, meta = reset["frame"], reset
    levels0 = int(meta.get("levels_completed") or 0)
    pts = _interest_points(frame)
    # remember 01 center for post-H5 click
    pt01 = next((p for p in pts if p[0] == "color01"), None)

    max_lv = levels0
    side_effect = False
    for label, x, y in pts:
        f_before = frame
        lv_before = int(meta.get("levels_completed") or 0)
        try:
            resp = sess.action(6, x=x, y=y)
            frame, meta = resp["frame"], resp
            ok = True
            err = None
        except Exception as e:
            ok, err = False, str(e)
            results.append({"pt": (label, x, y), "ok": False, "err": err})
            continue
        lv = int(meta.get("levels_completed") or 0)
        max_lv = max(max_lv, lv)
        ch, blobs = _non_ui_change(f_before, frame)
        if ch >= 5:
            side_effect = True
        results.append({
            "pt": (label, x, y), "ok": ok, "levels": lv,
            "changed_non_ui": ch, "diff_blobs": blobs[:5],
        })
        if lv > levels0:
            return Case(
                "H13", "SUPPORTED",
                f"levels {levels0}->{lv} click {label}@({x},{y})",
                extra={"results": results, "tech": tech},
            )

    # after H5, click former 01 center again
    if pt01:
        reset = sess.reset()
        frame, meta = reset["frame"], reset
        state = ls20.init(frame)
        offset = ls20.grid_offset(frame)
        _, x01, y01 = pt01
        target, _ = nearest_walkable(state, offset, x01, y01)
        path = plan_to(state, target)
        frame, meta, _ = go(sess, frame, meta, path)
        frame, meta = do_interact(sess, frame, meta)
        f_before = frame
        try:
            resp = sess.action(6, x=x01, y=y01)
            frame, meta = resp["frame"], resp
            lv = int(meta.get("levels_completed") or 0)
            max_lv = max(max_lv, lv)
            ch, blobs = _non_ui_change(f_before, frame)
            if ch >= 5:
                side_effect = True
            results.append({
                "pt": ("postH5_color01", x01, y01), "ok": True, "levels": lv,
                "changed_non_ui": ch, "diff_blobs": blobs[:5],
            })
            if lv > levels0:
                return Case(
                    "H13", "SUPPORTED",
                    f"post-H5 click levels->{lv}",
                    extra={"results": results, "tech": tech},
                )
        except Exception as e:
            results.append({"pt": ("postH5_color01", x01, y01), "ok": False, "err": str(e)})

    detail = (
        f"tech={tech} max_levels={max_lv} side_effect={side_effect} "
        f"n_clicks={len(results)} results={results}"
    )
    # overgate branch
    if max_lv > levels0:
        v = "SUPPORTED"
    else:
        v = "REFUTED"
    # annotate weak side effect in detail only
    return Case("H13", v, detail, extra={"results": results, "tech": tech, "side_effect": side_effect})


def case_h14(sess: OnlineSession) -> Case:
    """Enumerate available_actions at RESET and near color0/1."""
    timeline = []
    levels0 = None
    max_lv = 0

    def try_each(frame, meta, tag: str):
        nonlocal max_lv
        legal = list(meta.get("available_actions") or [])
        # normalize to ints
        legal = [int(a) for a in legal]
        rows = []
        for aid in legal:
            f0 = frame
            lv0 = int(meta.get("levels_completed") or 0)
            try:
                if aid == 6:
                    bb = ls20.locate_mover(frame)
                    if bb is None:
                        rows.append({"action": aid, "skip": "no mover"})
                        continue
                    x = (bb[0] + bb[2]) // 2
                    y = (bb[1] + bb[3]) // 2
                    resp = sess.action(aid, x=x, y=y)
                else:
                    resp = sess.action(aid)
                frame, meta = resp["frame"], resp
                lv = int(meta.get("levels_completed") or 0)
                max_lv = max(max_lv, lv)
                ch, blobs = _non_ui_change(f0, frame)
                rows.append({
                    "action": aid, "levels": lv, "delta_levels": lv - lv0,
                    "changed_non_ui": ch, "diff_blobs": blobs[:3],
                    "available_after": meta.get("available_actions"),
                })
                if lv > lv0 and levels0 is not None and lv > levels0:
                    return frame, meta, rows, True
            except Exception as e:
                rows.append({"action": aid, "err": str(e)[:120]})
        return frame, meta, rows, False

    # pass 1: at RESET
    reset = sess.reset()
    frame, meta = reset["frame"], reset
    levels0 = int(meta.get("levels_completed") or 0)
    max_lv = levels0
    legal0 = list(meta.get("available_actions") or [])
    frame, meta, rows, won = try_each(frame, meta, "reset")
    timeline.append({"phase": "at_RESET", "available": legal0, "rows": rows})
    if won:
        return Case("H14", "SUPPORTED", f"win in RESET enum; {timeline}", extra={"timeline": timeline})

    # pass 2: near color0/1
    reset = sess.reset()
    frame, meta = reset["frame"], reset
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    g = plane(frame)
    ys, xs = np.where(np.isin(g, [0, 1]))
    if len(xs):
        target, _ = nearest_walkable(state, offset, int(xs.mean()), int(ys.mean()))
        path = plan_to(state, target)
        frame, meta, _ = go(sess, frame, meta, path)
        legal1 = list(meta.get("available_actions") or [])
        frame, meta, rows, won = try_each(frame, meta, "near01")
        timeline.append({"phase": "near_color01", "available": legal1, "rows": rows})
        if won:
            return Case("H14", "SUPPORTED", f"win near01 enum; {timeline}", extra={"timeline": timeline})
    else:
        timeline.append({"phase": "near_color01", "skip": "no color01"})

    detail = f"available_at_reset={legal0} max_levels={max_lv} timeline={timeline}"
    return Case(
        "H14",
        "SUPPORTED" if max_lv > levels0 else "REFUTED",
        detail,
        extra={"timeline": timeline},
    )


def case_h15(sess: OnlineSession) -> Case:
    """Post-interaction frame diff -> new blobs -> ACTION5/6."""
    trials = []

    def run_sequence(tag: str, build_path):
        reset = sess.reset()
        frame, meta = reset["frame"], reset
        f0 = frame
        levels0 = int(meta.get("levels_completed") or 0)
        state = ls20.init(frame)
        offset = ls20.grid_offset(frame)
        target = build_path(frame, state, offset)
        if target is None:
            trials.append({"tag": tag, "skip": "no target"})
            return None
        path = plan_to(state, target)
        frame, meta, _ = go(sess, frame, meta, path)
        frame, meta = do_interact(sess, frame, meta)
        f1 = frame
        ch, blobs = _non_ui_change(f0, f1)
        entry = {
            "tag": tag, "levels_after_seq": meta.get("levels_completed"),
            "changed_non_ui": ch, "new_blobs": blobs[:8],
        }
        if int(meta.get("levels_completed") or 0) > levels0:
            entry["won"] = True
            trials.append(entry)
            return Case("H15", "SUPPORTED", f"levels+1 during seq {tag}", extra={"trials": trials})

        # interact with each new blob
        for n, dom, bbox in blobs[:6]:
            state = ls20.init(frame)
            offset = ls20.grid_offset(frame)
            cx, cy = (bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2
            tcell, dist = nearest_walkable(state, offset, cx, cy)
            try:
                path = plan_to(state, tcell)
            except RuntimeError:
                entry.setdefault("blob_tries", []).append({"bbox": bbox, "err": "unreachable"})
                continue
            frame, meta, _ = go(sess, frame, meta, path)
            # ACTION5
            frame, meta = do_interact(sess, frame, meta)
            lv = int(meta.get("levels_completed") or 0)
            row = {"bbox": bbox, "dom": dom, "n": n, "via": "ACTION5", "levels": lv}
            # ACTION6 on center
            try:
                resp = sess.action(6, x=cx, y=cy)
                frame, meta = resp["frame"], resp
                lv = int(meta.get("levels_completed") or 0)
                row["via6_levels"] = lv
            except Exception as e:
                row["via6_err"] = str(e)[:80]
            entry.setdefault("blob_tries", []).append(row)
            if lv > levels0:
                trials.append(entry)
                return Case(
                    "H15", "SUPPORTED",
                    f"levels+1 on blob {bbox} after {tag}",
                    extra={"trials": trials},
                )
        trials.append(entry)
        return None

    def target_01(frame, state, offset):
        g = plane(frame)
        ys, xs = np.where(np.isin(g, [0, 1]))
        if not len(xs):
            return None
        t, _ = nearest_walkable(state, offset, int(xs.mean()), int(ys.mean()))
        return t

    def target_c5(frame, state, offset):
        blocks = playfield_color5_blocks(plane(frame))
        if not blocks:
            return None
        b = blocks[0][1]
        t, _ = nearest_walkable(state, offset, (b[0] + b[2]) // 2, (b[1] + b[3]) // 2)
        return t

    for tag, builder in (("seq_H5_on_01", target_01), ("seq_ACTION5_on_color5", target_c5)):
        won = run_sequence(tag, builder)
        if isinstance(won, Case):
            return won

    # summarize
    any_blobs = any(t.get("new_blobs") for t in trials if isinstance(t, dict))
    detail = f"any_new_blobs={any_blobs} trials={trials}"
    if not any_blobs:
        v = "REFUTED"
    else:
        # had blobs but no levels+1
        v = "REFUTED"
    return Case("H15", v, detail, extra={"trials": trials})


def case_h16(sess: OnlineSession) -> Case:
    """From color5-neighbor walkable, one more UP into color9 zone => levels+1?"""
    reset = sess.reset()
    frame, meta = reset["frame"], reset
    levels0 = int(meta.get("levels_completed") or 0)
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    blocks = playfield_color5_blocks(plane(frame))
    if not blocks:
        return Case("H16", "INCONCLUSIVE", "no playfield color5")
    b = blocks[0][1]
    cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
    gate, dist = nearest_walkable(state, offset, cx, cy)
    path = plan_to(state, gate)
    frame, meta, logs = go(sess, frame, meta, path)
    before = snap(frame, meta)
    bb_before = before.bbox12
    # one UP
    resp = sess.action(1)
    frame, meta = resp["frame"], resp
    after = snap(frame, meta)
    lv = after.levels
    moved = bb_before is not None and after.bbox12 is not None and after.bbox12[1] < bb_before[1]
    n9_before = before.blobs9  # playfield list
    # count color9 inside start-shape bbox
    g0 = plane(reset["frame"])  # not right - use frame before UP
    # re-get: we need frame before UP — reconstruct from before state approx via logs
    # simpler: compare n9 total in start-shape bbox on after vs fixture start shape
    g1 = plane(frame)
    n9_in_shape = int(np.count_nonzero(g1[b[1]:b[3] + 1, b[0]:b[2] + 1] == 9))
    detail = (
        f"gate={gate} dist={dist} path_len={len(path)} "
        f"bbox12 {bb_before}->{after.bbox12} moved_up={moved} "
        f"levels {levels0}->{lv} n9_in_shape_after={n9_in_shape} "
        f"n01 {before.n01}->{after.n01}"
    )
    logs.append({"ACTION1": True, "levels": lv, "bbox12": after.bbox12})
    if lv > levels0:
        return Case("H16", "SUPPORTED", detail, logs, {
            "gate": gate, "moved_up": moved, "bbox_after": after.bbox12,
        })
    if not moved:
        return Case("H16", "REFUTED", detail + " (blocked; walkable model matches engine)", logs)
    return Case("H16", "REFUTED", detail + " (entered but no level-up)", logs)


def case_h17(sess: OnlineSession) -> Case:
    """Rebuild walkable with obstacles={4} only; path to max overlap with color5 block."""
    reset = sess.reset()
    frame, meta = reset["frame"], reset
    levels0 = int(meta.get("levels_completed") or 0)
    g = plane(frame)
    offset = ls20.grid_offset(frame)
    ox, oy = offset
    blocks = playfield_color5_blocks(g)
    if not blocks:
        return Case("H17", "INCONCLUSIVE", "no color5 block")
    shape = blocks[0][1]

    # build walkable ignoring color9
    walkable = set()
    H, W = g.shape
    mw, mh = ls20.MOVE_SHAPE
    for cx in range(-1, (W + ls20.STEP) // ls20.STEP + 1):
        for cy in range(-1, (H + ls20.STEP) // ls20.STEP + 1):
            px, py = ox + ls20.STEP * cx, oy + ls20.STEP * cy
            if px < 0 or py < 0 or px + mw > W or py + mh > H:
                continue
            fp = g[py:py + mh, px:px + mw]
            if not np.any(fp == 4):  # only walls
                walkable.add((cx, cy))

    start = ls20.init(frame).cursor
    # score by overlap of predicted mover bbox with shape
    def overlap(cell):
        px, py = ls20.cursor_to_pixel(cell, offset)
        bb = (px, py, px + 4, py + 1)
        ox0 = max(bb[0], shape[0])
        oy0 = max(bb[1], shape[1])
        ox1 = min(bb[2], shape[2])
        oy1 = min(bb[3], shape[3])
        if ox0 <= ox1 and oy0 <= oy1:
            return (ox1 - ox0 + 1) * (oy1 - oy0 + 1)
        return 0

    candidates = [(overlap(c), c) for c in walkable if overlap(c) > 0]
    if not candidates:
        return Case("H17", "INCONCLUSIVE", f"no overlap cells; walkable_n={len(walkable)}")
    candidates.sort(key=lambda t: (-t[0], t[1][0], t[1][1]))
    target = candidates[0][1]
    ov = candidates[0][0]

    # BFS on custom walkable
    from collections import deque
    from longquan.interactive.state import WorldState
    st = WorldState(
        grid_w=W, grid_h=H, cursor=start, walkable=frozenset(walkable),
        steps_limit=ls20.STEPS_LIMIT,
    )

    def acts(s):
        out = []
        cx, cy = s.cursor
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            if (cx + dx, cy + dy) in s.walkable:
                out.append((dx, dy))
        return out

    found, path = search.bfs(st, acts, move.step, lambda s: s.cursor == target)
    if not found:
        return Case("H17", "REFUTED", f"BFS failed to overlap target={target} ov={ov}")

    frame, meta, logs = go(sess, frame, meta, path)
    lv = int(meta.get("levels_completed") or 0)
    bb = ls20.locate_mover(frame)
    g2 = plane(frame)
    n9_shape = int(np.count_nonzero(g2[shape[1]:shape[3] + 1, shape[0]:shape[2] + 1] == 9))
    detail = (
        f"target={target} overlap={ov} path_len={len(path)} "
        f"end_bbox={bb} levels {levels0}->{lv} n9_in_shape={n9_shape} "
        f"path_actions={[DIR_TO_ACTION[a] for a in path]}"
    )
    v = "SUPPORTED" if lv > levels0 else "REFUTED"
    return Case("H17", v, detail, logs, {
        "target": target, "overlap": ov, "path": [DIR_TO_ACTION[a] for a in path],
        "n9_in_shape": n9_shape,
    })


def case_h18(sess: OnlineSession, prior: list) -> Case:
    """If H16/H17 supported, check stamp signature: levels+1 + color9 drop in shape."""
    winners = [c for c in prior if c.name in ("H16", "H17") and c.verdict == "SUPPORTED"]
    if not winners:
        return Case("H18", "INCONCLUSIVE", "no prior level-up to inspect signature")
    # Re-run the winning procedure once and measure n9 in shape before/after last step
    # Prefer H17 path if present else H16
    w = next((c for c in winners if c.name == "H17"), winners[0])
    reset = sess.reset()
    frame, meta = reset["frame"], reset
    g0 = plane(frame)
    blocks = playfield_color5_blocks(g0)
    shape = blocks[0][1]
    n9_before = int(np.count_nonzero(g0[shape[1]:shape[3] + 1, shape[0]:shape[2] + 1] == 9))
    levels0 = int(meta.get("levels_completed") or 0)

    if w.name == "H17" and w.extra.get("path"):
        # replay action ids
        for aid in w.extra["path"]:
            resp = sess.action(aid)
            frame, meta = resp["frame"], resp
    else:
        # H16 style
        state = ls20.init(frame)
        offset = ls20.grid_offset(frame)
        cx = (shape[0] + shape[2]) // 2
        cy = (shape[1] + shape[3]) // 2
        gate, _ = nearest_walkable(state, offset, cx, cy)
        path = plan_to(state, gate)
        frame, meta, _ = go(sess, frame, meta, path)
        resp = sess.action(1)
        frame, meta = resp["frame"], resp

    g1 = plane(frame)
    n9_after = int(np.count_nonzero(g1[shape[1]:shape[3] + 1, shape[0]:shape[2] + 1] == 9))
    lv = int(meta.get("levels_completed") or 0)
    detail = (
        f"via={w.name} levels {levels0}->{lv} n9_in_shape {n9_before}->{n9_after} "
        f"bbox12={ls20.locate_mover(frame)}"
    )
    if lv > levels0 and n9_after < n9_before:
        return Case("H18", "SUPPORTED", detail)
    if lv > levels0:
        return Case("H18", "REFUTED", detail + " (leveled but n9 did not drop)")
    return Case("H18", "INCONCLUSIVE", detail + " (no level-up on replay)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, default=5, choices=[2, 3, 4, 5])
    args = ap.parse_args()
    key = _api_key()
    if not key:
        print("no API key", file=sys.stderr)
        return 2
    sess = OnlineSession(key)
    cases: List[Case] = []
    try:
        sess.open(tags=[f"ls20_match_r{args.round}"])
        print("game", sess.game_id, "round", args.round)
        if args.round == 2:
            fns = (case_h5, case_h6, case_h7)
        elif args.round == 3:
            fns = (case_h10a, case_h10b, case_h8, case_h12)
        elif args.round == 4:
            fns = (case_h13, case_h14, case_h15)
        else:
            fns = (case_h16, case_h17)
        for fn in fns:
            print(f"\n=== {fn.__name__} ===")
            c = fn(sess)
            cases.append(c)
            print(f"  {c.name}: {c.verdict}")
            print(f"  {c.detail[:360]}")
        if args.round == 3:
            h11 = case_h11_note(cases)
            cases.append(h11)
            cases.append(Case("H9", "DEFERRED", "no multi-clear success to motivate order search"))
            print(f"\n=== H11 ===\n  {h11.verdict}\n  {h11.detail}")
        if args.round == 5:
            h18 = case_h18(sess, cases)
            cases.append(h18)
            print(f"\n=== H18 ===\n  {h18.verdict}\n  {h18.detail}")
    finally:
        sess.close()
    path = write_report(cases, sess.game_id or "", args.round)
    print("\nreport", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
