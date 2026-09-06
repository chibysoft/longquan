"""Seated multi-level ls20 clear (H19/H20/H21/H23) — no canned action table.

Per level:
  1. Energy-aware BFS to marker contact (carrying overlaps marker)
  2. L2+: forced H23 ritual UP→DOWN→DOWN (same column sweep; live-probed)
  3. Energy-aware BFS to stamp with ov>=10 on armed walkable
After level-up the response frame is stale — sync ACTION1 yields the true start.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import carrying_bbox_from_cursor
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key

REPORT = ROOT / "docs" / "ls20-seated-clear-report.md"

# Live-probed: soft-reset on the 22nd depleting move after a full bar.
MAX_FUEL = 21

# H23 live-probed minimal vertical sweep after contact (L2+).
RITUAL = ((0, -1), (0, 1), (0, 1))  # UP, DOWN, DOWN


def _ov(a, b) -> int:
    ox0, oy0 = max(a[0], b[0]), max(a[1], b[1])
    ox1, oy1 = min(a[2], b[2]), min(a[3], b[3])
    if ox0 <= ox1 and oy0 <= oy1:
        return (ox1 - ox0 + 1) * (oy1 - oy0 + 1)
    return 0


def _ov_stamp(cell, offset, stamp) -> int:
    px, py = ls20.cursor_to_pixel(cell, offset)
    return _ov((px, py, px + 4, py + 1), stamp)


def _pickup_mask(cell, offset, pickups, already: int) -> tuple[int, bool]:
    px, py = ls20.cursor_to_pixel(cell, offset)
    mb = (px, py, px + 4, py + 1)
    mask = already
    refilled = False
    for i, pb in enumerate(pickups):
        bit = 1 << i
        if mask & bit:
            continue
        if _ov(mb, pb) > 0:
            mask |= bit
            refilled = True
    return mask, refilled


def _step_cell(cur, d, walk, warps):
    """Apply one action; honor portal warps when present.

    Live-probed: action on a portal cell teleports to the landing cell, then
    attempts the same direction from the landing (blocked => stay on landing).
    """
    if (cur, d) in warps:
        land = warps[(cur, d)]
        if land not in walk:
            return None
        after = (land[0] + d[0], land[1] + d[1])
        return after if after in walk else land
    nxt = (cur[0] + d[0], cur[1] + d[1])
    return nxt if nxt in walk else None


def _energy_bfs(start, fuel0, pmask0, walk, pickups, offset, goal_fn, warps=None):
    """Shortest path under H21 fuel. goal_fn(cell, fuel, pmask) -> bool."""
    warps = warps or {}
    start_key = (start[0], start[1], fuel0, pmask0)
    q = deque([(start_key, [])])
    seen = {start_key}
    while q:
        (x, y, fuel, pmask), path = q.popleft()
        if goal_fn((x, y), fuel, pmask):
            return path, (x, y), fuel, pmask
        for d in DIRS:
            nxt = _step_cell((x, y), d, walk, warps)
            if nxt is None:
                continue
            n_mask, refilled = _pickup_mask(nxt, offset, pickups, pmask)
            if fuel <= 0 and not refilled:
                continue
            n_fuel = MAX_FUEL if refilled else fuel - 1
            key = (nxt[0], nxt[1], n_fuel, n_mask)
            if key in seen:
                continue
            seen.add(key)
            q.append((key, path + [d]))
    return None, None, None, None


def plan_two_phase(frame):
    """Contact (+ H23 ritual on L2+) then stamp; energy-aware throughout."""
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    markers = [g for g in state.goals if g.id == "ls20-marker"]
    stamps = [g for g in state.goals if g.id == "ls20-stamp"]
    if not markers or not stamps:
        raise RuntimeError(f"missing goals: {[g.id for g in state.goals]}")
    marker, stamp = markers[0].shape, stamps[0].shape
    if (stamp[2] - stamp[0] + 1) * (stamp[3] - stamp[1] + 1) > 40 * 40:
        raise RuntimeError(f"stamp bbox implausible {stamp}")
    if (marker[2] - marker[0] + 1) * (marker[3] - marker[1] + 1) > 20 * 20:
        raise RuntimeError(f"marker bbox implausible {marker}")

    pickups = ls20.energy_pickups(frame)
    need_ritual = len(pickups) > 0
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    warps = ls20.detect_warps(frame, offset, walk_u)
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))

    def at_contact(cell, _fuel, _pm):
        return _ov(carrying_bbox_from_cursor(cell, offset), marker) > 0

    p1, c1, f1, pm1 = _energy_bfs(
        state.cursor, fuel0, 0, walk_u, pickups, offset, at_contact, warps,
    )
    if p1 is None:
        raise RuntimeError(f"no path to marker contact; marker={marker}")

    path = list(p1)
    cur, fuel, pmask = c1, f1, pm1

    if need_ritual:
        for a in RITUAL:
            nxt = _step_cell(cur, a, walk_u, warps)
            if nxt is None:
                raise RuntimeError(f"H23 ritual blocked {a} at {cur}")
            n_mask, refilled = _pickup_mask(nxt, offset, pickups, pmask)
            if fuel <= 0 and not refilled:
                raise RuntimeError(f"H23 ritual out of fuel at {cur}")
            fuel = MAX_FUEL if refilled else fuel - 1
            cur, pmask = nxt, n_mask
            path.append(a)

    def at_stamp(cell, _fuel, _pm):
        return _ov_stamp(cell, offset, stamp) >= 10

    p2, c2, f2, pm2 = _energy_bfs(
        cur, fuel, pmask, walk_a, pickups, offset, at_stamp, warps,
    )
    if p2 is None:
        raise RuntimeError(
            f"no path to stamp after arming; at={cur} fuel={fuel} "
            f"pickups={pickups} stamp={stamp}"
        )
    path.extend(p2)

    return path, {
        "t1": c1,
        "t2": c2,
        "ov": _ov_stamp(c2, offset, stamp),
        "marker": marker,
        "stamp": stamp,
        "path1_len": len(p1),
        "ritual_len": len(RITUAL) if need_ritual else 0,
        "path2_len": len(p2),
        "cursor0": state.cursor,
        "pickups": pickups,
        "fuel0": fuel0,
        "fuel_end": f2,
        "path_len": len(path),
        "ritual": need_ritual,
        "warps": {str(k): v for k, v in warps.items()},
    }


def run_online(max_levels: int = 7) -> dict:
    key = _api_key()
    if not key:
        raise RuntimeError("no ARC_API_KEY")
    sess = OnlineSession(key)
    log = []
    try:
        sess.open(tags=["ls20_seated_multilevel"])
        reset = sess.reset()
        frame, meta = reset["frame"], reset
        win_levels = int(meta.get("win_levels") or max_levels)
        print(f"start lv={meta.get('levels_completed')} win_levels={win_levels} "
              f"mover={ls20.locate_mover(frame)}")

        while True:
            lv = int(meta.get("levels_completed") or 0)
            state_name = meta.get("state")
            if state_name == "WIN" or lv >= win_levels or lv >= max_levels:
                log.append({"event": "done", "levels": lv, "state": state_name})
                break
            try:
                path, info = plan_two_phase(frame)
            except Exception as e:
                log.append({"event": "plan_fail", "levels": lv, "error": str(e)})
                print(f"PLAN FAIL at lv={lv}: {e}")
                break
            print(
                f"\n=== clear level index {lv} === "
                f"len={len(path)} ritual={info.get('ritual')} "
                f"pickups={info['pickups']} marker={info['marker']} stamp={info['stamp']}"
            )
            print("actions", [DIR_TO_ACTION[a] for a in path])
            entry = {
                "event": "attempt", "levels_before": lv, "info": info,
                "actions": [DIR_TO_ACTION[a] for a in path],
            }
            leveled = False
            for i, a in enumerate(path, 1):
                resp = sess.action(DIR_TO_ACTION[a])
                frame, meta = resp["frame"], resp
                new_lv = int(meta.get("levels_completed") or 0)
                mover = ls20.locate_mover(frame)
                arr = np.asarray(frame)
                layers = arr.shape[0] if arr.ndim == 3 else 1
                print(
                    f"  {i:02d} A{DIR_TO_ACTION[a]} bbox={mover} lv={new_lv} "
                    f"layers={layers} c11={int((ls20._plane(frame) == 11).sum())}"
                )
                if new_lv > lv:
                    entry["levels_after"] = new_lv
                    entry["steps_used"] = i
                    leveled = True
                    log.append(entry)
                    print(f"  PASS lv {lv}->{new_lv}")
                    if (meta.get("state") != "WIN"
                            and new_lv < win_levels and new_lv < max_levels):
                        sync = sess.action(1)
                        frame, meta = sync["frame"], sync
                        print(
                            f"  sync A1 -> mover={ls20.locate_mover(frame)} "
                            f"stamp={ls20.stamp_block(frame)} "
                            f"pickups={ls20.energy_pickups(frame)}"
                        )
                        log.append({
                            "event": "level_sync", "levels": new_lv,
                            "mover": ls20.locate_mover(frame), "sync_action": 1,
                        })
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
        "# ls20 seated 多关通关报告",
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
        "- `ls20.init`：`locate_mover` 认 5×2 色12（L3+ 去装饰）",
        "- L3+：`detect_warps` 顶带传送门（色1 侧轨 → 同行段落点）",
        "- 接触 → L2+ 强制 H23（UP/DOWN/DOWN）→ H20 盖印（ov≥10）",
        "- H21 能量感知 BFS；过关后 sync ACTION1 再规划",
        "",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-levels", type=int, default=7)
    ap.add_argument("--plan-only-fixture", type=str, default="")
    args = ap.parse_args()
    if args.plan_only_fixture:
        data = json.loads(Path(args.plan_only_fixture).read_text(encoding="utf-8"))
        path, info = plan_two_phase(data["frame"])
        print("info", info)
        print("actions", [DIR_TO_ACTION[a] for a in path])
        return 0
    result = run_online(max_levels=args.max_levels)
    path = write_report(result)
    print("\nreport", path)
    ok = (result["final_levels"] >= (result.get("win_levels") or 7)
          or result.get("final_state") == "WIN")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
