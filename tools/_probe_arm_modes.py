"""Try ACTION5 / alternate overlaps to arm on L2."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import plan_two_phase
from tools._probe_l2_arm import clear_to_l2, locate_any


def try_enter_stamp(sess, frame, label):
    """From current pose, walk to (2,7) then A2 into (2,8); report if entered."""
    # Use a few manual moves if already near stamp corridor — else skip
    # After marker we're at (49,45). Too far — just try ACTION5 variants here first.
    print(label, "at", locate_any(frame), "c01", ls20._bbox(ls20._plane(frame), (0, 1)))


def main():
    for mode in ["a5", "linger", "down50", "left_overlap"]:
        sess = OnlineSession(_api_key())
        sess.open(tags=[f"arm_{mode}"])
        try:
            frame, meta = clear_to_l2(sess)
            path, info = plan_two_phase(frame)
            for d in path[: info["path1_len"]]:
                out = sess.action(DIR_TO_ACTION[d])
                frame, meta = out["frame"], out
            print(f"\n=== mode {mode} at marker", locate_any(frame))
            if mode == "a5":
                out = sess.action(5)
                frame, meta = out["frame"], out
                print(" after A5", locate_any(frame), "c01", ls20._bbox(ls20._plane(frame), (0, 1)))
            elif mode == "linger":
                for aid in (1, 2, 2, 1):  # wiggle on marker
                    out = sess.action(aid)
                    frame, meta = out["frame"], out
                    print("  wig", aid, locate_any(frame))
            elif mode == "down50":
                out = sess.action(2)
                frame, meta = out["frame"], out
                print(" after down", locate_any(frame))
            elif mode == "left_overlap":
                out = sess.action(4)  # right first maybe blocked
                frame = out["frame"]
                out = sess.action(3)
                frame, meta = out["frame"], out
                print(" after L", locate_any(frame))

            # Now burn path to stamp (reuse plan from current — quick greedy)
            # Go up corridor and left — same as path2 from seated plan
            path2 = path[info["path1_len"]:]
            # If we inserted extra moves, path2 may desync — replan from frame
            from tools.ls20_seated_clear import plan_two_phase as p2
            # force: only stamp half by temporarily... just execute remaining original path2
            # For modes with extra moves, replan full from here with fuel
            try:
                path_r, info_r = plan_two_phase(frame)
                # If already armed in our model, path may be shorter; take full path
                seq = path_r
            except Exception as e:
                print("replan fail", e)
                seq = path2
            for i, d in enumerate(seq, 1):
                out = sess.action(DIR_TO_ACTION[d])
                frame, meta = out["frame"], out
                bb, shape = locate_any(frame)
                lv = meta.get("levels_completed")
                if i % 5 == 0 or int(lv or 0) >= 2 or shape[0] > 1:
                    print(f"  {i:02d} A{DIR_TO_ACTION[d]} {bb} lv={lv} layers={shape[0]}")
                if int(lv or 0) >= 2:
                    print(f"SUCCESS mode={mode}")
                    break
                if shape[0] > 1 and bb and bb[1] >= 40 and bb[0] <= 33:
                    # possible soft-reset at spawn
                    if bb[0] <= 33:
                        print(f"flash/reset mode={mode} at {i}")
                        break
            else:
                print(f"FAIL mode={mode} final", locate_any(frame))
        finally:
            sess.close()


if __name__ == "__main__":
    main()
