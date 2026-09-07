"""L4 H5/H6 probe: skip ring-unlock; try alternate arming; calibrate (7,5).

Variants (each full climb L1-L3 -> L4 start):
  h6     - stand at (7,5), pulse L/R/D (UP already known -> (7,1))
  bare   - armed BFS to stamp, no prep (control)
  c0     - walk to carrying-overlap color0 cell, no ritual, then armed stamp
  warp84 - enter vertical portal (8,4)+DOWN, snapshot, then armed stamp
  legend - visit mover-overlap color14 cell (bottom), then armed stamp

Pass: levels_completed 3 -> 4.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import carrying_bbox_from_cursor, mover_bbox_from_cursor
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import _energy_bfs, _step_cell
from tools.ls20_l4_arming_probe import (
    _climb_to_l4,
    _fuel0,
    _gate_walk,
    _plan_armed_stamp_only,
    _plan_to_pickup,
)

REPORT = ROOT / "docs" / "ls20_l4_h5_arming_probe.md"


def _walk_to(frame, target, *, armed: bool = False):
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk = ls20.build_walkable(frame, offset, armed=armed)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    p, c, f, pm = _energy_bfs(
        state.cursor, _fuel0(frame), 0, walk, pickups, offset,
        lambda cell, _f, _p: cell == target, warps,
    )
    return p, c


def _c0_contact_cell(frame):
    g = ls20._plane(frame)
    offset = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, offset, armed=False)
    hits = []
    for cell in sorted(wu):
        cb = carrying_bbox_from_cursor(cell, offset)
        x0, y0, x1, y1 = cb
        if np.any(g[y0 : y1 + 1, x0 : x1 + 1] == 0):
            hits.append(cell)
    return hits


def _c14_cells(frame):
    g = ls20._plane(frame)
    offset = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, offset, armed=False)
    hits = []
    for cell in sorted(wu):
        mb = mover_bbox_from_cursor(cell, offset)
        x0, y0, x1, y1 = mb
        if np.any(g[y0 : y1 + 1, x0 : x1 + 1] == 14):
            hits.append(cell)
    return hits


def _exec_path(sess, frame, meta, path, log, tag):
    lv = int(meta.get("levels_completed") or 0)
    for i, a in enumerate(path, 1):
        resp = sess.action(DIR_TO_ACTION[a])
        frame, meta = resp["frame"], resp
        nl = int(meta.get("levels_completed") or 0)
        log.append({
            "tag": tag, "step": i, "action": DIR_TO_ACTION[a],
            "cursor": ls20.init(frame).cursor,
            "mover": ls20.locate_mover(frame),
            "levels": nl, "ui": ls20.ui_energy(frame),
        })
        if nl > lv:
            return frame, meta, True
    return frame, meta, False


def _try_stamp(sess, frame, meta, log, tag):
    path, dest, fuel, info = _plan_armed_stamp_only(frame)
    log.append({"tag": f"{tag}_plan", "ok": path is not None, "info": info,
                "snap": _gate_walk(frame)})
    if path is None:
        return frame, meta, False
    print(f"  stamp plan len={len(path)} -> {dest}")
    return _exec_path(sess, frame, meta, path, log, f"{tag}_stamp")


def variant_h6(sess, frame, meta, log):
    """Calibrate (7,5) L/R/D; re-approach after each pulse (UP already known)."""
    p_pu, _ = _plan_to_pickup(frame)
    if p_pu:
        frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")

    for d in ((-1, 0), (1, 0), (0, 1)):  # L, R, D
        p, _ = _walk_to(frame, (7, 4))
        if p is None:
            log.append({"tag": "h6", "verdict": "UNREACHABLE_74", "dir": d})
            return frame, meta, "H6_UNREACHABLE_74"
        if p:
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to_74")
        # ensure at 7,4
        if ls20.init(frame).cursor != (7, 4):
            log.append({"tag": "h6_miss_74", "cursor": ls20.init(frame).cursor, "dir": d})
            # still try DOWN if nearby
        frame, meta, _ = _exec_path(sess, frame, meta, [(0, 1)], log, "to_75")
        before = ls20.init(frame).cursor
        if before != (7, 5):
            log.append({"tag": "h6_not_75", "cursor": before, "dir": d})
            return frame, meta, "H6_NOT_AT_75"
        off = ls20.grid_offset(frame)
        wu = ls20.build_walkable(frame, off, armed=False)
        model = _step_cell(before, d, wu, ls20.detect_warps(frame, off, wu))
        resp = sess.action(DIR_TO_ACTION[d])
        frame, meta = resp["frame"], resp
        after = ls20.init(frame).cursor
        row = {
            "tag": "h6_pulse", "dir": d, "before": before,
            "model": model, "after": after, "match": model == after,
            "mover": ls20.locate_mover(frame),
        }
        log.append(row)
        print(f"  h6 {d}: {before} model={model} after={after}")
    return frame, meta, "H6_DONE"


def variant_bare(sess, frame, meta, log):
    frame, meta, ok = _try_stamp(sess, frame, meta, log, "bare")
    return frame, meta, "H5_BARE_PASS" if ok else "H5_BARE_FAIL"


def variant_c0(sess, frame, meta, log):
    p_pu, _ = _plan_to_pickup(frame)
    if p_pu:
        frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
    hits = _c0_contact_cell(frame)
    log.append({"tag": "c0_hits", "hits": hits})
    if not hits:
        return frame, meta, "H5_C0_NO_HIT"
    p, _ = _walk_to(frame, hits[0])
    if p is None:
        return frame, meta, "H5_C0_UNREACHABLE"
    frame, meta, cleared = _exec_path(sess, frame, meta, p, log, "to_c0")
    if cleared:
        return frame, meta, "H5_C0_PASS_ON_CONTACT"
    log.append({"tag": "c0_contact", "cursor": ls20.init(frame).cursor,
                "snap": _gate_walk(frame)})
    frame, meta, ok = _try_stamp(sess, frame, meta, log, "c0")
    return frame, meta, "H5_C0_PASS" if ok else "H5_C0_FAIL"


def variant_warp84(sess, frame, meta, log):
    p_pu, _ = _plan_to_pickup(frame)
    if p_pu:
        frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
    p, _ = _walk_to(frame, (8, 4))
    if p is None:
        return frame, meta, "H5_WARP84_UNREACHABLE"
    frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to_84")
    # fire DOWN through vertical portal
    before = ls20.init(frame).cursor
    frame, meta, _ = _exec_path(sess, frame, meta, [(0, 1)], log, "warp_down")
    after = ls20.init(frame).cursor
    log.append({"tag": "warp84_land", "before": before, "after": after,
                "snap": _gate_walk(frame),
                "c9": int((ls20._plane(frame) == 9).sum()),
                "c14": int((ls20._plane(frame) == 14).sum())})
    print(f"  warp84 {before}+DOWN -> {after}")
    frame, meta, ok = _try_stamp(sess, frame, meta, log, "warp84")
    return frame, meta, "H5_WARP84_PASS" if ok else "H5_WARP84_FAIL"


def variant_legend(sess, frame, meta, log):
    p_pu, _ = _plan_to_pickup(frame)
    if p_pu:
        frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
    hits = _c14_cells(frame)
    log.append({"tag": "c14_hits", "hits": hits})
    if not hits:
        return frame, meta, "H5_LEGEND_NO_HIT"
    p, _ = _walk_to(frame, hits[0])
    if p is None:
        return frame, meta, "H5_LEGEND_UNREACHABLE"
    frame, meta, cleared = _exec_path(sess, frame, meta, p, log, "to_legend")
    if cleared:
        return frame, meta, "H5_LEGEND_PASS_ON_TOUCH"
    log.append({"tag": "legend_touch", "cursor": ls20.init(frame).cursor,
                "snap": _gate_walk(frame),
                "c9": int((ls20._plane(frame) == 9).sum()),
                "c14": int((ls20._plane(frame) == 14).sum())})
    frame, meta, ok = _try_stamp(sess, frame, meta, log, "legend")
    return frame, meta, "H5_LEGEND_PASS" if ok else "H5_LEGEND_FAIL"


VARIANTS = {
    "h6": variant_h6,
    "bare": variant_bare,
    "c0": variant_c0,
    "warp84": variant_warp84,
    "legend": variant_legend,
}


def run_one(variant: str) -> dict:
    fn = VARIANTS[variant]
    key = _api_key()
    if not key:
        raise RuntimeError("no ARC_API_KEY")
    sess = OnlineSession(key)
    log = []
    try:
        sess.open(tags=[f"ls20_l4_h5_{variant}"])
        frame, meta = _climb_to_l4(sess)
        log.append({"tag": "l4_start", "levels": int(meta.get("levels_completed") or 0),
                    "snap": _gate_walk(frame), "mover": ls20.locate_mover(frame)})
        print(f"=== variant={variant} lv={log[-1]['levels']} ===")
        frame, meta, verdict = fn(sess, frame, meta, log)
        log.append({"tag": "RESULT", "verdict": verdict,
                    "levels": int(meta.get("levels_completed") or 0),
                    "snap": _gate_walk(frame)})
        print(f"verdict={verdict}")
        return {"variant": variant, "verdict": verdict, "log": log}
    finally:
        sess.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=list(VARIANTS) + ["all"], default="all")
    args = ap.parse_args()
    variants = list(VARIANTS) if args.variant == "all" else [args.variant]
    # Prefer order: h6 first (cheap info), then arming attempts
    if args.variant == "all":
        variants = ["h6", "c0", "warp84", "legend", "bare"]
    results = []
    for v in variants:
        results.append(run_one(v))
        if results[-1]["verdict"].endswith("_PASS") or "PASS" in results[-1]["verdict"]:
            break
    lines = ["# ls20 L4 H5/H6 probe", ""]
    for r in results:
        lines.append(f"## variant `{r['variant']}` → **{r['verdict']}**")
        lines.append("")
        for row in r["log"]:
            lines.append(f"- `{row}`")
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {REPORT}")
    return 0 if any("PASS" in r["verdict"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
