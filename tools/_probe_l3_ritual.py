"""Try alternate L3 rituals after contact, then approach stamp."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import carrying_bbox_from_cursor
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import _ov, plan_two_phase


def to_l3(sess):
    reset = sess.reset()
    frame, meta = reset["frame"], reset
    while int(meta.get("levels_completed") or 0) < 2:
        lv = int(meta.get("levels_completed") or 0)
        path, _ = plan_two_phase(frame)
        for a in path:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            if int(meta.get("levels_completed") or 0) > lv:
                break
        sync = sess.action(1)
        frame, meta = sync["frame"], sync
    return frame, meta


def run_to_contact(sess, frame):
    path, info = plan_two_phase(frame)
    marker, stamp = info["marker"], info["stamp"]
    for a in path[: info["path1_len"]]:
        resp = sess.action(DIR_TO_ACTION[a])
        frame = resp["frame"]
    return frame, marker, stamp, info


def try_ritual(sess, frame, marker, stamp, ritual, then_stamp_dirs):
    print("ritual", ritual)
    for a in ritual:
        resp = sess.action(a)
        frame = resp["frame"]
        bb = ls20.locate_mover(frame)
        cur = ((bb[0] - 4) // 5, bb[1] // 5)
        cb = carrying_bbox_from_cursor(cur, (4, 0))
        print(f"  A{a} cur={cur} ovM={_ov(cb, marker)}")
    # walk toward stamp with given dirs (coarse)
    for a in then_stamp_dirs:
        prev = ls20.locate_mover(frame)
        resp = sess.action(a)
        frame, meta = resp["frame"], resp
        bb = ls20.locate_mover(frame)
        lv = meta.get("levels_completed")
        layers = np.asarray(frame).shape[0] if np.asarray(frame).ndim == 3 else 1
        print(
            f"  go A{a} {prev}->{bb} ovS={_ov(bb, stamp)} lv={lv} L={layers}"
        )
        if int(lv or 0) >= 3:
            print("PASS")
            return True, frame
        if bb == prev and a == 2:
            print("  stamp blocked")
            return False, frame
    return False, frame


def main() -> int:
    key = _api_key()
    sess = OnlineSession(key)
    try:
        sess.open(tags=["l3_ritual_variants"])
        rituals = [
            [1, 2, 2],
            [1, 2, 2, 1],
            [1, 1, 2, 2],
            [2, 2, 1, 1],
            [1, 2, 2, 2, 1],
        ]
        # stamp approach from (9,3) after typical ritual end: R then many D
        stamp_approach = [4, 2, 2, 2, 2, 2, 2, 2]
        for rit in rituals:
            frame, _ = to_l3(sess)
            frame, marker, stamp, info = run_to_contact(sess, frame)
            bb = ls20.locate_mover(frame)
            print("\n=== contact at", bb, "try", rit)
            ok, frame = try_ritual(sess, frame, marker, stamp, rit, stamp_approach)
            if ok:
                return 0
            # soft reset session by closing? use new game — reopen
            sess.close()
            sess = OnlineSession(key)
            sess.open(tags=["l3_ritual_variants"])
        return 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
