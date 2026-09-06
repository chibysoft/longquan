"""Task A: online closed-loop validation of ls20 move.

Design rules (non-negotiable):
  - No hardcoded coordinates: locate mover by color-12; pick BFS target by
    reachability flood-fill (farthest reachable cell, stable tie-break).
  - Per-step compare: after every ACTION, re-locate color-12 and require 0px
    deviation from the predicted pixel top-left.
  - Auto-write docs/online-validation-report.md (handoff format).
  - Reproducible plan from tests/fixtures/ls20_l1_frame_live.json.
  - Closed-book: frames + online API only; no engine source; no extra actions.

Usage:
  python tools/ls20_online_validate.py              # full online run
  python tools/ls20_online_validate.py --plan-only  # fixture plan + report stub
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import requests

# repo root on sys.path so `longquan` imports work when run as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20, move, search  # noqa: E402
from longquan.interactive.state import Action, WorldState  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "ls20_l1_frame_live.json"
REPORT = ROOT / "docs" / "online-validation-report.md"

BASE = os.environ.get("ARC_BASE_URL", "https://three.arcprize.org")

# Semantic direction -> engine ACTION id (live-probed: 1=U 2=D 3=L 4=R)
DIR_TO_ACTION: Dict[Action, int] = {
    (0, -1): 1,
    (0, 1): 2,
    (-1, 0): 3,
    (1, 0): 4,
}
ACTION_NAME = {1: "ACTION1/UP", 2: "ACTION2/DOWN", 3: "ACTION3/LEFT", 4: "ACTION4/RIGHT"}


def _api_key() -> str:
    candidates = [
        ROOT.parent / "ARC-AGI-3-Agents" / ".env",
        ROOT / ".env",
        Path(".env"),
        Path("/sessions/nice-inspiring-edison/mnt/Projects/ARC-AGI-3-Agents/.env"),
    ]
    for p in candidates:
        if p.is_file():
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line.startswith("ARC_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return os.environ.get("ARC_API_KEY", "")


def _plane(frame) -> np.ndarray:
    a = np.asarray(frame, dtype=np.int8)
    return a[0] if a.ndim == 3 else a


# ---------------------------------------------------------------------------
# Offline plan (fixture only — reproducible, no network)
# ---------------------------------------------------------------------------

def pick_target_by_reachability(state: WorldState) -> Tuple[Tuple[int, int], int]:
    """Farthest walkable cell from cursor via BFS flood-fill.

    Tie-break: larger distance first, then smaller (x, y) for stability.
    Never uses a hand-picked coordinate.
    """
    start = state.cursor
    dist = {start: 0}
    q = deque([start])
    while q:
        cx, cy = q.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nxt = (cx + dx, cy + dy)
            if nxt in state.walkable and nxt not in dist:
                dist[nxt] = dist[(cx, cy)] + 1
                q.append(nxt)
    # exclude start; require at least 1 step
    candidates = [(d, xy) for xy, d in dist.items() if d > 0]
    if not candidates:
        raise RuntimeError("no reachable cells from start — walkable model empty?")
    candidates.sort(key=lambda t: (-t[0], t[1][0], t[1][1]))
    best_d, best_xy = candidates[0]
    return best_xy, best_d


def plan_from_fixture(fixture_path: Path = FIXTURE):
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    frame = data["frame"]
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    start_px = ls20.locate_mover(frame)
    target, flood_dist = pick_target_by_reachability(state)

    def done(s: WorldState) -> bool:
        return s.cursor == target

    found, path = search.bfs(state, move.actions, move.step, done)
    if not found:
        raise RuntimeError(f"BFS failed to reach target {target}")

    # predicted cursor + pixel sequence (including step 0 = start)
    pred_cursors: List[Tuple[int, int]] = [state.cursor]
    pred_pixels: List[Tuple[int, int]] = [ls20.cursor_to_pixel(state.cursor, offset)]
    s = state
    for a in path:
        s = move.step(s, a)
        pred_cursors.append(s.cursor)
        pred_pixels.append(ls20.cursor_to_pixel(s.cursor, offset))

    return {
        "fixture": str(fixture_path.relative_to(ROOT)).replace("\\", "/"),
        "game_id_fixture": data.get("game_id"),
        "start_cursor": state.cursor,
        "start_pixel_bbox": start_px,
        "grid_offset": offset,
        "walkable_n": len(state.walkable),
        "target": target,
        "flood_dist": flood_dist,
        "path": path,
        "path_actions": [DIR_TO_ACTION[a] for a in path],
        "pred_cursors": pred_cursors,
        "pred_pixels": pred_pixels,
        "fixture_frame": frame,
        "init_state": state,
        "offset": offset,
    }


# ---------------------------------------------------------------------------
# Online session
# ---------------------------------------------------------------------------

class OnlineSession:
    def __init__(self, key: str, base: str = BASE):
        self.base = base
        self.s = requests.Session()
        self.key = key
        self.card_id: Optional[str] = None
        self.game_id: Optional[str] = None
        self.guid: Optional[str] = None

    def _headers(self, json_body: bool = False) -> dict:
        h = {"X-API-Key": self.key, "Accept": "application/json"}
        if json_body:
            h["Content-Type"] = "application/json"
        return h

    def open(self, tags=None) -> None:
        r = self.s.post(
            f"{self.base}/api/scorecard/open",
            headers=self._headers(True),
            json={"tags": tags or ["ls20_move_validate"]},
            timeout=20,
        )
        r.raise_for_status()
        self.card_id = r.json()["card_id"]
        r = self.s.get(
            f"{self.base}/api/games/ls20",
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        self.game_id = r.json()["game_id"]

    def reset(self) -> dict:
        body = {"card_id": self.card_id, "game_id": self.game_id}
        if self.guid:
            body["guid"] = self.guid
        r = self.s.post(
            f"{self.base}/api/cmd/RESET",
            headers=self._headers(True),
            json=body,
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        self.guid = data["guid"]
        return data

    def action(self, action_id: int, x: Optional[int] = None, y: Optional[int] = None) -> dict:
        body = {"game_id": self.game_id, "guid": self.guid}
        if x is not None and y is not None:
            body["x"] = int(x)
            body["y"] = int(y)
        r = self.s.post(
            f"{self.base}/api/cmd/ACTION{action_id}",
            headers=self._headers(True),
            json=body,
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        self.guid = data.get("guid", self.guid)
        return data

    def close(self) -> None:
        if not self.card_id:
            return
        try:
            self.s.post(
                f"{self.base}/api/scorecard/close",
                headers=self._headers(True),
                json={"card_id": self.card_id},
                timeout=15,
            )
        except Exception:
            pass


def run_online(plan: dict) -> dict:
    key = _api_key()
    if not key:
        raise RuntimeError("ARC_API_KEY not found (check ARC-AGI-3-Agents/.env)")

    sess = OnlineSession(key)
    steps_log: List[dict] = []
    passed = True
    fail_reason = ""

    try:
        sess.open()
        reset = sess.reset()
        live_frame = reset["frame"]
        live_bb = ls20.locate_mover(live_frame)
        if live_bb is None:
            raise RuntimeError("RESET frame has no color-12 mover")

        live_state = ls20.init(live_frame)
        live_offset = ls20.grid_offset(live_frame)

        # Gate: live L1 start must match fixture plan coordinates
        start_ok = (
            live_state.cursor == plan["start_cursor"]
            and live_offset == plan["offset"]
            and live_bb[:2] == plan["pred_pixels"][0]
        )
        steps_log.append({
            "step": 0,
            "action": "RESET",
            "pred_pixel": plan["pred_pixels"][0],
            "pred_cursor": plan["start_cursor"],
            "actual_pixel": live_bb[:2],
            "actual_bbox": live_bb,
            "actual_cursor": live_state.cursor,
            "dx": live_bb[0] - plan["pred_pixels"][0][0],
            "dy": live_bb[1] - plan["pred_pixels"][0][1],
            "ok": start_ok,
        })
        if not start_ok:
            passed = False
            fail_reason = (
                f"live start mismatch: cursor {live_state.cursor} vs "
                f"{plan['start_cursor']}, pixel {live_bb[:2]} vs {plan['pred_pixels'][0]}"
            )
            return _result(plan, sess, steps_log, passed, fail_reason, reset)

        # Per-step execute + compare (only the planned actions — no extras)
        for i, (sem, aid) in enumerate(zip(plan["path"], plan["path_actions"]), start=1):
            resp = sess.action(aid)
            frame = resp["frame"]
            bb = ls20.locate_mover(frame)
            if bb is None:
                passed = False
                fail_reason = f"step {i}: color-12 disappeared after {ACTION_NAME[aid]}"
                steps_log.append({
                    "step": i,
                    "action": ACTION_NAME[aid],
                    "pred_pixel": plan["pred_pixels"][i],
                    "pred_cursor": plan["pred_cursors"][i],
                    "actual_pixel": None,
                    "actual_bbox": None,
                    "actual_cursor": None,
                    "dx": None,
                    "dy": None,
                    "ok": False,
                })
                break

            pred_px = plan["pred_pixels"][i]
            dx = bb[0] - pred_px[0]
            dy = bb[1] - pred_px[1]
            ok = (dx == 0 and dy == 0)
            # also confirm logical cursor via init (same frame)
            cur = ls20.init(frame).cursor
            steps_log.append({
                "step": i,
                "action": ACTION_NAME[aid],
                "semantic": sem,
                "pred_pixel": pred_px,
                "pred_cursor": plan["pred_cursors"][i],
                "actual_pixel": bb[:2],
                "actual_bbox": bb,
                "actual_cursor": cur,
                "dx": dx,
                "dy": dy,
                "ok": ok,
            })
            if not ok:
                passed = False
                fail_reason = (
                    f"step {i} ({ACTION_NAME[aid]}): pixel deviation "
                    f"dx={dx} dy={dy} (pred={pred_px}, actual={bb[:2]})"
                )
                break
    finally:
        sess.close()

    return _result(plan, sess, steps_log, passed, fail_reason, None)


def _result(plan, sess, steps_log, passed, fail_reason, reset_meta) -> dict:
    return {
        "mode": "online",
        "passed": passed,
        "fail_reason": fail_reason,
        "card_id": getattr(sess, "card_id", None),
        "game_id": getattr(sess, "game_id", None),
        "steps": steps_log,
        "max_abs_dev": max(
            (max(abs(s["dx"] or 0), abs(s["dy"] or 0)) for s in steps_log),
            default=0,
        ),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(plan: dict, online: Optional[dict], plan_only: bool) -> Path:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    path_str = " -> ".join(
        f"{ACTION_NAME[DIR_TO_ACTION[a]]}" for a in plan["path"]
    )
    pred_seq = ", ".join(
        f"{i}:{c}/{p}" for i, (c, p) in enumerate(zip(plan["pred_cursors"], plan["pred_pixels"]))
    )

    if plan_only or online is None:
        verdict = "PLAN_ONLY (online not run)"
        tone = "not verified online"
    elif online["passed"]:
        verdict = "PASS"
        tone = "actual displacement matches prediction; max deviation = 0 px"
    else:
        verdict = "FAIL"
        tone = online.get("fail_reason") or "deviation detected"

    lines = [
        "# ls20 move 线上闭环验证报告",
        "",
        f"> 生成时间：{now}",
        f"> 脚本：`tools/ls20_online_validate.py`",
        f"> 规划锚点：`{plan['fixture']}`（固化帧，可复现）",
        "",
        "---",
        "",
        "## 结论",
        "",
        f"**{verdict}** — {tone}",
        "",
        "| 项 | 值 |",
        "|----|----|",
        f"| 通过条件 | 每步实测色12 锚点与预测偏差 = 0 像素 |",
        f"| 判定 | **{verdict}** |",
        f"| 最大 |Δx|,|Δy| | "
        f"{0 if plan_only or online is None else online['max_abs_dev']} px |",
        f"| 规划步数 | {len(plan['path'])} |",
        f"| BFS 目标（可达性最远格） | `{plan['target']}` "
        f"(flood_dist={plan['flood_dist']}) |",
        "",
        "---",
        "",
        "## 规划（离线，仅依赖 fixture）",
        "",
        "定位方式：色12 bbox 模式匹配；目标：对 walkable 做 BFS 洪泛，取最远可达格"
        "（并列时取更小 (x,y)）。无手算坐标。",
        "",
        "| 项 | 值 |",
        "|----|----|",
        f"| 起始逻辑光标 | `{plan['start_cursor']}` |",
        f"| 起始像素 bbox | `{plan['start_pixel_bbox']}` |",
        f"| 网格 offset | `{plan['grid_offset']}` |",
        f"| walkable 格数 | {plan['walkable_n']} |",
        f"| 目标逻辑格 | `{plan['target']}` |",
        f"| 动作序列 | `{[DIR_TO_ACTION[a] for a in plan['path']]}` "
        f"({path_str}) |",
        f"| 预测光标序列 | {pred_seq} |",
        "",
        "### 预测坐标序列（逐步）",
        "",
        "| step | action | pred_cursor | pred_pixel (x,y) |",
        "|-----:|--------|-------------|------------------|",
        f"| 0 | (start) | `{plan['pred_cursors'][0]}` | `{plan['pred_pixels'][0]}` |",
    ]
    for i, a in enumerate(plan["path"], start=1):
        aid = DIR_TO_ACTION[a]
        lines.append(
            f"| {i} | {ACTION_NAME[aid]} | `{plan['pred_cursors'][i]}` | "
            f"`{plan['pred_pixels'][i]}` |"
        )

    lines += ["", "---", "", "## 线上执行比对", ""]

    if plan_only or online is None:
        lines += [
            "_未执行线上回放（`--plan-only` 或无 API 结果）。_",
            "",
        ]
    else:
        lines += [
            f"game_id=`{online.get('game_id')}` · card_id=`{online.get('card_id')}`",
            "",
            "| step | action | pred_pixel | actual_pixel | Δx | Δy | ok |",
            "|-----:|--------|------------|--------------|---:|---:|:--:|",
        ]
        for s in online["steps"]:
            lines.append(
                f"| {s['step']} | {s['action']} | `{s['pred_pixel']}` | "
                f"`{s['actual_pixel']}` | {s['dx']} | {s['dy']} | "
                f"{'Y' if s['ok'] else 'N'} |"
            )
        lines += ["", f"**失败原因**：{online['fail_reason'] or '（无）'}", ""]

    lines += [
        "---",
        "",
        "## 纪律核对",
        "",
        "- 不硬编码坐标：光标 = 色12；目标 = 可达性洪泛最远格",
        "- 不跳过比对：每步取帧、定位、与预测比对",
        "- 可复现：规划仅依赖 `ls20_l1_frame_live.json`",
        "- 闭卷：只发规划内 ACTION；不读引擎源码；不 import 罐头",
        "",
    ]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT


def main() -> int:
    ap = argparse.ArgumentParser(description="ls20 move online closed-loop validation")
    ap.add_argument("--plan-only", action="store_true",
                    help="plan from fixture and write report; skip online API")
    args = ap.parse_args()

    print(f"planning from {FIXTURE} ...")
    plan = plan_from_fixture()
    print(
        f"  start={plan['start_cursor']} target={plan['target']} "
        f"flood_dist={plan['flood_dist']} path_len={len(plan['path'])} "
        f"actions={[DIR_TO_ACTION[a] for a in plan['path']]}"
    )

    online = None
    if not args.plan_only:
        print("running online closed loop ...")
        try:
            online = run_online(plan)
            print(
                f"  verdict={'PASS' if online['passed'] else 'FAIL'} "
                f"max_dev={online['max_abs_dev']}px "
                f"steps_compared={len(online['steps'])}"
            )
            if online["fail_reason"]:
                print(f"  reason: {online['fail_reason']}")
        except Exception as e:
            print(f"  ONLINE ERROR: {e}", file=sys.stderr)
            # still write plan report with fail note
            online = {
                "mode": "online",
                "passed": False,
                "fail_reason": f"online exception: {e}",
                "card_id": None,
                "game_id": None,
                "steps": [],
                "max_abs_dev": -1,
            }

    report = write_report(plan, online, plan_only=args.plan_only)
    print(f"report -> {report}")

    if args.plan_only:
        return 0
    return 0 if online and online["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
