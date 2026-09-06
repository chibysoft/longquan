"""After L2 step-21 multilayer flash, does the next action continue or respawn?"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import OnlineSession, _api_key
from tools._probe_l2_arm import clear_to_l2, locate_any


def main():
    sess = OnlineSession(_api_key())
    sess.open(tags=["ls20_after_flash"])
    try:
        frame, meta = clear_to_l2(sess)
        # burn 20 steps oscillating
        for i, aid in enumerate([4, 3] * 10, 1):
            out = sess.action(aid)
            frame, meta = out["frame"], out
            bb, shape = locate_any(frame)
            print(f"{i:02d} A{aid} mover={bb} layers={shape[0]}")
        # 21st should flash
        out = sess.action(4)
        frame, meta = out["frame"], out
        bb, shape = locate_any(frame)
        print(f"21 FLASH mover={bb} layers={shape} reset={meta.get('full_reset')}")
        # continue several actions
        for i, aid in enumerate([4, 3, 4, 1, 2, 4], 22):
            out = sess.action(aid)
            frame, meta = out["frame"], out
            bb, shape = locate_any(frame)
            print(f"{i:02d} A{aid} mover={bb} layers={shape[0]} lv={meta.get('levels_completed')}")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
