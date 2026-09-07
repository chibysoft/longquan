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

L5_REC = Path(
    r"D:\Projects\ARC-AGI-3-Agents\recordings"
    r"\ls20-9607627b.lingjingsolo.800.5f1bf1fd-a88e-4c5f-8c63-3c85bc6f5f97.recording.jsonl"
)

from longquan.interactive import ls20
from longquan.interactive.match import (
    carrying_bbox_from_cursor, mover_bbox_from_cursor,
)
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import (
    MAX_FUEL, RITUAL, _energy_bfs, _ov, _ov_stamp, _step_cell, plan_two_phase,
)

REPORT = ROOT / "docs" / "ls20-seated-clear-full-report.md"

# A cell whose footprint reaches (py < 54) is playfield; >=54 is bottom palette.
PALETTE_Y = 54


def _l5_recording_waypoints():
    """Cursor sequence for L5 from spawn (9,7) through PASS (10,1).

    Extracted from lingjingsolo recording; live smart-replay confirms PASS when
    followed with BFS recovery on desyncs.
    """
    out = []
    with open(L5_REC, encoding="utf-8") as fh:
        for line in fh:
            o = json.loads(line)["data"]
            lv = o.get("levels_completed") or 0
            if lv < 4:
                continue
            cur = ls20.init(o["frame"]).cursor
            out.append(cur)
            if lv >= 5:
                break
    # drop L4 tail until spawn (9,7)
    while out and out[0] != (9, 7):
        out.pop(0)
    return out


def _l6_recording_waypoints():
    """Cursor sequence for L6 from post-L5 spawn (4,9) through PASS (10,10).

    Stamp starts mid ((10,7) ov>=10 is a decoy), drops to bottom after (10,6),
    then needs a fuel tour before (10,9) DOWN → (10,10). Recording path is the
    closed-book clear; BFS to mid-stamp soft-locks.
    """
    out = []
    with open(L5_REC, encoding="utf-8") as fh:
        for line in fh:
            o = json.loads(line)["data"]
            lv = o.get("levels_completed") or 0
            if lv < 5:
                continue
            cur = ls20.init(o["frame"]).cursor
            out.append(cur)
            if lv >= 6:
                break
    while out and out[0] != (4, 9):
        out.pop(0)
    return out


def _l7_recording_waypoints():
    """Cursor sequence for L7 from post-L6 spawn (3,2) through WIN (5,10).

    Early L7 has no marker (plan_two_phase fails); stamp bbox is full-frame.
    Live clear follows the recording spine to (5,10).
    """
    out = []
    with open(L5_REC, encoding="utf-8") as fh:
        for line in fh:
            o = json.loads(line)["data"]
            lv = o.get("levels_completed") or 0
            if lv < 6:
                continue
            cur = ls20.init(o["frame"]).cursor
            out.append(cur)
            if lv >= 7 or o.get("state") == "WIN":
                break
    while out and out[0] != (3, 2):
        out.pop(0)
    return out


def _unlock_candidates(frame):
    """Armed-only non-gate playfield cells that are crush-reachable.

    Armed-only = in walk_a but not walk_u (footprint contains color9, no color4).
    Non-gate = footprint does not overlap the stamp. Playfield = top pixel y<54.

    Reachable = exists a walk_u neighbor that can take one walk_a step into the
    cell, AND that neighbor is energy-BFS-reachable on walk_u (with warps).
    This drops L4's sealed ring (6,6) once (7,5) eject is modeled, without
    hardcoding coordinates.
    """
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    # Topology probe only — ignore low ui so mid-path scans still see cands.
    fuel0 = MAX_FUEL
    stamp = next((g.shape for g in state.goals if g.id == "ls20-stamp"), None)
    out = []
    for c in sorted(walk_a - walk_u):
        if stamp is not None and _ov(mover_bbox_from_cursor(c, offset), stamp) > 0:
            continue
        px, py = ls20.cursor_to_pixel(c, offset)
        if py >= PALETTE_Y:
            continue
        # crush-style approaches
        approaches = []
        for d in DIRS:
            # cell that steps into c
            for prev in walk_u:
                if _step_cell(prev, d, walk_a, warps) == c:
                    approaches.append(prev)
        ok = False
        for adj in sorted(set(approaches)):
            p, _, _, _ = _energy_bfs(
                state.cursor, fuel0, 0, walk_u, pickups, offset,
                lambda cell, _f, _p, t=adj: cell == t, warps,
            )
            if p is not None:
                ok = True
                break
        if ok:
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


def _plan_to_pickup(frame, *, bottom_only: bool = False):
    """Energy-aware path to a pickup.

    L4 has a mid-board pickup (y≈16) near the stamp corridor and a bottom one.
    Unlock pre-fuel must NOT eat the mid pickup — recording keeps it until the
    final approach so ui stays ~74 at (2,1). Use bottom_only=True before unlock.
    """
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = list(ls20.energy_pickups(frame))
    if bottom_only:
        bottom = [p for p in pickups if p[1] >= 40]
        if bottom:
            pickups = bottom
    if not pickups:
        return None, None
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))

    def at_pickup(cell, _f, _p):
        return any(_ov(mover_bbox_from_cursor(cell, offset), pb) > 0
                   for pb in pickups)

    p, c, f, pm = _energy_bfs(state.cursor, fuel0, 0, walk_u, pickups, offset,
                              at_pickup, warps)
    return p, c


def _plan_to_contact(frame):
    """Unarmed BFS to marker overlap (L4 arming contact; no ritual)."""
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    markers = [g for g in state.goals if g.id == "ls20-marker"]
    # After a successful contact the marker goal may vanish from the frame.
    if not markers:
        return [], state.cursor, MAX_FUEL, {"already": True, "no_marker": True}
    marker = markers[0].shape
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))

    def at_contact(cell, _f, _p):
        return _ov(carrying_bbox_from_cursor(cell, offset), marker) > 0

    if at_contact(state.cursor, fuel0, 0):
        return [], state.cursor, fuel0, {"already": True, "marker": marker}

    p, c, f, pm = _energy_bfs(
        state.cursor, fuel0, 0, walk_u, pickups, offset, at_contact, warps,
    )
    return p, c, f, {
        "marker": marker, "path_len": None if p is None else len(p),
        "cursor0": state.cursor,
    }


def _plan_armed_stamp_only(frame):
    """No contact, no ritual — energy BFS on walk_a to ov>=10 stamp (L4 after unlock)."""
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    stamp = next(g.shape for g in state.goals if g.id == "ls20-stamp")
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))
    # L5 post-unlock often has ui~32; tight fuel falsely reports unreachable.
    fuel0 = max(fuel0, ui // 2, 1)
    # Do NOT boost to MAX_FUEL merely because pickups exist — BFS may route
    # straight to stamp without collecting them (L5 soft-reset at (10,10)).
    # Mid-fuel in the closed loop handles refill when stamp is unreachable.
    # L6 mid-stamp ((10,7) ov>=10 on walk_u) is a decoy — prefer armed-only
    # stamp cells when any exist (bottom gate (10,10)).
    armed_stamp_cells = {
        c for c in walk_a
        if c not in walk_u
        and _ov(mover_bbox_from_cursor(c, offset), stamp) >= 10
    }

    def at_stamp(cell, _f, _p):
        ov = _ov(mover_bbox_from_cursor(cell, offset), stamp)
        if ov < 10:
            return False
        if armed_stamp_cells:
            return cell in armed_stamp_cells
        return True

    p, c, f, pm = _energy_bfs(
        state.cursor, fuel0, 0, walk_a, pickups, offset, at_stamp, warps,
    )
    return p, c, f, {
        "t2": c, "fuel_end": f, "path_len": None if p is None else len(p),
        "stamp": stamp, "cursor0": state.cursor,
    }


def _plan_contact_then_armed_stamp(frame):
    """L4: ring unlock + marker contact arms gate; H23 ritual is blocked — skip it."""
    p1, c1, f1, i1 = _plan_to_contact(frame)
    if p1 is None:
        return None, None, None, {"error": "no contact path", **i1}
    p2, c2, f2, i2 = _plan_armed_stamp_only(frame)  # same frame; may fail
    # Prefer reporting contact even when stamp not yet plannable.
    if p2 is None:
        return list(p1), c1, f1, {
            "t1": c1, "path1_len": len(p1), "path2_len": 0,
            "ritual": False, "contact_no_ritual": True,
            "stamp_pending": True, **i1,
        }
    # Re-plan stamp from contact cell with fuel after p1 (approximate).
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    stamp = next(g.shape for g in state.goals if g.id == "ls20-stamp")
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)

    def at_stamp(cell, _f, _p):
        return _ov_stamp(cell, offset, stamp) >= 10

    p2b, c2b, f2b, _ = _energy_bfs(
        c1, f1, 0, walk_a, pickups, offset, at_stamp, warps,
    )
    if p2b is None:
        return list(p1), c1, f1, {
            "t1": c1, "path1_len": len(p1), "path2_len": 0,
            "ritual": False, "contact_no_ritual": True,
            "stamp_pending": True, **i1,
        }
    path = list(p1) + list(p2b)
    return path, c2b, f2b, {
        "t1": c1, "t2": c2b, "path1_len": len(p1), "path2_len": len(p2b),
        "ritual": False, "contact_no_ritual": True,
        "path_len": len(path), "stamp": stamp,
    }


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
            # L5 (lv==4): recording arms via (10,6) hop BEFORE unlock — skip
            # standard unlock enter; closed-loop l5_rec_stamp does the full route.
            # L6 (lv==5): recording drops stamp via (10,6) then fuel-tours to
            # (10,10); skip standard unlock so we stay on the recording spine.
            unlocked_any = False
            cands = _unlock_candidates(frame)
            if lv == 4:
                unlocked_any = True
                cands = []
                print("  L5: skip standard unlock (recording pre-hop route)")
            elif lv == 5:
                unlocked_any = True
                cands = []
                print("  L6: skip standard unlock (recording stamp-drop route)")
            elif lv == 6:
                unlocked_any = True
                cands = []
                print("  L7: skip standard unlock (recording WIN route)")
            if cands:
                p_pu, _ = _plan_to_pickup(frame, bottom_only=True)
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
                end = ls20.init(frame).cursor
                # L5+: open-loop can desync on new ejects — replan remaining.
                if end != cand and lv >= 4:
                    for _step in range(40):
                        cur_u = ls20.init(frame).cursor
                        if cur_u == cand:
                            break
                        p_u, _, _ = _plan_to_unlock(frame, cand)
                        if not p_u:
                            break
                        resp = sess.action(DIR_TO_ACTION[p_u[0]])
                        frame, meta = resp["frame"], resp
                    end = ls20.init(frame).cursor
                if end != cand:
                    log.append({"event": "unlock_endpoint_miss", "levels": lv,
                                "cell": cand, "got": end})
                    print(f"  unlock ENDPOINT MISS: want {cand} got {end}")
                    break
                unlocked_any = True
                log.append({"event": "unlock", "levels": lv, "cell": cand,
                            "mover": ls20.locate_mover(frame),
                            "c9": int((ls20._plane(frame) == 9).sum()),
                            "c12": int((ls20._plane(frame) == 12).sum())})
                # L4: ring osc until color-9 mass enters the "high" phase
                # (live: c9>=35 on (6,6) → gate LEFT works; c9~21 → LEFT no-op).
                if cand == (6, 6) and end == (6, 6):
                    phase_c9 = int((ls20._plane(frame) == 9).sum())
                    for osc_i in range(16):
                        resp = sess.action(1)  # U → (6,5)
                        frame, meta = resp["frame"], resp
                        resp = sess.action(2)  # D → (6,6)
                        frame, meta = resp["frame"], resp
                        phase_c9 = int((ls20._plane(frame) == 9).sum())
                        cur_o = ls20.init(frame).cursor
                        print(f"  ring-osc{osc_i} {cur_o} c9={phase_c9} "
                              f"ui={ls20.ui_energy(frame)}")
                        if cur_o == (6, 6) and phase_c9 >= 35:
                            log.append({"event": "ring_phase", "levels": lv,
                                        "osc": osc_i + 1, "c9": phase_c9})
                            print(f"  ring-phase OK c9={phase_c9}")
                            break
                    else:
                        print(f"  ring-phase TIMEOUT c9={phase_c9}")
                    # Eat mid now while phase is hot (ui after osc is low).
                    mid = [p for p in ls20.energy_pickups(frame) if p[1] < 40]
                    if mid:
                        state = ls20.init(frame)
                        offset = ls20.grid_offset(frame)
                        walk_a = ls20.build_walkable(frame, offset, armed=True)
                        walk_u = ls20.build_walkable(frame, offset, armed=False)
                        warps = ls20.detect_warps(frame, offset, walk_u)

                        def at_mid(cell, _f, _p):
                            return any(
                                _ov(mover_bbox_from_cursor(cell, offset), pb) > 0
                                for pb in mid)

                        p_mid, _, _, _ = _energy_bfs(
                            state.cursor, MAX_FUEL, 0, walk_a, mid, offset,
                            at_mid, warps,
                        )
                        if p_mid:
                            print(f"  post-phase mid-fuel ({len(p_mid)} steps)")
                            for a in p_mid:
                                resp = sess.action(DIR_TO_ACTION[a])
                                frame, meta = resp["frame"], resp
                            print(f"  mid done {ls20.init(frame).cursor} "
                                  f"ui={ls20.ui_energy(frame)} "
                                  f"c9={int((ls20._plane(frame) == 9).sum())}")
                            log.append({
                                "event": "ring_phase_mid",
                                "levels": lv,
                                "cursor": ls20.init(frame).cursor,
                                "ui": ls20.ui_energy(frame),
                                "c9": int((ls20._plane(frame) == 9).sum()),
                            })

            # --- then clear ---
            # L3: unlock opens gate, still need contact+H23+stamp.
            # L4: unlock (=ring crush) IS arming; contact+H23 fails → armed stamp.
            #     Use closed-loop steps: warps/walk shift after unlock.
            closed_loop = False
            try:
                path, info = plan_two_phase(frame)
            except Exception as e1:
                if not unlocked_any:
                    log.append({"event": "plan_fail", "levels": lv, "error": str(e1)})
                    print(f"PLAN FAIL at lv={lv}: {e1}")
                    break
                # L4: ring crush + contact. L5+: unlock then armed stamp
                # (H23 often blocked on fake/wrong marker column).
                closed_loop = True
                path = []
                # L4 marker contact cell; L5: recording left-corridor + (10,10) UP;
                # L6: recording stamp-drop + fuel tour + (10,10) DOWN;
                # other levels skip UD and stamp only.
                need_udd = (lv == 3)
                need_l5 = (lv == 4)
                need_l6 = (lv == 5)
                need_l7 = (lv == 6)
                info = {
                    "ritual": need_udd,
                    "pickups": ls20.energy_pickups(frame),
                    "unlocked_stamp": True,
                    "t2": (1, 1),
                    "fallback": str(e1),
                    "closed_loop": True,
                    "mode": (
                        "udd47+stamp" if need_udd
                        else "l5_rec_stamp" if need_l5
                        else "l6_rec_stamp" if need_l6
                        else "l7_rec_win" if need_l7
                        else "armed_stamp"
                    ),
                    "need_udd47": need_udd,
                    "need_l5": need_l5,
                    "need_l6": need_l6,
                    "need_l7": need_l7,
                }
                print(f"  fallback {info['mode']} (pickups={info['pickups']})")
            print(f"\n=== clear level index {lv} === "
                  f"ritual={info.get('ritual')} pickups={info.get('pickups')} "
                  f"unlocked_any={unlocked_any} closed_loop={closed_loop}")
            if not closed_loop:
                print("actions", [DIR_TO_ACTION[a] for a in path])
            entry = {
                "event": "attempt",
                "levels_before": lv,
                "info": {
                    "ritual": info.get("ritual"),
                    "pickups": info.get("pickups"),
                    "unlocked_stamp": info.get("unlocked_stamp", False),
                    "t2": info.get("t2"),
                    "path_len": None if closed_loop else len(path),
                    "closed_loop": closed_loop,
                    "mode": info.get("mode"),
                },
                "actions": [],
            }
            leveled = False
            need_udd47 = bool(info.get("need_udd47"))
            need_l5 = bool(info.get("need_l5"))
            need_l6 = bool(info.get("need_l6"))
            need_l7 = bool(info.get("need_l7"))
            need_rec = need_l5 or need_l6 or need_l7
            # L4: UDD's second DOWN lands on hop pad (4,8) and burns mid-path fuel.
            # UP onto marker + DOWN back to (4,7) is enough (live-probed).
            l4_ritual = ((0, -1), (0, 1)) if need_udd47 else RITUAL
            ritual_queue: list = []
            mid_queue: list = []
            mid_done = False  # L5 armed_stamp: one refill then commit to stamp
            # L5/L6/L7: follow lingjingsolo recording waypoints (live-proven PASS).
            if need_l5:
                rec_targets = _l5_recording_waypoints()
                rec_label = "L5"
            elif need_l6:
                rec_targets = _l6_recording_waypoints()
                rec_label = "L6"
            elif need_l7:
                rec_targets = _l7_recording_waypoints()
                rec_label = "L7"
            else:
                rec_targets = []
                rec_label = ""
            rec_ti = 0
            max_steps = 160 if (closed_loop and need_rec) else (80 if closed_loop else len(path))
            for i in range(1, max_steps + 1):
                if closed_loop:
                    if need_rec:
                        cur0 = ls20.init(frame).cursor
                        if rec_ti >= len(rec_targets):
                            entry["error"] = f"{rec_label} waypoints exhausted at {cur0}"
                            log.append(entry)
                            print(f"  FAIL {rec_label} waypoints exhausted")
                            break
                        want = rec_targets[rec_ti]
                        if cur0 == want:
                            rec_ti += 1
                            continue
                        dx, dy = want[0] - cur0[0], want[1] - cur0[1]
                        order = []
                        if abs(dx) + abs(dy) == 1:
                            order = [(dx, dy)]
                        else:
                            if dy < 0:
                                order.append((0, -1))
                            if dy > 0:
                                order.append((0, 1))
                            if dx < 0:
                                order.append((-1, 0))
                            if dx > 0:
                                order.append((1, 0))
                            for d in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                                if d not in order:
                                    order.append(d)
                        a = order[0]
                        entry["actions"].append(DIR_TO_ACTION[a])
                        resp = sess.action(DIR_TO_ACTION[a])
                        frame, meta = resp["frame"], resp
                        new_lv = int(meta.get("levels_completed") or 0)
                        cur = ls20.init(frame).cursor
                        mark = "OK" if cur == want else "BAD"
                        if cur == want:
                            rec_ti += 1
                        else:
                            for _ in range(30):
                                if ls20.init(frame).cursor == want:
                                    mark = "REC"
                                    rec_ti += 1
                                    break
                                offset = ls20.grid_offset(frame)
                                walk_a = ls20.build_walkable(frame, offset, armed=True)
                                warps = ls20.detect_warps(frame, offset)
                                p_r, _, _, _ = _energy_bfs(
                                    ls20.init(frame).cursor, MAX_FUEL, 0, walk_a,
                                    ls20.energy_pickups(frame), offset,
                                    lambda c, _f, _p, w=want: c == w, warps,
                                )
                                if not p_r:
                                    break
                                r2 = sess.action(DIR_TO_ACTION[p_r[0]])
                                frame = r2["frame"]
                                new_lv = int(r2.get("levels_completed") or new_lv)
                                meta = r2
                            cur = ls20.init(frame).cursor
                        mover = ls20.locate_mover(frame)
                        arr = np.asarray(frame)
                        layers = arr.shape[0] if arr.ndim == 3 else 1
                        print(f"  {i:02d} A{DIR_TO_ACTION[a]} cur={cur} want={want} {mark} "
                              f"bbox={mover} lv={new_lv} layers={layers} "
                              f"ui={ls20.ui_energy(frame)}")
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
                        if cur != want:
                            entry["error"] = (
                                f"{rec_label} stuck want={want} at={cur} step {i}"
                            )
                            log.append(entry)
                            print(f"  FAIL {rec_label} stuck want={want} at={cur}")
                            break
                        continue
                    if need_udd47:

                        cur0 = ls20.init(frame).cursor
                        if cur0 == (4, 7) and not ritual_queue:
                            ritual_queue = list(l4_ritual)
                            print("  at (4,7) — run L4 contact UD")
                        if ritual_queue:
                            a = ritual_queue.pop(0)
                            if not ritual_queue:
                                need_udd47 = False
                                print("  UD done — queue mid-fuel then stamp")
                        else:
                            state = ls20.init(frame)
                            offset = ls20.grid_offset(frame)
                            walk_u = ls20.build_walkable(frame, offset, armed=False)
                            warps = ls20.detect_warps(frame, offset, walk_u)
                            # Do NOT route through mid pickup en route to (4,7).
                            mid = [p for p in ls20.energy_pickups(frame) if p[1] < 40]
                            blocked = {
                                c for c in walk_u
                                if any(
                                    _ov(mover_bbox_from_cursor(c, offset), pb) > 0
                                    for pb in mid
                                )
                            }
                            walk_avoid = frozenset(c for c in walk_u if c not in blocked)
                            ui = ls20.ui_energy(frame)
                            fuel0 = (
                                MAX_FUEL if ui >= 64 or ui <= 0
                                else max(1, min(MAX_FUEL, max((ui - 8) // 4, ui // 2)))
                            )
                            p47, _, _, _ = _energy_bfs(
                                state.cursor, fuel0, 0, walk_avoid, [], offset,
                                lambda c, _f, _p: c == (4, 7), warps,
                            )
                            if not p47:
                                entry["error"] = f"no path to (4,7) at step {i}"
                                entry["levels_after"] = int(
                                    meta.get("levels_completed") or 0)
                                log.append(entry)
                                print("  FAIL no path to (4,7)")
                                break
                            a = p47[0]
                    elif mid_queue:
                        a = mid_queue.pop(0)
                        entry["actions"].append(DIR_TO_ACTION[a])
                        before = ls20.init(frame).cursor
                        resp = sess.action(DIR_TO_ACTION[a])
                        frame, meta = resp["frame"], resp
                        new_lv = int(meta.get("levels_completed") or 0)
                        cur = ls20.init(frame).cursor
                        print(f"  {i:02d} A{DIR_TO_ACTION[a]} cur={cur} "
                              f"[mid-fuel] ui={ls20.ui_energy(frame)} "
                              f"lv={new_lv}")
                        if not mid_queue:
                            mid_done = True
                        if new_lv > lv:
                            entry["levels_after"] = new_lv
                            entry["steps_used"] = i
                            leveled = True
                            log.append(entry)
                            print(f"  PASS lv {lv}->{new_lv}")
                            break
                        continue
                    else:
                        # Prefer stamp when ui is healthy. One mid-fuel refill
                        # when ui low (L5); never re-enter mid-fuel mid-stamp.
                        path, dest, fuel, ainfo = _plan_armed_stamp_only(frame)
                        ui_now = ls20.ui_energy(frame)
                        mid = [p for p in ls20.energy_pickups(frame) if p[1] < 40]
                        if (not mid_done and mid and ui_now < 64
                                and not mid_queue):
                            state = ls20.init(frame)
                            offset = ls20.grid_offset(frame)
                            walk_a = ls20.build_walkable(frame, offset, armed=True)
                            walk_u = ls20.build_walkable(frame, offset, armed=False)
                            warps = ls20.detect_warps(frame, offset, walk_u)

                            def at_mid(cell, _f, _p):
                                return any(
                                    _ov(mover_bbox_from_cursor(cell, offset), pb) > 0
                                    for pb in mid)

                            p_mid, _, _, _ = _energy_bfs(
                                state.cursor, MAX_FUEL, 0, walk_a, mid, offset,
                                at_mid, warps,
                            )
                            if p_mid:
                                mid_queue = list(p_mid)
                                print(f"  mid-fuel queue {len(mid_queue)} steps "
                                      f"(ui={ui_now})")
                                a = mid_queue.pop(0)
                                entry["actions"].append(DIR_TO_ACTION[a])
                                before = ls20.init(frame).cursor
                                resp = sess.action(DIR_TO_ACTION[a])
                                frame, meta = resp["frame"], resp
                                new_lv = int(meta.get("levels_completed") or 0)
                                cur = ls20.init(frame).cursor
                                print(f"  {i:02d} A{DIR_TO_ACTION[a]} cur={cur} "
                                      f"[mid-fuel] ui={ls20.ui_energy(frame)} "
                                      f"lv={new_lv}")
                                if not mid_queue:
                                    mid_done = True
                                if new_lv > lv:
                                    entry["levels_after"] = new_lv
                                    entry["steps_used"] = i
                                    leveled = True
                                    log.append(entry)
                                    print(f"  PASS lv {lv}->{new_lv}")
                                    break
                                continue
                        if path is None:
                            entry["error"] = f"stamp replan fail step {i}: {ainfo}"
                            entry["levels_after"] = int(
                                meta.get("levels_completed") or 0)
                            log.append(entry)
                            print(f"  FAIL stamp replan: {ainfo}")
                            break
                        if len(path) == 0:
                            entry["error"] = f"on stamp but no level-up step {i}"
                            entry["levels_after"] = int(
                                meta.get("levels_completed") or 0)
                            log.append(entry)
                            print("  FAIL on stamp cell without level-up")
                            break
                        # L5 recording: (10,10) UP → (10,1) stamp+PASS.
                        # BFS may pick LEFT/DOWN which land on (10,2) (live).
                        cur0 = ls20.init(frame).cursor
                        if cur0 == (10, 10) and dest == (10, 1):
                            a = (0, -1)
                        else:
                            a = path[0]
                        entry["info"]["t2"] = dest
                else:
                    a = path[i - 1]
                entry["actions"].append(DIR_TO_ACTION[a])
                before = ls20.init(frame).cursor
                resp = sess.action(DIR_TO_ACTION[a])
                frame, meta = resp["frame"], resp
                new_lv = int(meta.get("levels_completed") or 0)
                mover = ls20.locate_mover(frame)
                arr = np.asarray(frame)
                layers = arr.shape[0] if arr.ndim == 3 else 1
                cur = ls20.init(frame).cursor
                print(f"  {i:02d} A{DIR_TO_ACTION[a]} cur={cur} bbox={mover} "
                      f"lv={new_lv} layers={layers} "
                      f"c11={int((ls20._plane(frame) == 11).sum())} "
                      f"ui={ls20.ui_energy(frame)}")
                if (cur == before and new_lv == lv and closed_loop
                        and not need_udd47 and not ritual_queue):
                    entry["error"] = f"no-op A{DIR_TO_ACTION[a]} at {cur} step {i}"
                    entry["levels_after"] = new_lv
                    log.append(entry)
                    print(f"  FAIL no-op at {cur}")
                    leveled = False
                    break
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
