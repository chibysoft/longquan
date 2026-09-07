"""L4 arming probe: falsify H1/H2 (unlock then stamp without H23).

Climb L1-L3 with the seated full solver, then on L4:
  1. optional unlock of armed-only non-gate cells (frame-derived)
  2. snapshot walk_u/walk_a and stamp-glyph color9 (H2)
  3. execute armed BFS to stamp with NO marker contact / NO UDD (H1)

Pass criterion: levels_completed 3 -> 4 only.
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
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, _ov, plan_two_phase
from tools.ls20_seated_clear_full import (
    _plan_to_pickup,
    _plan_to_unlock,
    _unlock_candidates,
)

REPORT = ROOT / "docs" / "ls20_l4_arming_probe.md"
FIXTURE_POST = ROOT / "tests" / "fixtures" / "ls20_l4_frame_post_unlock.json"


def _fuel0(frame) -> int:
    ui = ls20.ui_energy(frame)
    return MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))


def _has_plus_marker(frame) -> bool:
    """True iff a compact plus-like 0/1 blob exists (L1/L2/L3 style)."""
    g = ls20._plane(frame)
    H, W = g.shape
    for y in range(H - 2):
        if y >= 54:
            break
        for x in range(W - 2):
            patch = g[y : y + 3, x : x + 3]
            core = {(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)}
            vals = [int(patch[dy, dx]) for dx, dy in core]
            if all(v in (0, 1) for v in vals) and sum(v in (0, 1) for v in vals) == 5:
                # Reject solid 3x3 blocks of floor; require center + arms.
                if int(patch[1, 1]) in (0, 1):
                    return True
    return False


def _stamp_c9(frame) -> int:
    st = ls20.init(frame)
    stamp = next((g.shape for g in st.goals if g.id == "ls20-stamp"), None)
    if stamp is None:
        return -1
    x0, y0, x1, y1 = stamp
    g = ls20._plane(frame)
    return int((g[y0 : y1 + 1, x0 : x1 + 1] == 9).sum())


def _gate_walk(frame) -> dict:
    off = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, off, armed=False)
    wa = ls20.build_walkable(frame, off, armed=True)
    st = ls20.init(frame)
    stamp = next(g.shape for g in st.goals if g.id == "ls20-stamp")
    gate = None
    for c in sorted(wa):
        if _ov(mover_bbox_from_cursor(c, off), stamp) >= 10:
            gate = c
            break
    return {
        "gate": gate,
        "gate_in_walk_u": gate in wu if gate is not None else None,
        "gate_in_walk_a": gate in wa if gate is not None else None,
        "stamp_c9": _stamp_c9(frame),
        "has_plus": _has_plus_marker(frame),
        "unlock_cands": _unlock_candidates(frame),
        "marker": next((g.shape for g in st.goals if g.id == "ls20-marker"), None),
    }


def _plan_armed_stamp_only(frame):
    """No contact, no ritual — energy BFS on walk_a to ov>=10 stamp."""
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    stamp = next(g.shape for g in state.goals if g.id == "ls20-stamp")
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    fuel0 = _fuel0(frame)

    def at_stamp(cell, _f, _p):
        return _ov(mover_bbox_from_cursor(cell, offset), stamp) >= 10

    p, c, f, pm = _energy_bfs(
        state.cursor, fuel0, 0, walk_a, pickups, offset, at_stamp, warps,
    )
    return p, c, f, {
        "t2": c, "fuel_end": f, "path_len": None if p is None else len(p),
        "stamp": stamp, "cursor0": state.cursor,
    }


def _climb_to_l4(sess) -> tuple:
    import time

    def _act(aid):
        last = None
        for i in range(4):
            try:
                return sess.action(aid)
            except Exception as e:
                last = e
                time.sleep(1.5 * (i + 1))
        raise last

    reset = sess.reset()
    frame, meta = reset["frame"], reset
    while int(meta.get("levels_completed") or 0) < 3:
        lv = int(meta.get("levels_completed") or 0)
        for cand in _unlock_candidates(frame):
            p_pu, _ = _plan_to_pickup(frame)
            if p_pu:
                for a in p_pu:
                    resp = _act(DIR_TO_ACTION[a])
                    frame, meta = resp["frame"], resp
            p, _, _ = _plan_to_unlock(frame, cand)
            if p is None:
                continue
            for a in p:
                resp = _act(DIR_TO_ACTION[a])
                frame, meta = resp["frame"], resp
        path, _ = plan_two_phase(frame)
        leveled = False
        for a in path:
            resp = _act(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            if int(meta.get("levels_completed") or 0) > lv:
                leveled = True
                break
        if not leveled:
            raise RuntimeError(f"climb failed at lv={lv}")
        resp = _act(1)  # sync stale frame
        frame, meta = resp["frame"], resp
    return frame, meta


def _adjacent_unarmed(frame, target):
    """L3-style: cell in walk_u that can step into `target` (one armed step)."""
    offset = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, offset, armed=False)
    wa = ls20.build_walkable(frame, offset, armed=True)
    warps = ls20.detect_warps(frame, offset, wu)
    from tools.ls20_seated_clear import _step_cell
    from longquan.interactive.state import DIRS
    hits = []
    for cell in wu:
        for d in DIRS:
            if _step_cell(cell, d, wa, warps) == target:
                hits.append((cell, d))
    return hits


def _plan_crush(frame, target):
    """Unarmed BFS to an adjacent walk_u cell, then one step into target."""
    hits = _adjacent_unarmed(frame, target)
    if not hits:
        return None, None
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, wu)
    pickups = ls20.energy_pickups(frame)
    fuel0 = _fuel0(frame)
    best = None
    for adj, d_in in hits:
        p, c, f, pm = _energy_bfs(
            state.cursor, fuel0, 0, wu, pickups, offset,
            lambda cell, _f, _p, t=adj: cell == t, warps,
        )
        if p is None:
            continue
        path = list(p) + [d_in]
        if best is None or len(path) < len(best[0]):
            best = (path, target)
    return (best[0], best[1]) if best else (None, None)


def _do_unlocks(sess, frame, meta, log, *, style: str = "crush"):
    cands = _unlock_candidates(frame)
    log.append({"tag": "unlock_cands", "cands": cands, "snap": _gate_walk(frame)})
    if not cands:
        return frame, meta
    p_pu, _ = _plan_to_pickup(frame)
    if p_pu:
        for a in p_pu:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
        log.append({"tag": "pre_fuel", "mover": ls20.locate_mover(frame),
                    "cursor": ls20.init(frame).cursor,
                    "ui": ls20.ui_energy(frame)})
    for cand in cands:
        if style == "crush":
            p, _ = _plan_crush(frame, cand)
        else:
            p, _, _ = _plan_to_unlock(frame, cand)
        if p is None:
            log.append({"tag": "unlock_unreachable", "cell": cand, "style": style})
            continue
        log.append({"tag": "unlock_plan", "cell": cand, "style": style,
                    "len": len(p), "actions": [DIR_TO_ACTION[a] for a in p]})
        for i, a in enumerate(p, 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            cur = ls20.init(frame).cursor
            log.append({
                "tag": "unlock_step", "step": i, "action": DIR_TO_ACTION[a],
                "cursor": cur, "mover": ls20.locate_mover(frame),
                "levels": int(meta.get("levels_completed") or 0),
            })
        reached = ls20.init(frame).cursor == cand
        log.append({
            "tag": "post_unlock", "cell": cand, "reached": reached,
            "cursor": ls20.init(frame).cursor,
            "mover": ls20.locate_mover(frame),
            "levels": int(meta.get("levels_completed") or 0),
            "snap": _gate_walk(frame),
            "c9": int((ls20._plane(frame) == 9).sum()),
            "c12": int((ls20._plane(frame) == 12).sum()),
            "c14": int((ls20._plane(frame) == 14).sum()),
        })
    g = ls20._plane(frame)
    FIXTURE_POST.write_text(
        json.dumps({"frame": g.tolist(),
                    "levels": int(meta.get("levels_completed") or 0)}),
        encoding="utf-8",
    )
    return frame, meta


def run(skip_unlock: bool = False, unlock_style: str = "crush") -> dict:
    key = _api_key()
    if not key:
        raise RuntimeError("ARC_API_KEY not found")
    sess = OnlineSession(key)
    log = []
    try:
        sess.open(tags=["ls20_l4_arming"])
        frame, meta = _climb_to_l4(sess)
        lv = int(meta.get("levels_completed") or 0)
        log.append({"tag": "l4_start", "levels": lv, "snap": _gate_walk(frame),
                    "mover": ls20.locate_mover(frame)})
        print(f"L4 start lv={lv} snap={log[-1]['snap']}")

        if not skip_unlock:
            frame, meta = _do_unlocks(sess, frame, meta, log, style=unlock_style)
            post = [r for r in log if r.get("tag") == "post_unlock"]
            print(f"post-unlock={post[-1] if post else None}")

        # H1: armed stamp only
        path, dest, fuel, info = _plan_armed_stamp_only(frame)
        log.append({"tag": "plan_h1", "ok": path is not None, "info": info})
        if path is None:
            log.append({"tag": "RESULT", "verdict": "H1_PLAN_FAIL"})
            return {"log": log, "verdict": "H1_PLAN_FAIL"}

        print(f"H1 path len={len(path)} -> {dest} fuel_end={fuel}")
        for i, a in enumerate(path, 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            nl = int(meta.get("levels_completed") or 0)
            log.append({
                "tag": "h1_step", "step": i, "action": DIR_TO_ACTION[a],
                "mover": ls20.locate_mover(frame), "levels": nl,
                "ui": ls20.ui_energy(frame),
            })
            if nl > lv:
                log.append({"tag": "RESULT", "verdict": "H1_PASS", "levels": nl})
                print(f"H1_PASS levels {lv}->{nl}")
                return {"log": log, "verdict": "H1_PASS"}

        snap = _gate_walk(frame)
        log.append({"tag": "h1_end", "snap": snap, "mover": ls20.locate_mover(frame)})
        log.append({"tag": "RESULT", "verdict": "H1_FAIL", "snap": snap})
        print(f"H1_FAIL end snap={snap}")
        return {"log": log, "verdict": "H1_FAIL"}
    finally:
        sess.close()


def _write_report(result: dict) -> None:
    lines = [
        "# ls20 L4 arming probe",
        "",
        f"> verdict: **{result.get('verdict')}**",
        "",
        "## log",
        "",
    ]
    for row in result.get("log", []):
        lines.append(f"- `{row}`")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {REPORT}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-unlock", action="store_true")
    ap.add_argument("--unlock-style", choices=("crush", "armed"), default="crush")
    ap.add_argument("--plan-only", action="store_true",
                    help="offline plan on fixture only")
    args = ap.parse_args()
    if args.plan_only:
        data = json.loads(
            (ROOT / "tests/fixtures/ls20_l4_frame_live.json").read_text(encoding="utf-8")
        )
        frame = data["frame"]
        print("snap", _gate_walk(frame))
        print("has_plus", _has_plus_marker(frame))
        print("adjacent", _adjacent_unarmed(frame, (6, 6)))
        p_c, _ = _plan_crush(frame, (6, 6))
        print("crush plan", None if p_c is None else [DIR_TO_ACTION[a] for a in p_c])
        p, c, f, info = _plan_armed_stamp_only(frame)
        print("H1 plan", None if p is None else len(p), c, f, info)
        return 0
    result = run(skip_unlock=args.skip_unlock, unlock_style=args.unlock_style)
    _write_report(result)
    return 0 if result.get("verdict") == "H1_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
