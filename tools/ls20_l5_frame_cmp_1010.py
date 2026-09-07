"""Byte-level compare recording (10,10) pre-clear vs live (10,10) ui~8."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs
from tools.ls20_seated_clear_full import _plan_to_pickup, _plan_to_unlock
from tools.ls20_l5_unlock_trace import clear_l4

REC = Path(
    r"D:\Projects\ARC-AGI-3-Agents\recordings"
    r"\ls20-9607627b.lingjingsolo.800.5f1bf1fd-a88e-4c5f-8c63-3c85bc6f5f97.recording.jsonl"
)


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
    with open(REC, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i == 182:
                rec = json.loads(line)["data"]
                break
    rg = ls20._plane(rec["frame"])

    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l5_frame_cmp"])
        frame, _ = clear_l4(sess)
        ppu, _ = _plan_to_pickup(frame, bottom_only=True)
        for a in ppu or []:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        for _ in range(40):
            if ls20.init(frame).cursor == (5, 5):
                break
            p, _, _ = _plan_to_unlock(frame, (5, 5))
            if not p:
                break
            frame = sess.action(DIR_TO_ACTION[p[0]])["frame"]
        frame, _ = goto(frame, sess, (7, 5))
        frame = sess.action(2)["frame"]
        frame, _ = goto(frame, sess, (1, 2))
        frame, _ = goto(frame, sess, (10, 10))
        # burn to ~8 via (10,8)/(10,9) if needed
        while ls20.ui_energy(frame) > 10:
            cur = ls20.init(frame).cursor
            if cur == (10, 10):
                frame = sess.action(1)["frame"]
                if ls20.init(frame).cursor != (10, 9):
                    frame, _ = goto(frame, sess, (10, 9))
            elif cur == (10, 9):
                if ls20.ui_energy(frame) <= 12:
                    frame = sess.action(2)["frame"]
                else:
                    frame = sess.action(1)["frame"]
            elif cur == (10, 8):
                frame = sess.action(2)["frame"]
            else:
                frame, _ = goto(frame, sess, (10, 9))
                break
        if ls20.init(frame).cursor != (10, 10):
            frame, _ = goto(frame, sess, (10, 9))
            frame = sess.action(2)["frame"]
        lg = ls20._plane(frame)
        print("live", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        print("rec ", ls20.init(rec["frame"]).cursor, "ui", ls20.ui_energy(rec["frame"]))
        diff = rg != lg
        print("diff pixels", int(diff.sum()))
        # ignore mover 12 and ui 11
        mask = diff & (rg != 12) & (lg != 12) & (rg != 11) & (lg != 11)
        ys, xs = np.where(mask)
        print("struct diff", len(xs))
        for y, x in list(zip(ys, xs))[:60]:
            print(f"  ({x},{y}) rec={int(rg[y,x])} live={int(lg[y,x])}")
        # color hist
        for c in range(16):
            a, b = int((rg == c).sum()), int((lg == c).sum())
            if a != b:
                print(f"hist c{c}: rec={a} live={b}")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
