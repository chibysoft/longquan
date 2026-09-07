"""Compare recording L5 clear frames; try low-ui eject from (10,10)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs
from tools.ls20_seated_clear_full import _plan_to_pickup, _plan_to_unlock, _ov
from tools.ls20_l5_unlock_trace import clear_l4
from longquan.interactive.match import mover_bbox_from_cursor

REC = Path(
    r"D:\Projects\ARC-AGI-3-Agents\recordings"
    r"\ls20-9607627b.lingjingsolo.800.5f1bf1fd-a88e-4c5f-8c63-3c85bc6f5f97.recording.jsonl"
)


def rec_tail():
    rows = []
    with open(REC, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i < 180 or i > 184:
                continue
            o = json.loads(line)["data"]
            frame = o["frame"]
            st = ls20.init(frame)
            stamp = next(g.shape for g in st.goals if g.id == "ls20-stamp")
            bb = ls20.locate_mover(frame)
            print(
                f"rec{i} lv={o['levels_completed']} cur={st.cursor} bb={bb} "
                f"ui={ls20.ui_energy(frame)} ov={_ov(bb, stamp) if bb else None} "
                f"stamp={stamp} state={o.get('state')}"
            )
            g = ls20._plane(frame)
            # footprint at (10,1) and (10,2)
            offset = ls20.grid_offset(frame)
            for cell in ((10, 1), (10, 2), (10, 10)):
                px, py = ls20.cursor_to_pixel(cell, offset)
                foot = g[py:py + 2, px:px + 5]
                print(f"  foot{cell}={foot.tolist()}")


def goto(frame, sess, target, max_steps=50):
    for _ in range(max_steps):
        if ls20.init(frame).cursor == target:
            return frame, True
        offset = ls20.grid_offset(frame)
        walk = ls20.build_walkable(frame, offset, armed=True)
        warps = ls20.detect_warps(frame, offset)
        pickups = ls20.energy_pickups(frame)
        path, _, _, _ = _energy_bfs(
            ls20.init(frame).cursor, MAX_FUEL, 0, walk, pickups, offset,
            lambda c, _f, _p: c == target, warps,
        )
        if not path:
            return frame, False
        frame = sess.action(DIR_TO_ACTION[path[0]])["frame"]
    return frame, ls20.init(frame).cursor == target


def live_low_ui():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l5_lowui_eject"])
        frame, _ = clear_l4(sess)
        ppu, _ = _plan_to_pickup(frame, bottom_only=True)
        for a in ppu or []:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        for _ in range(40):
            if ls20.init(frame).cursor == (5, 5):
                break
            p, _, _ = _plan_to_unlock(frame, (5, 5))
            if not p:
                break
            frame = sess.action(DIR_TO_ACTION[p[0]])["frame"]
        frame, _ = goto(frame, sess, (7, 5))
        frame = sess.action(4)["frame"]
        frame, _ = goto(frame, sess, (10, 10))
        # burn ui down toward ~8 without leaving (10,10): oscillate if possible
        # LEFT/RIGHT may eject — use no-op? ACTION5? Or go to (10,9) and back
        while ls20.ui_energy(frame) > 12:
            cur = ls20.init(frame).cursor
            if cur != (10, 10):
                frame, ok = goto(frame, sess, (10, 10), max_steps=15)
                if not ok:
                    print("lost", ls20.init(frame).cursor)
                    break
            # DOWN then UP: DOWN may eject!
            # stay: try ACTION5 to burn? or move to (10,9) if walk
            r = sess.action(5)
            frame = r["frame"]
            print("burn A5", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame),
                  "lv", r.get("levels_completed"))
            if ls20.init(frame).cursor != (10, 10):
                break
            if int(r.get("levels_completed") or 0) >= 5:
                print("PASS via A5")
                return
        print("pre-eject", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        for name, aid in (("U", 1), ("L", 3), ("R", 4), ("D", 2)):
            if ls20.init(frame).cursor != (10, 10):
                frame, _ = goto(frame, sess, (10, 10), max_steps=20)
            r = sess.action(aid)
            print(name, "->", ls20.init(r["frame"]).cursor,
                  "lv", r.get("levels_completed"), "ui", ls20.ui_energy(r["frame"]))
            frame = r["frame"]
            if int(r.get("levels_completed") or 0) >= 5:
                print("PASS")
                break
    finally:
        sess.close()


if __name__ == "__main__":
    print("=== recording ===")
    rec_tail()
    print("=== live ===")
    live_low_ui()
