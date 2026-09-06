"""Probe: after arming on L2, which next moves soft-reset?"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import plan_two_phase


def locate_any(frame):
    arr = np.asarray(frame)
    if arr.ndim == 2:
        return ls20.locate_mover(frame), arr.shape
    for i in range(arr.shape[0]):
        bb = ls20._bbox(arr[i], (12,))
        if bb is not None:
            return bb, arr.shape
    return None, arr.shape


def clear_to_l2(sess):
    r = sess.reset()
    frame, meta = r["frame"], r
    path, _ = plan_two_phase(frame)
    for d in path:
        out = sess.action(DIR_TO_ACTION[d])
        frame, meta = out["frame"], out
        if int(meta.get("levels_completed") or 0) >= 1:
            break
    # sync with A1 to match recording spawn approach -> (29,35)
    out = sess.action(1)
    return out["frame"], out


def go_to_marker(sess, frame):
    path, info = plan_two_phase(frame)
    p1 = path[: info["path1_len"]]
    for i, d in enumerate(p1, 1):
        out = sess.action(DIR_TO_ACTION[d])
        frame, meta = out["frame"], out
        bb, shape = locate_any(frame)
        print(f"p1 {i:02d} A{DIR_TO_ACTION[d]} mover={bb} layers={shape} "
              f"reset={meta.get('full_reset')} lv={meta.get('levels_completed')}")
    return frame, meta, info


def main():
    sess = OnlineSession(_api_key())
    sess.open(tags=["ls20_arm_probe"])
    try:
        frame, meta = clear_to_l2(sess)
        print("L2", locate_any(frame), "marker", ls20._bbox(ls20._plane(frame), (0, 1)))
        frame, meta, info = go_to_marker(sess, frame)
        print("armed at", locate_any(frame), "info", info)
        # try sequence of next moves
        for aid in [1, 1, 1, 1, 1, 1]:  # ups like our failing path2
            out = sess.action(aid)
            frame, meta = out["frame"], out
            bb, shape = locate_any(frame)
            print(
                f"post A{aid} mover={bb} layers={shape} "
                f"reset={meta.get('full_reset')} state={meta.get('state')} "
                f"avail={meta.get('available_actions')}"
            )
            if shape[0] > 1 or bb == (29, 40, 33, 41) or bb == (29, 35, 33, 36):
                print("  -> soft-reset or multi-layer detected")
                break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
