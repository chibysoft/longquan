"""Trace L5 unlock to (5,5) step-by-step after seated L4 clear."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import mover_bbox_from_cursor
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, _step_cell
from tools.ls20_seated_clear_full import (
    _ov,
    _plan_armed_stamp_only,
    _plan_to_pickup,
    _plan_to_unlock,
    _sync_after_levelup,
    _unlock_candidates,
)
from tools.ls20_l4_unlock_trace import advance_to_l4_pre_unlock


def clear_l4(sess):
    frame, _ = advance_to_l4_pre_unlock(sess)
    p, _, _ = _plan_to_unlock(frame, (6, 6))
    for a in p:
        frame = sess.action(DIR_TO_ACTION[a])["frame"]
    for _ in range(16):
        frame = sess.action(1)["frame"]
        frame = sess.action(2)["frame"]
        if (ls20.init(frame).cursor == (6, 6)
                and int((ls20._plane(frame) == 9).sum()) >= 35):
            break
    offset = ls20.grid_offset(frame)
    mid = [p for p in ls20.energy_pickups(frame) if p[1] < 40]
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    warps = ls20.detect_warps(frame, offset)

    def at_mid(c, _f, _p):
        return any(_ov(mover_bbox_from_cursor(c, offset), pb) > 0 for pb in mid)

    pm, _, _, _ = _energy_bfs(
        ls20.init(frame).cursor, MAX_FUEL, 0, walk_a, mid, offset, at_mid, warps,
    )
    for a in pm or []:
        frame = sess.action(DIR_TO_ACTION[a])["frame"]
    p47, _, _, _ = _energy_bfs(
        ls20.init(frame).cursor, MAX_FUEL, 0,
        ls20.build_walkable(frame, ls20.grid_offset(frame), armed=False),
        [], ls20.grid_offset(frame),
        lambda c, _f, _p: c == (4, 7),
        ls20.detect_warps(frame, ls20.grid_offset(frame)),
    )
    for a in p47 or []:
        frame = sess.action(DIR_TO_ACTION[a])["frame"]
    for a in ((0, -1), (0, 1)):
        frame = sess.action(DIR_TO_ACTION[a])["frame"]
    for _ in range(40):
        path, _, _, _ = _plan_armed_stamp_only(frame)
        if not path:
            break
        r = sess.action(DIR_TO_ACTION[path[0]])
        frame = r["frame"]
        if int(r.get("levels_completed") or 0) >= 4:
            break
    return _sync_after_levelup(sess, frame)


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l5_unlock_trace"])
        frame, meta = clear_l4(sess)
        print("L5", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame),
              "cands", _unlock_candidates(frame))
        ppu, _ = _plan_to_pickup(frame, bottom_only=True)
        print("prefuel", ppu)
        for a in ppu or []:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        print("after fuel", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        offset = ls20.grid_offset(frame)
        warps = ls20.detect_warps(frame, offset)
        print("eject75", warps.get(((7, 5), (-1, 0))),
              "eject65", warps.get(((6, 5), (-1, 0))))
        for i in range(30):
            cur = ls20.init(frame).cursor
            if cur == (5, 5):
                print("REACHED", cur)
                break
            p, _, _ = _plan_to_unlock(frame, (5, 5))
            if not p:
                print("NO_PLAN at", cur)
                break
            a = p[0]
            wa = ls20.build_walkable(frame, ls20.grid_offset(frame), armed=True)
            warps = ls20.detect_warps(frame, ls20.grid_offset(frame))
            pred = _step_cell(cur, a, wa, warps)
            r = sess.action(DIR_TO_ACTION[a])
            live = ls20.init(r["frame"]).cursor
            print(f"{i:02d} {cur} {a} pred={pred} live={live} "
                  f"{'OK' if live == pred else 'BAD'} warp={warps.get((cur, a))} "
                  f"rest={len(p)-1}")
            frame = r["frame"]
            if live != pred:
                # continue anyway with replan
                pass
        print("final", ls20.init(frame).cursor,
              "cands", _unlock_candidates(frame))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
