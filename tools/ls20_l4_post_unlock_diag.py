"""Diagnose post-(6,6)-unlock walk/warps/armed-stamp plan (one-shot online)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import mover_bbox_from_cursor
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import (
    MAX_FUEL, _energy_bfs, _ov, _step_cell, plan_two_phase,
)
from tools.ls20_seated_clear_full import (
    _plan_armed_stamp_only, _plan_to_pickup, _plan_to_unlock, _unlock_candidates,
    _sync_after_levelup,
)


def _nbr(frame, cell=None):
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    cur = cell or state.cursor
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    rows = []
    for d in DIRS:
        rows.append({
            "d": d, "aid": DIR_TO_ACTION[d],
            "warp": warps.get((cur, d)),
            "step": _step_cell(cur, d, walk_a, warps),
        })
    return {
        "cursor": cur, "ui": ls20.ui_energy(frame),
        "gate_u": (1, 1) in walk_u, "gate_a": (1, 1) in walk_a,
        "nbr": rows, "n_warps": len(warps),
    }


def main():
    key = _api_key()
    sess = OnlineSession(key)
    log = []
    try:
        sess.open(tags=["ls20_l4_post_unlock_diag"])
        reset = sess.reset()
        frame, meta = reset["frame"], reset
        # burn L1-L3 via seated full logic (compact)
        from tools.ls20_seated_clear_full import run_online
        # inline: advance to lv=3 with unlock+clear like full
        while int(meta.get("levels_completed") or 0) < 3:
            lv = int(meta.get("levels_completed") or 0)
            for cand in _unlock_candidates(frame):
                p_pu, _ = _plan_to_pickup(frame)
                if p_pu:
                    for a in p_pu:
                        resp = sess.action(DIR_TO_ACTION[a])
                        frame, meta = resp["frame"], resp
                p, _, _ = _plan_to_unlock(frame, cand)
                if p:
                    for a in p:
                        resp = sess.action(DIR_TO_ACTION[a])
                        frame, meta = resp["frame"], resp
            path, info = plan_two_phase(frame)
            for a in path:
                resp = sess.action(DIR_TO_ACTION[a])
                frame, meta = resp["frame"], resp
                if int(meta.get("levels_completed") or 0) > lv:
                    break
            if int(meta.get("levels_completed") or 0) > lv:
                frame, meta = _sync_after_levelup(sess, frame)
            else:
                log.append({"fail_before_l4": meta})
                break
        log.append({"at_l4": _nbr(frame), "lv": meta.get("levels_completed")})
        # unlock (6,6)
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            for a in p_pu:
                resp = sess.action(DIR_TO_ACTION[a])
                frame, meta = resp["frame"], resp
        p, _, _ = _plan_to_unlock(frame, (6, 6))
        log.append({"unlock_plan_len": None if p is None else len(p)})
        for a in (p or []):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
        log.append({"post_unlock": _nbr(frame), "mover": ls20.locate_mover(frame)})
        # plans
        try:
            plan_two_phase(frame)
            log.append({"two_phase": "ok"})
        except Exception as e:
            log.append({"two_phase": str(e)})
        path, dest, fuel, info = _plan_armed_stamp_only(frame)
        acts = None if path is None else [DIR_TO_ACTION[a] for a in path]
        log.append({"armed_stamp": {"path": acts, "dest": dest, "info": info}})
        # simulate predicted steps
        if path:
            state = ls20.init(frame)
            offset = ls20.grid_offset(frame)
            walk_a = ls20.build_walkable(frame, offset, armed=True)
            walk_u = ls20.build_walkable(frame, offset, armed=False)
            warps = ls20.detect_warps(frame, offset, walk_u)
            cur = state.cursor
            sim = []
            for a in path:
                nxt = _step_cell(cur, a, walk_a, warps)
                sim.append({"a": DIR_TO_ACTION[a], "from": cur, "to": nxt})
                if nxt is None:
                    break
                cur = nxt
            log.append({"sim": sim})
    finally:
        try:
            sess.close()
        except Exception:
            pass
    out = ROOT / "docs" / "ls20_l4_post_unlock_diag.md"
    out.write_text(
        "# post-unlock diag\n\n" + "\n".join(f"- `{json.dumps(x, default=str)}`" for x in log),
        encoding="utf-8",
    )
    print(out)
    for x in log:
        print(x)


if __name__ == "__main__":
    main()
