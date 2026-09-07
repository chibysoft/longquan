"""Post-eject-fix: neighbors along UUU path after unlock."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import plan_two_phase, _step_cell
from tools.ls20_seated_clear_full import (
    _plan_to_pickup, _plan_to_unlock, _unlock_candidates, _sync_after_levelup,
    _plan_armed_stamp_only,
)


def snap(frame, cell=None):
    st = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    cur = cell or st.cursor
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    nbr = []
    for d in DIRS:
        nbr.append({
            "aid": DIR_TO_ACTION[d],
            "warp": warps.get((cur, d)),
            "step": _step_cell(cur, d, walk_a, warps),
        })
    return {"cur": cur, "ui": ls20.ui_energy(frame), "nbr": nbr,
            "n_warps": len(warps), "66_in_u": (6, 6) in walk_u}


def to_l4(sess):
    resp = sess.reset()
    frame, meta = resp["frame"], resp
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
        path, _ = plan_two_phase(frame)
        for a in path:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            if int(meta.get("levels_completed") or 0) > lv:
                break
        frame, meta = _sync_after_levelup(sess, frame)
    return frame, meta


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_uuu_diag"])
        frame, meta = to_l4(sess)
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            for a in p_pu:
                resp = sess.action(DIR_TO_ACTION[a])
                frame, meta = resp["frame"], resp
        p, _, _ = _plan_to_unlock(frame, (6, 6))
        for a in p:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
        print("AT66", snap(frame))
        path, dest, fuel, info = _plan_armed_stamp_only(frame)
        print("PLAN", [DIR_TO_ACTION[a] for a in path], "dest", dest)
        # take UUU live and compare
        for i in range(3):
            pred = snap(frame)
            resp = sess.action(1)
            frame, meta = resp["frame"], resp
            arr = __import__("numpy").asarray(frame)
            print(f"U{i+1}", "pred_step_U", pred["nbr"][2],  # DIRS order L,R,U,D -> index 2 is U
                  "live", ls20.init(frame).cursor,
                  "layers", arr.shape[0] if arr.ndim == 3 else 1,
                  "mover", ls20.locate_mover(frame))
            print("  snap", snap(frame))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
