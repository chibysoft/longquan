"""Unlock → contact (4,6) → DOWN DOWN → approach (2,1) → LEFT."""
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
    _plan_to_pickup, _plan_to_unlock, _sync_after_levelup,
    _plan_to_contact, _plan_armed_stamp_only,
)
from tools.ls20_l4_stamp9_probe import stamp9


def boot_l4(sess):
    resp = sess.reset()
    frame, meta = resp["frame"], resp
    while int(meta.get("levels_completed") or 0) < 3:
        lv = int(meta.get("levels_completed") or 0)
        from tools.ls20_seated_clear_full import _unlock_candidates
        for cand in _unlock_candidates(frame):
            p_pu, _ = _plan_to_pickup(frame)
            if p_pu:
                for a in p_pu:
                    resp = sess.action(DIR_TO_ACTION[a])
                    frame, meta = resp["frame"], resp
            p, _, _ = _plan_to_unlock(frame, cand)
            if p:
                for a in p:
                    resp = sess.action(DIR_TO_ACTION[a])
                    frame, meta = resp["frame"], resp
        path, _ = plan_two_phase(frame)
        for a in path:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            if int(meta.get("levels_completed") or 0) > lv:
                break
        frame, meta = _sync_after_levelup(sess, frame)
    p_pu, _ = _plan_to_pickup(frame)
    if p_pu:
        for a in p_pu:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
    p, _, _ = _plan_to_unlock(frame, (6, 6))
    for a in p:
        resp = sess.action(DIR_TO_ACTION[a])
        frame, meta = resp["frame"], resp
    return frame, meta


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_dd_ritual"])
        frame, meta = boot_l4(sess)
        for _ in range(20):
            pc, cc, _, ic = _plan_to_contact(frame)
            if not pc:
                # require real overlap, not no_marker
                if ic.get("already") and not ic.get("no_marker"):
                    print("contacted", cc)
                    break
                if ic.get("no_marker"):
                    # still try to step if cursor is (4,6)
                    if ls20.init(frame).cursor == (4, 6):
                        print("at (4,6) with no_marker — treat as contact")
                        break
                    print("no_marker elsewhere", ls20.init(frame).cursor)
                    break
                print("fail", ic)
                break
            resp = sess.action(DIR_TO_ACTION[pc[0]])
            frame, meta = resp["frame"], resp
        print("pre-ritual", ls20.init(frame).cursor)
        for aid, name in [(2, "D"), (2, "D")]:
            before = ls20.init(frame).cursor
            resp = sess.action(aid)
            frame, meta = resp["frame"], resp
            print(name, before, "->", ls20.init(frame).cursor)
        for i in range(40):
            path, dest, _, info = _plan_armed_stamp_only(frame)
            if not path:
                print("no stamp", info)
                break
            before = ls20.init(frame).cursor
            resp = sess.action(DIR_TO_ACTION[path[0]])
            frame, meta = resp["frame"], resp
            after = ls20.init(frame).cursor
            print(f"{i+1:02d} A{DIR_TO_ACTION[path[0]]} {before}->{after} "
                  f"s9={stamp9(frame)[0]} lv={meta.get('levels_completed')} "
                  f"ui={ls20.ui_energy(frame)}")
            if int(meta.get("levels_completed") or 0) >= 4:
                print("CLEARED")
                return
            if after == before and after == (2, 1):
                print("stuck (2,1)")
                break
        print("DONE", ls20.init(frame).cursor, stamp9(frame)[0])
    finally:
        sess.close()


if __name__ == "__main__":
    main()
