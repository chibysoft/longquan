"""Follow recording L4 cursor waypoints after unlock; try clear at end."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, RITUAL, plan_two_phase
from tools.ls20_seated_clear_full import (
    _plan_to_pickup, _plan_to_unlock, _sync_after_levelup, _unlock_candidates,
    _plan_armed_stamp_only,
)
from tools.ls20_l4_stamp9_probe import stamp9

# Recording cursors i109..i139 (unique progression)
WAYPOINTS = [
    (6, 6), (6, 5), (6, 6), (6, 5), (6, 6), (6, 5), (6, 4),
    (9, 4), (8, 4), (8, 8), (6, 9), (5, 9), (4, 9), (4, 8),
    (1, 7), (4, 6), (4, 7), (4, 8), (2, 8), (2, 7), (2, 6),
    (2, 5), (2, 4), (3, 4), (3, 3), (4, 3), (4, 2), (4, 1),
    (3, 1), (2, 1), (1, 1),
]


def boot(sess):
    resp = sess.reset()
    frame, meta = resp["frame"], resp
    while int(meta.get("levels_completed") or 0) < 3:
        lv = int(meta.get("levels_completed") or 0)
        for cand in _unlock_candidates(frame):
            p_pu, _ = _plan_to_pickup(frame, bottom_only=True)
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
    p_pu, _ = _plan_to_pickup(frame, bottom_only=True)
    if p_pu:
        for a in p_pu:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
    p, _, _ = _plan_to_unlock(frame, (6, 6))
    for a in p:
        resp = sess.action(DIR_TO_ACTION[a])
        frame, meta = resp["frame"], resp
    return frame, meta


def step_toward(frame, goal, armed=True):
    state = ls20.init(frame)
    if state.cursor == goal:
        return None
    offset = ls20.grid_offset(frame)
    walk = ls20.build_walkable(frame, offset, armed=armed)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))
    # try armed then unarmed
    for w in (walk, walk_u):
        p, _, _, _ = _energy_bfs(
            state.cursor, fuel0, 0, w, pickups, offset,
            lambda c, _f, _p: c == goal, warps,
        )
        if p:
            return p[0]
    return None


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_rec_waypoints"])
        frame, meta = boot(sess)
        print("start", ls20.init(frame).cursor, ls20.energy_pickups(frame))
        # insert UDD when first at (4,7) area
        did_ritual = False
        for wi, wp in enumerate(WAYPOINTS):
            for _ in range(25):
                cur = ls20.init(frame).cursor
                if cur == wp:
                    break
                if cur == (4, 7) and not did_ritual:
                    for a in RITUAL:
                        resp = sess.action(DIR_TO_ACTION[a])
                        frame, meta = resp["frame"], resp
                    did_ritual = True
                    print("H23 at", ls20.init(frame).cursor)
                    continue
                a = step_toward(frame, wp, armed=True)
                if a is None:
                    a = step_toward(frame, wp, armed=False)
                if a is None:
                    print("stuck going to", wp, "from", cur)
                    break
                before = cur
                resp = sess.action(DIR_TO_ACTION[a])
                frame, meta = resp["frame"], resp
                if int(meta.get("levels_completed") or 0) >= 4:
                    print("CLEARED en route", wp)
                    return
                if ls20.init(frame).cursor == before:
                    print("noop", before, "to", wp)
                    break
            print(f"wp{wi}", wp, "at", ls20.init(frame).cursor,
                  "ui", ls20.ui_energy(frame), "s9", stamp9(frame)[0],
                  "lv", meta.get("levels_completed"))
            if int(meta.get("levels_completed") or 0) >= 4:
                print("CLEARED")
                return
        # final stamp attempts
        for i in range(10):
            path, _, _, _ = _plan_armed_stamp_only(frame)
            if not path:
                break
            resp = sess.action(DIR_TO_ACTION[path[0]])
            frame, meta = resp["frame"], resp
            print("fin", ls20.init(frame).cursor, meta.get("levels_completed"),
                  ls20.ui_energy(frame))
            if int(meta.get("levels_completed") or 0) >= 4:
                print("CLEARED")
                return
        print("FAIL")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
