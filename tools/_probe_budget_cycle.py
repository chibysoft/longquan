"""How many steps between soft-resets on L2? Does budget change?"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import OnlineSession, _api_key
from tools._probe_l2_arm import clear_to_l2, locate_any


def main():
    sess = OnlineSession(_api_key())
    sess.open(tags=["ls20_budget_cycle"])
    try:
        frame, meta = clear_to_l2(sess)
        total = 0
        life = 1
        life_steps = 0
        while life <= 3 and total < 80:
            out = sess.action(4 if life_steps % 2 == 0 else 3)
            total += 1
            life_steps += 1
            frame, meta = out["frame"], out
            bb, shape = locate_any(frame)
            if shape[0] > 1:
                print(f"life{life} flash after {life_steps} steps (total={total}) mover={bb}")
                life += 1
                life_steps = 0
        print("done")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
