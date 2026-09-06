"""Reproduce linger success with full c11 logging."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import plan_two_phase
from tools._probe_l2_arm import clear_to_l2, locate_any


def c11(frame):
    return int((ls20._plane(frame) == 11).sum())


def main():
    sess = OnlineSession(_api_key())
    sess.open(tags=["reproduce_linger"])
    try:
        frame, _ = clear_to_l2(sess)
        # Build path to contact via energy using a working offline method:
        # use previous combined plan without ritual — take until first contact
        # Fallback: use recording-like seq to energy+contact
        seq_to_contact = [4] + [1]*5 + [4]*3 + [2]*8 + [3]*2 + [4]*2 + [1]
        # ends: energy at 19, then R R U to (49,45) contact
        for i, aid in enumerate(seq_to_contact, 1):
            out = sess.action(aid)
            frame = out["frame"]
            print(f"pre {i:02d} A{aid} {locate_any(frame)[0]} c11={c11(frame)}")
        print("RITUAL 1,2,2")
        for aid in (1, 2, 2):
            out = sess.action(aid)
            frame = out["frame"]
            print(f"rit A{aid} {locate_any(frame)[0]} c11={c11(frame)}")
        # align back to contact
        out = sess.action(1)
        frame = out["frame"]
        print(f"align A1 {locate_any(frame)[0]} c11={c11(frame)}")
        # path to stamp: up corridor left down — from known plan
        stamp_path = [1,1,1,1,1,1,1,3,1,3,3,3,3,3,3,2,2,2,2,2,2]
        for i, aid in enumerate(stamp_path, 1):
            out = sess.action(aid)
            frame, meta = out["frame"], out
            bb = locate_any(frame)[0]
            print(f"st {i:02d} A{aid} {bb} c11={c11(frame)} lv={meta.get('levels_completed')}")
            if int(meta.get("levels_completed") or 0) >= 2:
                print("CLEARED")
                return
        print("failed")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
