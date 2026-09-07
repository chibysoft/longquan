"""Unlock → ring osc N× → mid → (4,7) UD → stamp → LEFT at (2,1)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import mover_bbox_from_cursor
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, _ov
from tools.ls20_seated_clear_full import _plan_to_unlock, _unlock_candidates
from tools.ls20_l4_unlock_trace import advance_to_l4_pre_unlock
from tools.ls20_l4_stamp9_probe import stamp9


def _fuel(ui: int) -> int:
    if ui >= 64 or ui <= 0:
        return MAX_FUEL
    return max(1, min(MAX_FUEL, max((ui - 8) // 4, ui // 2)))


def _bfs_to(frame, goal, *, armed: bool, avoid_mid: bool = False, fuel0=None):
    offset = ls20.grid_offset(frame)
    walk = ls20.build_walkable(frame, offset, armed=armed)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = list(ls20.energy_pickups(frame))
    if avoid_mid:
        mid = [p for p in pickups if p[1] < 40]
        blocked = {
            c for c in walk
            if any(_ov(mover_bbox_from_cursor(c, offset), pb) > 0 for pb in mid)
        }
        walk = frozenset(c for c in walk if c not in blocked)
        pickups = []
    ui = ls20.ui_energy(frame)
    if fuel0 is None:
        fuel0 = _fuel(ui)
    p, _, _, _ = _energy_bfs(
        ls20.init(frame).cursor, fuel0, 0, walk, pickups, offset,
        lambda c, _f, _p: c == goal, warps,
    )
    return p


def _bfs_mid(frame):
    offset = ls20.grid_offset(frame)
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    warps = ls20.detect_warps(frame, offset, ls20.build_walkable(frame, offset, armed=False))
    mid = [p for p in ls20.energy_pickups(frame) if p[1] < 40]
    if not mid:
        return None

    def at_mid(cell, _f, _p):
        return any(_ov(mover_bbox_from_cursor(cell, offset), pb) > 0 for pb in mid)

    p, _, _, _ = _energy_bfs(
        ls20.init(frame).cursor, MAX_FUEL, 0, walk_a, mid, offset, at_mid, warps,
    )
    return p


def _exec(sess, frame, path, tag=""):
    for a in path or []:
        resp = sess.action(DIR_TO_ACTION[a])
        frame = resp["frame"]
        if tag:
            print(f"  {tag}", a, ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
    return frame, resp if path else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--osc", type=int, default=3, help="full U-D cycles on ring")
    ap.add_argument("--mid-first", action="store_true",
                    help="eat mid before osc (keeps fuel for osc+gate)")
    args = ap.parse_args()

    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=[f"ls20_osc{args.osc}_gate"])
        frame, _ = advance_to_l4_pre_unlock(sess)
        p, _, _ = _plan_to_unlock(frame, (6, 6))
        frame, _ = _exec(sess, frame, p)
        cur = ls20.init(frame).cursor
        print("UNLOCK", cur, "ui", ls20.ui_energy(frame),
              "cands", _unlock_candidates(frame))
        if cur != (6, 6):
            print("FAIL unlock endpoint")
            return

        if args.mid_first:
            pm = _bfs_mid(frame)
            print("mid-first", pm)
            frame, _ = _exec(sess, frame, pm, "mid")
            print("after mid", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame),
                  "pu", ls20.energy_pickups(frame))
            # return to ring for osc
            p66 = _bfs_to(frame, (6, 6), armed=True, fuel0=MAX_FUEL)
            print("back66", p66)
            frame, _ = _exec(sess, frame, p66)
            print("at66", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))

        # oscillate (6,6) U->(6,5) D->(6,6)
        for i in range(args.osc):
            for aid, expect in ((1, (6, 5)), (2, (6, 6))):
                resp = sess.action(aid)
                frame = resp["frame"]
                got = ls20.init(frame).cursor
                print(f"osc{i}", "A" + str(aid), got, "ui", ls20.ui_energy(frame),
                      "c9", int((ls20._plane(frame) == 9).sum()),
                      "ok" if got == expect else f"WANT {expect}")
                if got != expect:
                    print("osc path broke")
                    return

        print("post-osc", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame),
              "cands", _unlock_candidates(frame),
              "wa66", (6, 6) in ls20.build_walkable(frame, ls20.grid_offset(frame), armed=True),
              "wu66", (6, 6) in ls20.build_walkable(frame, ls20.grid_offset(frame), armed=False))

        # mid if still present
        if any(p[1] < 40 for p in ls20.energy_pickups(frame)):
            # go to (4,7) avoiding mid, UD, then mid queue
            p47 = _bfs_to(frame, (4, 7), armed=False, avoid_mid=True, fuel0=MAX_FUEL)
            print("to47 avoid", p47)
            frame, _ = _exec(sess, frame, p47)
            print("at47", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
            for a in ((0, -1), (0, 1)):
                resp = sess.action(DIR_TO_ACTION[a])
                frame = resp["frame"]
                print("UD", a, ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
            pm = _bfs_mid(frame)
            print("mid-after-ud", pm)
            frame, _ = _exec(sess, frame, pm, "mid")
            print("fueled", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame),
                  "pu", ls20.energy_pickups(frame))
        else:
            p47 = _bfs_to(frame, (4, 7), armed=False, fuel0=MAX_FUEL)
            print("to47", p47)
            frame, _ = _exec(sess, frame, p47)
            print("at47", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
            for a in ((0, -1), (0, 1)):
                resp = sess.action(DIR_TO_ACTION[a])
                frame = resp["frame"]
                print("UD", a, ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))

        # to (2,1)
        for step in range(25):
            cur = ls20.init(frame).cursor
            if cur == (2, 1):
                break
            p21 = _bfs_to(frame, (2, 1), armed=True, fuel0=MAX_FUEL)
            if not p21:
                print("no path to 21 at", cur)
                break
            resp = sess.action(DIR_TO_ACTION[p21[0]])
            frame = resp["frame"]
            print(f"to21#{step}", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))

        cur = ls20.init(frame).cursor
        arr = np.asarray(frame)
        print("at21", cur, "ui", ls20.ui_energy(frame),
              "s9", stamp9(frame)[0], "carry", ls20.init(frame).carrying,
              "layers", arr.shape[0] if arr.ndim == 3 else 1,
              "cands", _unlock_candidates(frame))
        for t in range(3):
            before = ls20.init(frame).cursor
            resp = sess.action(3)
            frame = resp["frame"]
            after = ls20.init(frame).cursor
            arr = np.asarray(frame)
            lv = int(resp.get("levels_completed") or 0)
            print(f"LEFT{t}", before, "->", after, "lv", lv,
                  "layers", arr.shape[0] if arr.ndim == 3 else 1,
                  "ui", ls20.ui_energy(frame))
            if lv >= 4:
                print("CLEARED")
                return
            if after != before:
                print("MOVED")
                return
        print("NO_CLEAR")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
