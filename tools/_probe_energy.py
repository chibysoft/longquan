"""Confirm L2 color-11 pickups refill energy and extend step budget."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import OnlineSession, _api_key
from tools._probe_l2_arm import clear_to_l2, locate_any


def c11(frame):
    g = ls20._plane(frame)
    return int((g == 11).sum())


def main():
    sess = OnlineSession(_api_key())
    sess.open(tags=["ls20_energy"])
    try:
        frame, meta = clear_to_l2(sess)
        print("start", locate_any(frame), "c11", c11(frame))
        # from (29,35) go toward bottom pickup ~(40,51): need down and right
        # path: down to y50, right toward x40
        # cursor (5,7)-> want near (7,10) for pickup (40,51) center ~41,52
        # pixel (40,51) -> cursor ((40-4)/5, 51/5)=(7,10)
        seq = [
            2, 2, 2,  # down to (29,50)? 35+5*3=50 yes if start y35
            4, 4,     # right toward pickup
        ]
        # carefully step
        for i, aid in enumerate(seq, 1):
            out = sess.action(aid)
            frame, meta = out["frame"], out
            bb, shape = locate_any(frame)
            print(f"{i:02d} A{aid} mover={bb} c11={c11(frame)} layers={shape[0]}")
            if shape[0] > 1:
                print("flash early")
                return
        # more rights/downs to hit pickup
        for i in range(len(seq) + 1, 25):
            bb0 = locate_any(frame)[0]
            # move toward (39-42, 50-53)
            px = bb0[0]
            py = bb0[1]
            if px < 38:
                aid = 4
            elif py < 48:
                aid = 2
            else:
                aid = 4 if px < 40 else 3
            out = sess.action(aid)
            frame, meta = out["frame"], out
            bb, shape = locate_any(frame)
            n11 = c11(frame)
            print(f"{i:02d} A{aid} mover={bb} c11={n11} layers={shape[0]}")
            if n11 >= 80:
                print("REFILL detected")
                # burn many more steps to prove extended budget
                for j in range(30):
                    out = sess.action(4 if j % 2 == 0 else 3)
                    frame, meta = out["frame"], out
                    bb, shape = locate_any(frame)
                    print(f"  burn{j:02d} mover={bb} c11={c11(frame)} layers={shape[0]}")
                    if shape[0] > 1:
                        print(f"  flash after {j+1} post-refill burns")
                        return
                print("survived 30 post-refill — energy works")
                return
            if shape[0] > 1:
                print("flash before refill")
                return
    finally:
        sess.close()


if __name__ == "__main__":
    main()
