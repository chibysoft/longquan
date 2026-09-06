"""Is L2 soft-reset a raw step-count limit?"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import OnlineSession, _api_key
from tools._probe_l2_arm import clear_to_l2, locate_any


def main():
    sess = OnlineSession(_api_key())
    sess.open(tags=["ls20_step_limit"])
    try:
        frame, meta = clear_to_l2(sess)
        print("start", locate_any(frame))
        # oscillate LEFT/RIGHT near spawn (safe corridor)
        # spawn (29,35); right to (34,35) and back
        seq = [4, 3] * 15  # 30 moves
        for i, aid in enumerate(seq, 1):
            out = sess.action(aid)
            frame, meta = out["frame"], out
            bb, shape = locate_any(frame)
            print(f"{i:02d} A{aid} mover={bb} layers={shape[0]}")
            if shape[0] > 1:
                print(f"SOFT RESET at step {i}")
                break
        else:
            print("no soft-reset in", len(seq), "moves")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
