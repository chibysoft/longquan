"""Capture the L4 start frame for offline analysis (one-shot, minimal API use).

Reuses the closed-book solver's own clear logic to reach L4 (clear L1-L3),
then saves the L4 start frame to a fixture. Probe-only: no new solving logic.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import plan_two_phase
from tools.ls20_seated_clear_full import (
    _unlock_candidates, _plan_to_pickup, _plan_to_unlock,
)

FIXTURE = ROOT / "tests" / "fixtures" / "ls20_l4_frame_live.json"


def main() -> int:
    key = _api_key()
    if not key:
        raise RuntimeError("ARC_API_KEY not found")
    sess = OnlineSession(key)
    try:
        sess.open(tags=["ls20_l4_frame_capture"])
        reset = sess.reset()
        frame, meta = reset["frame"], reset
        print(f"start lv={meta.get('levels_completed')} mover={ls20.locate_mover(frame)}")

        while int(meta.get("levels_completed") or 0) < 3:
            lv = int(meta.get("levels_completed") or 0)
            # unlock candidates first (refuel + enter)
            for cand in _unlock_candidates(frame):
                p_pu, _ = _plan_to_pickup(frame)
                if p_pu:
                    for a in p_pu:
                        resp = sess.action(DIR_TO_ACTION[a])
                        frame, meta = resp["frame"], resp
                p, _, _ = _plan_to_unlock(frame, cand)
                if p is None:
                    continue
                for a in p:
                    resp = sess.action(DIR_TO_ACTION[a])
                    frame, meta = resp["frame"], resp
            # two-phase flow
            path, _ = plan_two_phase(frame)
            leveled = False
            for a in path:
                resp = sess.action(DIR_TO_ACTION[a])
                frame, meta = resp["frame"], resp
                if int(meta.get("levels_completed") or 0) > lv:
                    leveled = True
                    break
            if not leveled:
                print(f"failed to clear {lv}")
                return 1
            # sync
            resp = sess.action(1)
            frame, meta = resp["frame"], resp
            print(f"cleared {lv} -> sync mover={ls20.locate_mover(frame)}")

        # now at L4 start
        lv = int(meta.get("levels_completed") or 0)
        print(f"at L4 start: lv={lv} mover={ls20.locate_mover(frame)}")
        g = ls20._plane(frame)
        FIXTURE.write_text(json.dumps({"frame": g.tolist(), "levels": lv}),
                           encoding="utf-8")
        print(f"saved -> {FIXTURE}")
        return 0
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
