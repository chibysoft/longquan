"""L5: follow recording unlock crush + route; check c9 and final UP."""
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


def c9(frame):
    g = ls20._plane(frame)
    return int((g == 9).sum()), int((g[:54] == 9).sum())


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
        sess.open(tags=["ls20_l5_rec_route"])
        frame, _ = clear_l4(sess)
        # recording: bottom fuel, (10,7)/(10,6) hop, (7,5)R fuel, approach (5,5)
        ppu, _ = _plan_to_pickup(frame, bottom_only=True)
        for a in ppu or []:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        print("spawnish", ls20.init(frame).cursor, "c9", c9(frame))
        # go (7,5) R like rec after hop path
        frame, _ = goto(frame, sess, (7, 5))
        frame = sess.action(4)["frame"]
        print("after75R", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame), "c9", c9(frame))
        # enter (5,5)
        frame, _ = goto(frame, sess, (5, 5))
        print("enter55", ls20.init(frame).cursor, "c9", c9(frame), "ui", ls20.ui_energy(frame))
        # oscillate R/L like rec until c9 drops after spike
        for i in range(6):
            frame = sess.action(4)["frame"]
            print(f"  R {ls20.init(frame).cursor} c9={c9(frame)}")
            frame = sess.action(3)["frame"]
            print(f"  L {ls20.init(frame).cursor} c9={c9(frame)}")
            if c9(frame)[0] <= 20 and i >= 1:
                break
        # (7,5) D eject, (1,2), long to (10,10) ui~8
        frame, _ = goto(frame, sess, (7, 5))
        frame = sess.action(2)["frame"]
        print("75D", ls20.init(frame).cursor, c9(frame))
        frame, _ = goto(frame, sess, (1, 2))
        print("12", ls20.ui_energy(frame), c9(frame))
        # path via (3,5)(1,6)(1,7)... like rec — just goto 10,10
        frame, _ = goto(frame, sess, (10, 10), max_steps=100)
        print("1010", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame), c9(frame))
        # if ui high, burn on 10,8/9
        while ls20.ui_energy(frame) > 10:
            cur = ls20.init(frame).cursor
            if cur == (10, 10):
                frame = sess.action(1)["frame"]
                if ls20.init(frame).cursor != (10, 9):
                    frame, _ = goto(frame, sess, (10, 9))
            elif cur == (10, 9):
                frame = sess.action(1 if ls20.ui_energy(frame) > 12 else 2)["frame"]
            elif cur == (10, 8):
                frame = sess.action(2)["frame"]
            else:
                frame, _ = goto(frame, sess, (10, 9))
        if ls20.init(frame).cursor != (10, 10):
            if ls20.init(frame).cursor == (10, 9):
                frame = sess.action(2)["frame"]
            else:
                frame, _ = goto(frame, sess, (10, 10))
        print("ready", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame), c9(frame))
        r = sess.action(1)
        print("U", ls20.init(r["frame"]).cursor, "lv", r.get("levels_completed"),
              "ui", ls20.ui_energy(r["frame"]), "c9", c9(r["frame"]))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
