"""Does touching the L2 marker refill the step budget?"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import plan_two_phase
from tools._probe_l2_arm import clear_to_l2, locate_any


def main():
    sess = OnlineSession(_api_key())
    sess.open(tags=["ls20_refill"])
    try:
        frame, meta = clear_to_l2(sess)  # uses 1 sync step
        path, info = plan_two_phase(frame)
        p1 = path[: info["path1_len"]]  # 16 more -> total 17
        for d in p1:
            out = sess.action(DIR_TO_ACTION[d])
            frame, meta = out["frame"], out
        print("at marker after", 1 + len(p1), "L2 steps", locate_any(frame))
        # now burn steps — if refill, should get ~20 more before flash
        for i in range(1, 30):
            # oscillate up/down near marker: A1/A2
            aid = 1 if i % 2 else 2
            out = sess.action(aid)
            frame, meta = out["frame"], out
            bb, shape = locate_any(frame)
            print(f"post-arm {i:02d} A{aid} mover={bb} layers={shape[0]}")
            if shape[0] > 1:
                print(f"FLASH after {i} post-arm steps (total L2~{1+len(p1)+i})")
                break
        else:
            print("no flash in 30 post-arm steps — strong refill signal")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
