"""Post-energy soft-reset budget on L2."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools._probe_l2_arm import clear_to_l2, locate_any


def c11(frame):
    return int((ls20._plane(frame) == 11).sum())


def main():
    sess = OnlineSession(_api_key())
    sess.open(tags=["post_energy_budget"])
    try:
        frame, _ = clear_to_l2(sess)
        print("start", locate_any(frame), "c11", c11(frame))
        # Hand path to bottom pickup (40,51): recording-like top corridor then down then left
        # (29,35)->R->(34,35)->U*5->(34,10)->R*3->(49,10)->D*8->(49,50)->L*2->(39,50)
        seq = [4] + [1] * 5 + [4] * 3 + [2] * 8 + [3] * 2
        prev = c11(frame)
        for i, aid in enumerate(seq, 1):
            out = sess.action(aid)
            frame = out["frame"]
            n = c11(frame)
            bb, shape = locate_any(frame)
            print(f"{i:02d} A{aid} mover={bb} c11={n}")
            if n > prev + 30 and shape[0] == 1:
                print("REFILL")
                for j in range(1, 35):
                    out = sess.action(4 if j % 2 == 0 else 3)
                    frame = out["frame"]
                    arr = np.asarray(frame)
                    bb, shape = locate_any(frame)
                    print(f"  burn{j:02d} c11={c11(frame)} layers={shape[0]} mover={bb}")
                    if shape[0] > 1 and np.all(arr[0] == 11):
                        print(f"SOFT-RESET after {j} post-refill moves")
                        return
                print("no soft-reset in 35 post-refill moves")
                return
            prev = n
            if shape[0] > 1 and np.all(np.asarray(frame)[0] == 11):
                print("soft-reset before refill")
                return
        print("never refilled; end", locate_any(frame), c11(frame))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
