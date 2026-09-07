"""UDD+fuel+to (2,1), save frame, diff vs recording i138 gate region."""
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
from tools.ls20_seated_clear import RITUAL, MAX_FUEL, _energy_bfs
from tools.ls20_seated_clear_full import _plan_to_pickup, _plan_armed_stamp_only
from tools.ls20_l4_dd_ritual_probe import boot_l4


def plan_to(frame, goal):
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk_u)
    pickups = ls20.energy_pickups(frame)
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))
    return _energy_bfs(state.cursor, fuel0, 0, walk_u, pickups, offset,
                       lambda c, _f, _p: c == goal, warps)


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_frame_diff"])
        frame, meta = boot_l4(sess)
        for _ in range(30):
            p, _, _, _ = plan_to(frame, (4, 7))
            if not p or len(p) == 0:
                break
            resp = sess.action(DIR_TO_ACTION[p[0]])
            frame, meta = resp["frame"], resp
            if ls20.init(frame).cursor == (4, 7):
                break
        for a in RITUAL:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
        for _ in range(15):
            p_pu, _ = _plan_to_pickup(frame)
            if not p_pu:
                break
            resp = sess.action(DIR_TO_ACTION[p_pu[0]])
            frame, meta = resp["frame"], resp
            if ls20.ui_energy(frame) >= 70:
                break
        for _ in range(25):
            path, _, _, _ = _plan_armed_stamp_only(frame)
            if not path:
                break
            resp = sess.action(DIR_TO_ACTION[path[0]])
            frame, meta = resp["frame"], resp
            if ls20.init(frame).cursor == (2, 1):
                break
        out = ROOT / "tests" / "fixtures" / "ls20_l4_stuck_21.json"
        out.write_text(json.dumps({"frame": frame, "meta": {
            "cursor": ls20.init(frame).cursor,
            "carry": ls20.init(frame).carrying,
            "ui": ls20.ui_energy(frame),
        }}), encoding="utf-8")
        print("saved", out, ls20.init(frame).cursor, ls20.init(frame).carrying,
              ls20.ui_energy(frame))

        # diff vs recording
        rp = Path(r"D:\Projects\ARC-AGI-3-Agents\recordings\ls20-9607627b.lingjingsolo.800.5f1bf1fd-a88e-4c5f-8c63-3c85bc6f5f97.recording.jsonl")
        with rp.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i == 138:
                    rec = json.loads(line)["data"]["frame"]
                    break
        a = ls20._plane(frame)
        b = ls20._plane(rec)
        # gate window
        win = a[0:20, 0:30]
        winb = b[0:20, 0:30]
        diff = win != winb
        print("gate window diffs", int(diff.sum()), "of", diff.size)
        ys, xs = np.where(diff)
        for y, x in list(zip(ys.tolist(), xs.tolist()))[:40]:
            print(f"  ({x},{y}) live={int(win[y,x])} rec={int(winb[y,x])}")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
