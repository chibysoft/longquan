"""Probe: is the second color-12 blob on L3 movable?

CONTEXT (from the L3 arming experiments, docs/ls20_l3_armed_controller.md):
  L3 has TWO color-12 blobs. The main mover is a 5x2 block; a SECOND 2px blob at
  pixel (30,48)-(31,48) sits next to a color-9 blob (30,46)-(30,47) and a color-0
  pixel (31,47) — a "mini mirror" of the main mover's 12-on-top / 9-below
  structure. L2 has NO such second blob.

  The L3 arming question ("what arms L3?") currently blocks on: contact-plus +
  UDD ritual does NOT arm. One new hypothesis is that the arming trigger is the
  SECOND color-12 object, not the plus marker. But "movable" is a TEMPORAL
  property — one frame can't prove it, only two-frame comparison can.

PROBE (minimal, no solver):
  1. reach L3 (clear L1+L2 with the seated planner)
  2. locate the main mover and the second color-12 blob
  3. move the main mover toward the second blob, re-locating BOTH every step
  4. verdict: did the second blob's pixel bbox change? (movable vs static)

Read-only reasoning + minimal online actions. No canned answers; the mover path
is BFS-generated toward the second blob's nearest reachable cell.

Usage:
  python tools/ls20_second_block_probe.py --plan-only    # offline locate + target
  python tools/ls20_second_block_probe.py                # online probe
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import _energy_bfs, _step_cell
from tools.ls20_l3_armed_controller import reach_l3

FIXTURE = ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json"


def all_color12(frame) -> List[Tuple[Tuple[int, int, int, int], int]]:
    """Every playfield color-12 connected component as (bbox, area).

    Unlike ls20.locate_mover (which prefers the 5x2 mover), this returns ALL
    color-12 blobs so we can find the second one. Excludes the bottom UI (y>=54).
    """
    g = ls20._plane(frame)
    H, W = g.shape
    vis = np.zeros_like(g, dtype=bool)
    out: List[Tuple[Tuple[int, int, int, int], int]] = []
    for y in range(H):
        for x in range(W):
            if g[y, x] != ls20.MOVE_COLOR or vis[y, x] or y >= 54:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (0 <= nx < W and 0 <= ny < H and not vis[ny, nx]
                            and g[ny, nx] == ls20.MOVE_COLOR):
                        vis[ny, nx] = True
                        q.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            bb = (min(xs), min(ys), max(xs), max(ys))
            out.append((bb, len(cells)))
    out.sort(key=lambda t: (t[0][0], t[0][1]))
    return out


def main_mover_and_second(frame):
    """Return (main_bbox, [second_blob_bboxes]) by splitting 5x2 vs the rest."""
    main = ls20.locate_mover(frame)
    blobs = all_color12(frame)
    if main is None:
        raise RuntimeError("no main mover (color-12 5x2)")
    others = [b for (b, _n) in blobs if b != main]
    return main, others


def nearest_cell_to_second(walkable, offset, second_bb):
    """Walkable cell whose 5x2 footprint is closest (Euclidean) to second_bb."""
    sx = (second_bb[0] + second_bb[2]) / 2.0
    sy = (second_bb[1] + second_bb[3]) / 2.0
    best = None
    for c in walkable:
        px, py = ls20.cursor_to_pixel(c, offset)
        mx, my = px + 2.0, py + 0.5
        d = (mx - sx) ** 2 + (my - sy) ** 2
        if best is None or d < best[0]:
            best = (d, c)
    return best[1] if best else None


def plan_to_second(frame):
    """Energy-aware BFS path from the mover to the cell nearest the second blob."""
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    main, seconds = main_mover_and_second(frame)
    if not seconds:
        raise RuntimeError("no second color-12 blob on this frame")
    second = seconds[0]
    target = nearest_cell_to_second(walk_u, offset, second)

    ui = ls20.ui_energy(frame)
    fuel0 = ls20.STEPS_LIMIT if ui >= 64 or ui <= 0 else max(1, min(21, (ui - 8) // 4))

    path, _c, _f, _pm = _energy_bfs(
        state.cursor, fuel0, 0, walk_u, pickups, offset,
        lambda cell, _f, _p: cell == target, warps,
    )
    if path is None:
        raise RuntimeError(f"no path to nearest cell {target} of second {second}")
    return path, target, second, main, offset


def probe_online() -> dict:
    key = _api_key()
    if not key:
        raise RuntimeError("no ARC_API_KEY")
    sess = OnlineSession(key)
    try:
        frame, meta = reach_l3(sess)
        print(f"reached L3 levels={meta.get('levels_completed')}")
        path, target, second0, main0, offset = plan_to_second(frame)
        print(f"main={main0} second0={second0} target={target} len={len(path)}")
        print(f"actions={[DIR_TO_ACTION[a] for a in path]}")

        log = [{
            "step": 0, "action": "RESET", "main": main0, "second": second0,
            "layers": 1, "levels": int(meta.get('levels_completed') or 0),
        }]
        second = second0
        for i, a in enumerate(path, 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            main = ls20.locate_mover(frame)
            _, seconds = main_mover_and_second(frame)
            cur_second = seconds[0] if seconds else None
            arr = np.asarray(frame)
            layers = arr.shape[0] if arr.ndim == 3 else 1
            lv = int(meta.get("levels_completed") or 0)
            moved = (cur_second is not None and cur_second != second)
            print(f"  {i:02d} A{DIR_TO_ACTION[a]} main={main} second={cur_second} "
                  f"layers={layers} lv={lv} moved={moved}")
            log.append({
                "step": i, "action": DIR_TO_ACTION[a], "main": main,
                "second": cur_second, "layers": layers, "levels": lv,
                "second_moved": moved,
            })
            if cur_second is not None:
                second = cur_second
        final_second = log[-1]["second"]
        moved_at_all = any(r.get("second_moved") for r in log)
        verdict = (
            "MOVABLE" if moved_at_all
            else "STATIC" if final_second is not None
            else "VANISHED"
        )
        print(f"VERDICT: second blob {verdict} (moved_at_all={moved_at_all})")
        return {
            "verdict": verdict, "moved_at_all": moved_at_all,
            "second0": second0, "second_final": final_second,
            "target": target, "log": log,
        }
    finally:
        sess.close()


def plan_only() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    frame = data["frame"]
    main, seconds = main_mover_and_second(frame)
    print(f"main mover   = {main}")
    print(f"second blobs = {seconds}")
    blobs = all_color12(frame)
    print(f"all color12  = {blobs}")
    path, target, second, main, offset = plan_to_second(frame)
    print(f"nearest cell = {target}  second={second}")
    print(f"path len     = {len(path)}")
    print(f"actions      = {[DIR_TO_ACTION[a] for a in path]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-only", action="store_true")
    args = ap.parse_args()
    if args.plan_only:
        plan_only()
        return 0
    probe_online()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
