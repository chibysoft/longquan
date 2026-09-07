"""Reach (10,10) with ui~8 (recording), then UP for L5 stamp."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, _step_cell
from tools.ls20_seated_clear_full import _plan_to_pickup, _plan_to_unlock, _ov
from tools.ls20_l5_unlock_trace import clear_l4
from longquan.interactive.match import mover_bbox_from_cursor


def goto(frame, sess, target, max_steps=60):
    for _ in range(max_steps):
        if ls20.init(frame).cursor == target:
            return frame, True
        offset = ls20.grid_offset(frame)
        walk = ls20.build_walkable(frame, offset, armed=True)
        warps = ls20.detect_warps(frame, offset)
        pickups = ls20.energy_pickups(frame)
        # avoid pickups so fuel drains
        path, _, _, _ = _energy_bfs(
            ls20.init(frame).cursor, MAX_FUEL, 0, walk, [], offset,
            lambda c, _f, _p: c == target, warps,
        )
        if not path:
            return frame, False
        frame = sess.action(DIR_TO_ACTION[path[0]])["frame"]
    return frame, ls20.init(frame).cursor == target


def burn_to(frame, sess, target_ui=10, max_burn=40):
    """Oscillate on safe cells near col10 bottom without triggering eject."""
    for _ in range(max_burn):
        ui = ls20.ui_energy(frame)
        cur = ls20.init(frame).cursor
        if ui <= target_ui and cur == (10, 10):
            return frame
        if cur == (10, 10):
            # step to (10,9) — UP ejects!
            frame = sess.action(1)["frame"]  # may eject — bad
            if ls20.init(frame).cursor != (10, 9):
                # ejected; return via goto avoiding fuel pickup
                frame, _ = goto(frame, sess, (10, 9))
            continue
        if cur == (10, 9):
            # go down to 10,10 only when ui low enough after this step
            ui = ls20.ui_energy(frame)
            if ui <= target_ui + 4:
                frame = sess.action(2)["frame"]  # DOWN to 10,10
            else:
                frame = sess.action(1)["frame"]  # UP to 10,8
            continue
        if cur == (10, 8):
            frame = sess.action(2)["frame"]
            continue
        frame, ok = goto(frame, sess, (10, 9))
        if not ok:
            break
    return frame


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l5_lowui8"])
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
        # follow recording-ish: (7,5) eject UP to (7,2), left pickup (1,2), then bottom
        frame, _ = goto(frame, sess, (7, 5))
        frame = sess.action(1)["frame"]  # UP eject -> (7,1) or (7,2)
        print("after75U", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        frame, _ = goto(frame, sess, (1, 2))
        print("pickup12", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        # long path to (10,10) without other pickups
        frame, ok = goto(frame, sess, (10, 10), max_steps=80)
        print("at1010", ok, ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        if ls20.ui_energy(frame) > 12:
            frame = burn_to(frame, sess, target_ui=8)
            # ensure on (10,10)
            if ls20.init(frame).cursor != (10, 10):
                # only DOWN from (10,9) if ui already low
                frame, _ = goto(frame, sess, (10, 9))
                while ls20.ui_energy(frame) > 8 and ls20.init(frame).cursor == (10, 9):
                    frame = sess.action(1)["frame"]
                    if ls20.init(frame).cursor == (10, 8):
                        frame = sess.action(2)["frame"]
                if ls20.init(frame).cursor == (10, 9):
                    frame = sess.action(2)["frame"]
        print("ready", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        stamp = next(g.shape for g in ls20.init(frame).goals if g.id == "ls20-stamp")
        offset = ls20.grid_offset(frame)
        warps = ls20.detect_warps(frame, offset)
        walk_a = ls20.build_walkable(frame, offset, armed=True)
        cur = ls20.init(frame).cursor
        for name, a in (("U", (0, -1)), ("L", (-1, 0)), ("R", (1, 0)), ("D", (0, 1))):
            if ls20.init(frame).cursor != (10, 10):
                print("not at 1010", ls20.init(frame).cursor)
                break
            pred = _step_cell(cur, a, walk_a, warps)
            r = sess.action(DIR_TO_ACTION[a])
            live = ls20.init(r["frame"]).cursor
            bb = ls20.locate_mover(r["frame"])
            print(
                f"{name} pred={pred} live={live} lv={r.get('levels_completed')} "
                f"ui={ls20.ui_energy(r['frame'])} ov={_ov(bb, stamp) if bb else None}"
            )
            frame = r["frame"]
            if int(r.get("levels_completed") or 0) >= 5:
                print("PASS L5")
                break
            # restore if possible — soft reset may help
            if live != (10, 10):
                break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
