"""Ring osc; on each c9 flip snapshot; try gate after leaving in each phase."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import mover_bbox_from_cursor
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs, _ov
from tools.ls20_seated_clear_full import _plan_to_unlock, _unlock_candidates
from tools.ls20_l4_unlock_trace import advance_to_l4_pre_unlock
from tools.ls20_l4_stamp9_probe import stamp9


def c9(frame):
    return int((ls20._plane(frame) == 9).sum())


def bfs_to(frame, goal, armed=True):
    offset = ls20.grid_offset(frame)
    walk = ls20.build_walkable(frame, offset, armed=armed)
    warps = ls20.detect_warps(frame, offset, ls20.build_walkable(frame, offset, armed=False))
    p, _, _, _ = _energy_bfs(
        ls20.init(frame).cursor, MAX_FUEL, 0, walk, [], offset,
        lambda c, _f, _p: c == goal, warps,
    )
    return p


def bfs_mid(frame):
    offset = ls20.grid_offset(frame)
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    warps = ls20.detect_warps(frame, offset, ls20.build_walkable(frame, offset, armed=False))
    mid = [p for p in ls20.energy_pickups(frame) if p[1] < 40]
    if not mid:
        return None

    def at_mid(cell, _f, _p):
        return any(_ov(mover_bbox_from_cursor(cell, offset), pb) > 0 for pb in mid)

    p, _, _, _ = _energy_bfs(
        ls20.init(frame).cursor, MAX_FUEL, 0, walk_a, mid, offset, at_mid, warps,
    )
    return p


def run_to_gate(sess, frame, label):
    """From current (expect near ring): mid if needed, UD47, to (2,1), LEFT once."""
    print(f"=== try {label} cur={ls20.init(frame).cursor} c9={c9(frame)} "
          f"ui={ls20.ui_energy(frame)} cands={_unlock_candidates(frame)} ===")
    # ensure fuel via mid or accept soft-reset
    if any(p[1] < 40 for p in ls20.energy_pickups(frame)):
        pm = bfs_mid(frame)
        if pm:
            for a in pm:
                frame = sess.action(DIR_TO_ACTION[a])["frame"]
            print(" mid", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
    p47 = bfs_to(frame, (4, 7), armed=False)
    if not p47:
        print(" no 47")
        return frame, False
    for a in p47:
        frame = sess.action(DIR_TO_ACTION[a])["frame"]
    for a in ((0, -1), (0, 1)):
        frame = sess.action(DIR_TO_ACTION[a])["frame"]
    print(" after UD", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame), "c9", c9(frame))
    if any(p[1] < 40 for p in ls20.energy_pickups(frame)):
        pm = bfs_mid(frame)
        if pm:
            for a in pm:
                frame = sess.action(DIR_TO_ACTION[a])["frame"]
            print(" mid2", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
    for _ in range(30):
        cur = ls20.init(frame).cursor
        if cur == (2, 1):
            break
        # avoid soft-reset death spiral: if ui==0 and not on path end, still try
        p = bfs_to(frame, (2, 1), armed=True)
        if not p:
            print(" stuck", cur, "ui", ls20.ui_energy(frame))
            break
        frame = sess.action(DIR_TO_ACTION[p[0]])["frame"]
        # if soft-reset teleported far, continue
    cur = ls20.init(frame).cursor
    print(" at", cur, "ui", ls20.ui_energy(frame), "s9", stamp9(frame)[0],
          "c9", c9(frame), "cands", _unlock_candidates(frame))
    if cur != (2, 1):
        # one more push from nearby
        p = bfs_to(frame, (2, 1), armed=True)
        for a in (p or [])[:10]:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        cur = ls20.init(frame).cursor
        print(" push", cur, "ui", ls20.ui_energy(frame))
    if cur != (2, 1):
        return frame, False
    before = cur
    resp = sess.action(3)
    frame = resp["frame"]
    after = ls20.init(frame).cursor
    lv = int(resp.get("levels_completed") or 0)
    arr = np.asarray(frame)
    print(" LEFT", before, "->", after, "lv", lv,
          "layers", arr.shape[0] if arr.ndim == 3 else 1)
    return frame, lv >= 4 or after == (1, 1)


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_c9_phases"])
        frame, _ = advance_to_l4_pre_unlock(sess)
        p, _, _ = _plan_to_unlock(frame, (6, 6))
        for a in p:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        print("UNLOCK", ls20.init(frame).cursor, "c9", c9(frame))

        # mid first for fuel, return to ring
        pm = bfs_mid(frame)
        for a in pm or []:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        print("mid", ls20.init(frame).cursor, "ui", ls20.ui_energy(frame))
        p66 = bfs_to(frame, (6, 6), armed=True)
        for a in p66 or []:
            frame = sess.action(DIR_TO_ACTION[a])["frame"]
        print("ring", ls20.init(frame).cursor, "c9", c9(frame), "ui", ls20.ui_energy(frame))

        prev = c9(frame)
        phases_seen = {}
        for i in range(12):
            for aid in (1, 2):
                resp = sess.action(aid)
                frame = resp["frame"]
                n = c9(frame)
                cur = ls20.init(frame).cursor
                flip = n != prev and abs(n - prev) >= 10
                print(f"osc{i} A{aid} {cur} c9 {prev}->{n} ui={ls20.ui_energy(frame)}"
                      f"{' FLIP' if flip else ''}")
                if flip and cur == (6, 6):
                    key = n
                    if key not in phases_seen:
                        phases_seen[key] = True
                        # save plane diff vs prev would need old plane; just note
                        g = ls20._plane(frame)
                        print("  phase foot66", g[
                            ls20.cursor_to_pixel((6, 6), ls20.grid_offset(frame))[1]:
                            ls20.cursor_to_pixel((6, 6), ls20.grid_offset(frame))[1] + 2,
                            ls20.cursor_to_pixel((6, 6), ls20.grid_offset(frame))[0]:
                            ls20.cursor_to_pixel((6, 6), ls20.grid_offset(frame))[0] + 5
                        ].tolist())
                        # try gate in THIS session for first two distinct phases
                        if len(phases_seen) <= 2:
                            frame2, ok = run_to_gate(sess, frame, f"c9={n}")
                            if ok:
                                print("CLEARED at phase", n)
                                return
                            # after failed attempt, game state is far from ring —
                            # cannot continue osc in same session usefully
                            print("phase try done; stop (state spent)")
                            return
                prev = n
        print("no clear from flips", list(phases_seen))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
