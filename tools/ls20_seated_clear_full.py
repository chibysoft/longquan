"""ls20 closed-book solver: L1-L3 with a GENERIC unlock rule (no canned table).

WHY THIS IS A SOLVER (not a probe)
  ls20_seated_clear.py stops at L2 because L3's stamp gate (10,10) is
  armed-only AND blocked by a color9 glyph until a level-specific "unlock
  object" is entered. E10b (probe) proved the mechanism: crushing the ring at
  (5,9) flips the legend and opens the gate, after which the ordinary
  contact + ritual + armed walk clears L3.

  This file ENCODES THE GENERAL RULE, not the coordinates:

    unlock object := an armed-only cell (mover footprint contains color9) that
                     is NOT the stamp gate (footprint does not overlap the
                     stamp) and is NOT bottom-palette chrome (y_px < 54).

  L1/L2 have NO such cell (their only non-gate armed-only cells are bottom
  palette at y>=54), so the rule is a no-op and the plain two-phase flow runs.
  L3 has exactly one ((5,9)), so the solver crushes it, then re-runs the plain
  flow. The rule derives from the frame alone — no "level N -> action seq"
  table, no hardcoded coordinates.

  Pass criterion is ONLY levels_completed increment (red line 3).

FLOW (per level)
  1. plan_two_phase (contact -> ritual -> armed walk to stamp gate)
  2. if no unlock candidates remain, done
  3. else enter each unlock candidate (armed), then retry two-phase

USAGE
  python tools/ls20_seated_clear_full.py --max-levels 3
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
from longquan.interactive.match import mover_bbox_from_cursor
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import (
    MAX_FUEL, _energy_bfs, _ov, _ov_stamp, _step_cell, plan_two_phase,
)

REPORT = ROOT / "docs" / "ls20-seated-clear-full-report.md"

# A cell whose footprint reaches (py < 54) is playfield; >=54 is bottom palette.
PALETTE_Y = 54


def _unlock_candidates(frame):
    """Armed-only non-gate playfield cells = candidate unlock objects.

    Armed-only = in walk_a but not walk_u (footprint contains color9, no color4).
    Non-gate = footprint does not overlap the stamp. Playfield = top pixel y<54.
    """
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    stamp = next((g.shape for g in state.goals if g.id == "ls20-stamp"), None)
    out = []
    for c in sorted(walk_a - walk_u):
        if stamp is not None and _ov(mover_bbox_from_cursor(c, offset), stamp) > 0:
            continue
        px, py = ls20.cursor_to_pixel(c, offset)
        if py >= PALETTE_Y:
            continue
        out.append(c)
    return out


def _plan_to_unlock(frame, target):
    """Energy-aware ARMED path to an unlock cell (mover enters color9 cell)."""
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    warps = ls20.detect_warps(frame, offset,
                              ls20.build_walkable(frame, offset, armed=False))
    pickups = ls20.energy_pickups(frame)
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))
    p, c, f, pm = _energy_bfs(
        state.cursor, fuel0, 0, walk_a, pickups, offset,
        lambda cell, _f, _p: cell == target, warps,
    )
    return p, c, f


def _plan_to_pickup(frame):
    """Energy-aware path to ANY pickup (refill before an energy-hungry unlock)."""
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))

    def at_pickup(cell, _f, _p):
        return any(_ov(mover_bbox_from_cursor(cell, offset), pb) > 0
                   for pb in pickups)

    p, c, f, pm = _energy_bfs(state.cursor, fuel0, 0, walk_u, pickups, offset,
                              at_pickup, warps)
    return p, c


def _sync_after_levelup(sess, frame):
    """Stale-frame fix: one no-op action after level-up yields the true frame."""
    resp = sess.action(1)
    return resp["frame"], resp


def run_online(max_levels: int = 7) -> dict:
    key = _api_key()
    if not key:
        raise RuntimeError("ARC_API_KEY not found")
    sess = OnlineSession(key)
    log = []
    try:
        sess.open(tags=["ls20_seated_full"])
        reset = sess.reset()
        frame, meta = reset["frame"], reset
        win_levels = int(meta.get("win_levels") or max_levels)
        print(f"start lv={meta.get('levels_completed')} win_levels={win_levels} "
              f"mover={ls20.locate_mover(frame)}")

        while True:
            lv = int(meta.get("levels_completed") or 0)
            if meta.get("state") == "WIN" or lv >= win_levels or lv >= max_levels:
                log.append({"event": "done", "levels": lv, "state": meta.get("state")})
                break

            # --- unlock-first: refuel, then clear every non-gate armed-only cell ---
            unlocked_any = False
            cands = _unlock_candidates(frame)
            if cands:
                p_pu, _ = _plan_to_pickup(frame)
                if p_pu is not None:
                    print(f"  unlock pre-fuel: eat pickup ({len(p_pu)} steps)")
                    for a in p_pu:
                        resp = sess.action(DIR_TO_ACTION[a])
                        frame, meta = resp["frame"], resp
            for cand in cands:
                p, _, _ = _plan_to_unlock(frame, cand)
                if p is None:
                    log.append({"event": "unlock_unreachable", "levels": lv,
                                "cell": cand})
                    print(f"  unlock {cand} unreachable (skip)")
                    continue
                print(f"  unlock: enter {cand} ({len(p)} armed steps)")
                for a in p:
                    resp = sess.action(DIR_TO_ACTION[a])
                    frame, meta = resp["frame"], resp
                unlocked_any = True
                log.append({"event": "unlock", "levels": lv, "cell": cand,
                            "mover": ls20.locate_mover(frame),
                            "c9": int((ls20._plane(frame) == 9).sum()),
                            "c12": int((ls20._plane(frame) == 12).sum())})

            # --- then the ordinary two-phase flow ---
            try:
                path, info = plan_two_phase(frame)
            except Exception as e:
                log.append({"event": "plan_fail", "levels": lv, "error": str(e)})
                print(f"PLAN FAIL at lv={lv}: {e}")
                break
            print(f"\n=== clear level index {lv} === len={len(path)} "
                  f"ritual={info.get('ritual')} pickups={info['pickups']} "
                  f"unlocked_any={unlocked_any}")
            print("actions", [DIR_TO_ACTION[a] for a in path])
            entry = {"event": "attempt", "levels_before": lv, "info": info,
                     "actions": [DIR_TO_ACTION[a] for a in path]}
            leveled = False
            for i, a in enumerate(path, 1):
                resp = sess.action(DIR_TO_ACTION[a])
                frame, meta = resp["frame"], resp
                new_lv = int(meta.get("levels_completed") or 0)
                mover = ls20.locate_mover(frame)
                arr = np.asarray(frame)
                layers = arr.shape[0] if arr.ndim == 3 else 1
                print(f"  {i:02d} A{DIR_TO_ACTION[a]} bbox={mover} lv={new_lv} "
                      f"layers={layers} c11={int((ls20._plane(frame) == 11).sum())}")
                if new_lv > lv:
                    entry["levels_after"] = new_lv
                    entry["steps_used"] = i
                    leveled = True
                    log.append(entry)
                    print(f"  PASS lv {lv}->{new_lv}")
                    if (meta.get("state") != "WIN"
                            and new_lv < win_levels and new_lv < max_levels):
                        frame, meta = _sync_after_levelup(sess, frame)
                        print(f"  sync A1 -> mover={ls20.locate_mover(frame)}")
                        log.append({"event": "level_sync", "levels": new_lv,
                                    "mover": ls20.locate_mover(frame)})
                    break
                if layers > 1 and new_lv == lv and bool(np.all(arr[0] == 11)):
                    entry["levels_after"] = new_lv
                    entry["error"] = f"soft-reset flash at step {i}"
                    log.append(entry)
                    print("  FAIL soft-reset (energy)")
                    leveled = False
                    break
            else:
                entry["levels_after"] = int(meta.get("levels_completed") or 0)
                entry["error"] = "path exhausted without level-up"
                log.append(entry)
                print("  FAIL no level-up")
                break
            if not leveled:
                break

        return {
            "final_levels": int(meta.get("levels_completed") or 0),
            "final_state": meta.get("state"),
            "win_levels": win_levels,
            "log": log,
            "game_id": sess.game_id,
        }
    finally:
        sess.close()


def write_report(result: dict) -> Path:
    lines = [
        "# ls20 seated 多关通关报告（含 L3 通用解锁规则）",
        "",
        f"> game_id=`{result.get('game_id')}`",
        f"> final levels=`{result['final_levels']}` / win_levels=`{result.get('win_levels')}` "
        f"state=`{result.get('final_state')}`",
        "",
        "## 结论",
        "",
    ]
    fl = result["final_levels"]
    wl = result.get("win_levels") or 7
    if result.get("final_state") == "WIN" or fl >= wl:
        lines.append(f"**PASS** — 全关 seated 通关（levels={fl}）。")
    elif fl >= 3:
        lines.append(f"**L1-L3 PASS** — levels={fl}，L3 通用解锁规则生效。")
    elif fl >= 1:
        lines.append(f"**PARTIAL** — 至少 L1 过；停在 levels={fl}。")
    else:
        lines.append("**FAIL** — 未能 levels+1。")
    lines += ["", "## 逐步", ""]
    for row in result["log"]:
        lines.append(f"- `{row}`")
    lines += [
        "",
        "## 方法",
        "",
        "- `plan_two_phase`：接触 → L2+ 强制 H23（UP/DOWN/DOWN）→ H20 盖印（ov≥10）",
        "- **通用解锁规则**：armed-only 非 gate 且 y<54 的格 = 解锁对象；",
        "  进入它（armed 步行）后重跑两阶段流程。L1/L2 无此类格（底部色板被排除），",
        "  L3 唯一命中 (5,9) 环 → 压环翻面 → gate 开。",
        "- 过关判据仅 `levels_completed` 增加（红线 3）。",
        "",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-levels", type=int, default=3)
    args = ap.parse_args()
    result = run_online(max_levels=args.max_levels)
    path = write_report(result)
    print("\nreport", path)
    ok = (result["final_levels"] >= 3
          or result["final_levels"] >= (result.get("win_levels") or 7)
          or result.get("final_state") == "WIN")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
