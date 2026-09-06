"""Find minimal post-marker wiggle that arms L2."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import plan_two_phase
from tools._probe_l2_arm import clear_to_l2, locate_any


def go_marker(sess):
    frame, _ = clear_to_l2(sess)
    path, info = plan_two_phase(frame)
    for d in path[: info["path1_len"]]:
        out = sess.action(DIR_TO_ACTION[d])
        frame = out["frame"]
    rest = path[info["path1_len"]:]
    return frame, rest


def try_stamp(sess, frame, rest, label):
    # ensure back at marker cell (49,45) before open-loop rest
    target = (49, 45, 53, 46)
    for _ in range(6):
        bb = locate_any(frame)[0]
        if bb == target:
            break
        if bb is None:
            break
        if bb[1] > target[1]:
            aid = 1
        elif bb[1] < target[1]:
            aid = 2
        elif bb[0] < target[0]:
            aid = 4
        else:
            aid = 3
        out = sess.action(aid)
        frame = out["frame"]
    print("  aligned", locate_any(frame))
    for i, d in enumerate(rest, 1):
        out = sess.action(DIR_TO_ACTION[d])
        frame, meta = out["frame"], out
        bb, shape = locate_any(frame)
        lv = int(meta.get("levels_completed") or 0)
        if lv >= 2:
            print(f"SUCCESS {label} at step {i} mover={bb}")
            return True
        if shape[0] > 1 and i >= len(rest) - 1:
            print(f"FAIL {label} flash near end mover={bb}")
            return False
    print(f"FAIL {label} final={locate_any(frame)}")
    return False


def main():
    candidates = {
        "up_back": [1, 2],
        "down_back": [2, 1],
        "up_back_down": [1, 2, 2],
        "up_back_down_back": [1, 2, 2, 1],  # known success
        "down_up": [2, 1],
        "double_up_back": [1, 1, 2, 2],
    }
    for name, wig in candidates.items():
        sess = OnlineSession(_api_key())
        sess.open(tags=[f"wig_{name}"])
        try:
            frame, rest = go_marker(sess)
            print(f"\n=== {name} wig={wig} start={locate_any(frame)}")
            for aid in wig:
                out = sess.action(aid)
                frame = out["frame"]
                print(f"  A{aid} {locate_any(frame)}")
            try_stamp(sess, frame, rest, name)
        finally:
            sess.close()


if __name__ == "__main__":
    main()
