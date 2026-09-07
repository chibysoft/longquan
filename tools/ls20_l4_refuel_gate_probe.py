"""At (2,1) with stamp9=9, refill then retry gate LEFT."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import plan_two_phase
from tools.ls20_seated_clear_full import (
    _plan_to_pickup, _plan_to_unlock, _unlock_candidates, _sync_after_levelup,
    _plan_armed_stamp_only, _plan_to_pickup as plan_pu,
)
from tools.ls20_l4_stamp9_probe import to_l4_unlock, stamp9


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_refuel_gate"])
        frame, meta = to_l4_unlock(sess)
        # go to (2,1) via armed stamp plan steps
        for _ in range(20):
            path, dest, fuel, info = _plan_armed_stamp_only(frame)
            if not path:
                break
            resp = sess.action(DIR_TO_ACTION[path[0]])
            frame, meta = resp["frame"], resp
            if ls20.init(frame).cursor == (2, 1):
                break
        print("at", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame),
              "stamp9", stamp9(frame)[0])
        # refuel
        p_pu, _ = _plan_to_pickup(frame)
        print("pickup plan", None if p_pu is None else len(p_pu))
        if p_pu:
            for a in p_pu:
                resp = sess.action(DIR_TO_ACTION[a])
                frame, meta = resp["frame"], resp
            print("after fuel", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame),
                  "stamp9", stamp9(frame)[0])
        # replan to stamp
        for i in range(25):
            path, dest, fuel, info = _plan_armed_stamp_only(frame)
            if not path:
                print("no path", info)
                break
            before = ls20.init(frame).cursor
            resp = sess.action(DIR_TO_ACTION[path[0]])
            frame, meta = resp["frame"], resp
            after = ls20.init(frame).cursor
            print(f"{i+1:02d} A{DIR_TO_ACTION[path[0]]} {before}->{after} "
                  f"ui={ls20.ui_energy(frame)} s9={stamp9(frame)[0]} "
                  f"lv={meta.get('levels_completed')}")
            if int(meta.get("levels_completed") or 0) >= 4:
                print("CLEARED")
                return
        print("FAIL", ls20.init(frame).cursor, stamp9(frame)[0])
    finally:
        sess.close()


if __name__ == "__main__":
    main()
