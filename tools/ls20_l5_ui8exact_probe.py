"""Hit (10,10) with exactly ui=8 then UP (recording)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs
from tools.ls20_seated_clear_full import _plan_to_pickup, _plan_to_unlock
from tools.ls20_l5_unlock_trace import clear_l4


def goto(frame, sess, target, max_steps=80):
    for _ in range(max_steps):
        if ls20.init(frame).cursor == target:
            return frame, True
        offset = ls20.grid_offset(frame)
        walk = ls20.build_walkable(frame, offset, armed=True)
        warps = ls20.detect_warps(frame, offset)
        path, _, _, _ = _energy_bfs(
            ls20.init(frame).cursor, MAX_FUEL, 0, walk, [], offset,
            lambda c, _f, _p: c == target, warps,
        )
        if not path:
            return frame, False
        frame = sess.action(DIR_TO_ACTION[path[0]])["frame"]
    return frame, ls20.init(frame).cursor == target


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l5_ui8exact"])
        frame, _ = clear_l4(sess)
        ppu, _ = _plan_to_pickup(frame, bottom_only=True)
        for a in ppu or []:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        frame, _ = goto(frame, sess, (7, 5))
        frame = sess.action(4)["frame"]
        frame, _ = goto(frame, sess, (5, 5))
        frame = sess.action(4)["frame"]
        frame = sess.action(3)["frame"]  # crush cycle once
        frame, _ = goto(frame, sess, (7, 5))
        frame = sess.action(2)["frame"]
        frame, _ = goto(frame, sess, (1, 2))
        frame, _ = goto(frame, sess, (10, 9), max_steps=100)
        print("at109", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        # burn on 108/109 until ui==12
        for _ in range(40):
            ui = ls20.ui_energy(frame)
            cur = ls20.init(frame).cursor
            print(" ", cur, ui)
            if cur == (10, 9) and ui == 12:
                frame = sess.action(2)["frame"]
                break
            if cur == (10, 9) and ui < 12:
                # too low — need refill then retry (hard). break
                print("undershoot")
                break
            if cur == (10, 9):
                frame = sess.action(1)["frame"]
            elif cur == (10, 8):
                frame = sess.action(2)["frame"]
            else:
                frame, _ = goto(frame, sess, (10, 9))
        print("at1010", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        for aid, name in ((1, "U"), (3, "L"), (4, "R"), (2, "D")):
            if ls20.init(frame).cursor != (10, 10):
                print("left", ls20.init(frame).cursor)
                break
            r = sess.action(aid)
            print(name, "->", ls20.init(r["frame"]).cursor, "lv", r.get("levels_completed"),
                  "ui", ls20.ui_energy(r["frame"]))
            if int(r.get("levels_completed") or 0) >= 5:
                print("PASS")
                break
            frame = r["frame"]
            break  # only first dir for exact ui test
    finally:
        sess.close()


if __name__ == "__main__":
    main()
