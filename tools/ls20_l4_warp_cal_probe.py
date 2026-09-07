"""L4 one-cell warp calibration at the ring approach corridor.

Climb to L4, refuel, walk to (7,4) via a path that avoids known (6,4) portal,
step DOWN to (7,5), then fire U/D/L/R and log landings (no crush attempt).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import _energy_bfs, _step_cell, plan_two_phase
from tools.ls20_seated_clear_full import (
    _plan_to_pickup,
    _unlock_candidates,
    _plan_to_unlock,
)
from tools.ls20_l4_arming_probe import _climb_to_l4, _fuel0, _gate_walk

REPORT = ROOT / "docs" / "ls20_l4_warp_cal_probe.md"


def main() -> int:
    key = _api_key()
    if not key:
        raise RuntimeError("no key")
    sess = OnlineSession(key)
    log = []
    try:
        sess.open(tags=["ls20_l4_warp_cal"])
        frame, meta = _climb_to_l4(sess)
        log.append({"tag": "l4", "snap": _gate_walk(frame),
                    "cursor": ls20.init(frame).cursor})

        p_pu, _ = _plan_to_pickup(frame)
        for a in p_pu or []:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
        cur0 = ls20.init(frame).cursor
        log.append({"tag": "post_fuel", "cursor": cur0})

        off = ls20.grid_offset(frame)
        wu = ls20.build_walkable(frame, off, armed=False)
        warps = ls20.detect_warps(frame, off, wu)
        pickups = ls20.energy_pickups(frame)
        p, c, f, pm = _energy_bfs(
            cur0, _fuel0(frame), 0, wu, pickups, off,
            lambda cell, _f, _p: cell == (7, 4), warps,
        )
        log.append({"tag": "to_74_plan", "len": None if p is None else len(p),
                    "actions": None if p is None else [DIR_TO_ACTION[a] for a in p],
                    "model_warps_74": {str(k): v for k, v in warps.items()
                                       if k[0] == (7, 4)}})
        if p is None:
            log.append({"tag": "RESULT", "verdict": "UNREACHABLE_74"})
            REPORT.write_text(json.dumps(log, indent=2), encoding="utf-8")
            return 1
        for a in p:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
        cur = ls20.init(frame).cursor
        log.append({"tag": "at", "want": (7, 4), "cursor": cur,
                    "mover": ls20.locate_mover(frame)})

        # DOWN into (7,5)
        resp = sess.action(DIR_TO_ACTION[(0, 1)])
        frame, meta = resp["frame"], resp
        cur = ls20.init(frame).cursor
        log.append({"tag": "down_to_75", "cursor": cur,
                    "mover": ls20.locate_mover(frame)})

        # From current cell, try each dir once (stateful — order U,R,D,L)
        # Re-acquire (7,5) if we drift: best-effort.
        for d in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            before = ls20.init(frame).cursor
            model = _step_cell(
                before, d,
                ls20.build_walkable(frame, off, armed=False),
                ls20.detect_warps(frame, off,
                                  ls20.build_walkable(frame, off, armed=False)),
            )
            resp = sess.action(DIR_TO_ACTION[d])
            frame, meta = resp["frame"], resp
            after = ls20.init(frame).cursor
            log.append({
                "tag": "pulse", "dir": d, "action": DIR_TO_ACTION[d],
                "before": before, "model": model, "after": after,
                "match": model == after,
                "mover": ls20.locate_mover(frame),
                "ui": ls20.ui_energy(frame),
            })
            print(f"pulse {d}: {before} model={model} after={after} match={model==after}")

        REPORT.write_text(
            "# ls20 L4 warp calibration\n\n"
            + "\n".join(f"- `{row}`" for row in log) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {REPORT}")
        return 0
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
