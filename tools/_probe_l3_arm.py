"""Probe L3 arming + stamp entry after seated plan prefix."""
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


def main() -> int:
    key = _api_key()
    sess = OnlineSession(key)
    try:
        sess.open(tags=["l3_arm"])
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

        path, info = plan_two_phase(frame)
        marker, stamp = info["marker"], info["stamp"]
        offset = ls20.grid_offset(frame)
        print("plan", info["path1_len"], info["ritual_len"], info["path2_len"])
        print("actions", [DIR_TO_ACTION[a] for a in path])

        n = info["path1_len"] + info["ritual_len"]
        for i, a in enumerate(path[:n], 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            bb = ls20.locate_mover(frame)
            cur = ((bb[0] - 4) // 5, bb[1] // 5)
            cb = carrying_bbox_from_cursor(cur, offset)
            layers = np.asarray(frame).shape[0] if np.asarray(frame).ndim == 3 else 1
            print(
                f"{i:02d} A{DIR_TO_ACTION[a]} cur={cur} "
                f"ovM={_ov(cb, marker)} layers={layers}"
            )

        print("--- stamp segment ---")
        for i, a in enumerate(path[n:], n + 1):
            prev = ls20.locate_mover(frame)
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            bb = ls20.locate_mover(frame)
            cur = ((bb[0] - 4) // 5, bb[1] // 5)
            layers = np.asarray(frame).shape[0] if np.asarray(frame).ndim == 3 else 1
            print(
                f"{i:02d} A{DIR_TO_ACTION[a]} {prev}->{bb} cur={cur} "
                f"ovS={_ov(bb, stamp)} lv={meta.get('levels_completed')} L={layers}"
            )
            if int(meta.get("levels_completed") or 0) >= 3:
                print("LEVEL UP")
                return 0
            if bb == prev:
                print("blocked at", bb)
                print("try UP D D U then DOWN into stamp")
                for a2 in (1, 2, 2, 1, 2):
                    prev = ls20.locate_mover(frame)
                    resp = sess.action(a2)
                    frame, meta = resp["frame"], resp
                    bb = ls20.locate_mover(frame)
                    print(
                        f"  A{a2} {prev}->{bb} lv={meta.get('levels_completed')} "
                        f"ovS={_ov(bb, stamp)}"
                    )
                    if int(meta.get("levels_completed") or 0) >= 3:
                        print("LEVEL UP after extra ritual")
                        return 0
                break
        return 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
