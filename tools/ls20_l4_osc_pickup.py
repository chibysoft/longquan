"""After unlock, oscillate ring; watch for mid pickup (20,16)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_dd_ritual_probe import boot_l4


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_osc_pickup"])
        frame, meta = boot_l4(sess)
        print("start", ls20.energy_pickups(frame), "c11pf",
              int(np.sum(ls20._plane(frame)[:54] == 11)))
        # oscillate U/D from (6,6)
        # ensure at (6,6)
        for i in range(16):
            cur = ls20.init(frame).cursor
            aid = 1 if cur == (6, 6) else 2  # U from 66, D from 65
            if cur not in ((6, 6), (6, 5)):
                print("left ring", cur)
                break
            resp = sess.action(aid)
            frame, meta = resp["frame"], resp
            pu = ls20.energy_pickups(frame)
            g = ls20._plane(frame)
            mid = g[16:19, 20:23]
            print(f"osc{i} cur={ls20.init(frame).cursor} pu={pu} "
                  f"mid11={int(np.sum(mid==11))} c11pf={int(np.sum(g[:54]==11))}")
            if any(b[1] < 40 for b in pu):
                print("MID PICKUP APPEARED")
                break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
