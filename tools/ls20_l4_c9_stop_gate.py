"""Stop ring osc at target c9 band, then mid→UD→gate LEFT."""
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


def c9(frame):
    return int((ls20._plane(frame) == 9).sum())


def bfs_to(frame, goal, armed=True, avoid_mid=False):
    offset = ls20.grid_offset(frame)
    walk = ls20.build_walkable(frame, offset, armed=armed)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    picks = []
    if avoid_mid:
        mid = [p for p in ls20.energy_pickups(frame) if p[1] < 40]
        blocked = {
            c for c in walk
            if any(_ov(mover_bbox_from_cursor(c, offset), pb) > 0 for pb in mid)
        }
        walk = frozenset(c for c in walk if c not in blocked)
    p, _, _, _ = _energy_bfs(
        ls20.init(frame).cursor, MAX_FUEL, 0, walk, picks, offset,
        lambda c, _f, _p: c == goal, warps,
    )
    return p


def bfs_mid(frame):
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--want-c9-ge", type=int, default=35,
                    help="stop when on (6,6) and c9 >= this (high phase)")
    ap.add_argument("--want-c9-lt", type=int, default=0,
                    help="if >0, stop when on (6,6) and c9 < this (low phase)")
    ap.add_argument("--max-osc", type=int, default=16)
    args = ap.parse_args()

    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_c9_stop"])
        frame, _ = advance_to_l4_pre_unlock(sess)
        p, _, _ = _plan_to_unlock(frame, (6, 6))
        for a in p:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        print("UNLOCK", ls20.init(frame).cursor, "c9", c9(frame), "ui", ls20.ui_energy(frame))

        # keep mid for late fuel: osc first on low ui, then mid
        # actually ui=42; osc until phase then mid from ring
        stopped = False
        for i in range(args.max_osc):
            for aid in (1, 2):
                frame = sess.action(aid)["frame"]
                cur = ls20.init(frame).cursor
                n = c9(frame)
                print(f"osc{i} A{aid} {cur} c9={n} ui={ls20.ui_energy(frame)}")
                if cur != (6, 6):
                    continue
                if args.want_c9_lt > 0 and n < args.want_c9_lt:
                    stopped = True
                    break
                if args.want_c9_lt <= 0 and n >= args.want_c9_ge:
                    stopped = True
                    break
            if stopped:
                break
        print("stop", ls20.init(frame).cursor, "c9", c9(frame),
              "cands", _unlock_candidates(frame),
              "wu66", (6, 6) in ls20.build_walkable(
                  frame, ls20.grid_offset(frame), armed=False))

        # mid (still there if we didn't walk through)
        pm = bfs_mid(frame)
        print("mid path", pm)
        if pm:
            for a in pm:
                frame = sess.action(DIR_TO_ACTION[a])["frame"]
            print("mid", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame),
                  "c9", c9(frame))

        p47 = bfs_to(frame, (4, 7), armed=False, avoid_mid=False)
        print("p47", p47)
        for a in p47 or []:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        for a in ((0, -1), (0, 1)):
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        print("UD", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame), "c9", c9(frame))

        # late mid if still present
        pm = bfs_mid(frame)
        if pm:
            print("late mid", pm)
            for a in pm:
                frame = sess.action(DIR_TO_ACTION[a])["frame"]
            print("fueled", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))

        for step in range(35):
            cur = ls20.init(frame).cursor
            if cur == (2, 1):
                break
            p = bfs_to(frame, (2, 1), armed=True)
            if not p:
                print("no 21", cur, "ui", ls20.ui_energy(frame))
                break
            frame = sess.action(DIR_TO_ACTION[p[0]])["frame"]
            print(f"#{step}", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))

        cur = ls20.init(frame).cursor
        print("at", cur, "ui", ls20.ui_energy(frame), "s9", stamp9(frame)[0],
              "carry", ls20.init(frame).carrying, "c9", c9(frame),
              "cands", _unlock_candidates(frame))
        if cur != (2, 1):
            print("NOT_AT_21")
            return
        for t in range(3):
            resp = sess.action(3)
            frame = resp["frame"]
            after = ls20.init(frame).cursor
            lv = int(resp.get("levels_completed") or 0)
            arr = np.asarray(frame)
            print(f"L{t}", cur, "->", after, "lv", lv,
                  "layers", arr.shape[0] if arr.ndim == 3 else 1)
            if lv >= 4 or after == (1, 1):
                print("CLEARED")
                return
            if after != cur:
                print("MOVED_ELSE", after)
                return
        print("NO_CLEAR")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
