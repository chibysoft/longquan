"""Replay recording L5 by trying dirs until cursor matches next waypoint."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l5_unlock_trace import clear_l4

REC = Path(
    r"D:\Projects\ARC-AGI-3-Agents\recordings"
    r"\ls20-9607627b.lingjingsolo.800.5f1bf1fd-a88e-4c5f-8c63-3c85bc6f5f97.recording.jsonl"
)


def rec_cursors():
    out = []
    with open(REC, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            o = json.loads(line)["data"]
            lv = o.get("levels_completed") or 0
            if lv < 4:
                continue
            cur = ls20.init(o["frame"]).cursor
            out.append((i, cur, lv))
            if lv >= 5:
                break
    return out


def main():
    curs = rec_cursors()
    while curs and curs[0][1] != (9, 7):
        curs.pop(0)

    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l5_smart_replay"])
        frame, _ = clear_l4(sess)
        assert ls20.init(frame).cursor == (9, 7)

        for j in range(1, len(curs)):
            want = curs[j][1]
            lv_want = curs[j][2]
            before = ls20.init(frame).cursor
            if before == want:
                continue
            matched = False
            # Prefer likely dir from delta
            dx = want[0] - before[0]
            dy = want[1] - before[1]
            order = []
            if abs(dx) + abs(dy) == 1:
                order = [(dx, dy)]
            else:
                if dy < 0:
                    order.append((0, -1))
                if dy > 0:
                    order.append((0, 1))
                if dx < 0:
                    order.append((-1, 0))
                if dx > 0:
                    order.append((1, 0))
            for a in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                if a not in order:
                    order.append(a)

            # Try dirs; if wrong, we cannot undo — so only try best first.
            # For multi-cell jumps, the first preferred dir should be the warp.
            a = order[0]
            r = sess.action(DIR_TO_ACTION[a])
            frame = r["frame"]
            live = ls20.init(frame).cursor
            ok = live == want
            print(
                f"{j:02d} {before} try{a} -> {live} want={want} "
                f"{'OK' if ok else 'BAD'} ui={ls20.ui_energy(frame)} "
                f"lv={r.get('levels_completed')}"
            )
            if int(r.get("levels_completed") or 0) >= 5:
                print("PASS L5")
                return
            if not ok:
                # If close to end, try remaining dirs from NEW position is useless.
                # Instead: BFS goto want
                from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs
                for _ in range(30):
                    if ls20.init(frame).cursor == want:
                        print("  recovered", want)
                        matched = True
                        break
                    offset = ls20.grid_offset(frame)
                    walk = ls20.build_walkable(frame, offset, armed=True)
                    warps = ls20.detect_warps(frame, offset)
                    path, _, _, _ = _energy_bfs(
                        ls20.init(frame).cursor, MAX_FUEL, 0, walk, [], offset,
                        lambda c, _f, _p, w=want: c == w, warps,
                    )
                    if not path:
                        print("  cannot recover to", want, "at", ls20.init(frame).cursor)
                        break
                    frame = sess.action(DIR_TO_ACTION[path[0]])["frame"]
                if not matched and ls20.init(frame).cursor != want:
                    if j >= len(curs) - 5:
                        print("fail near end")
                        # still try UP if at 10,10
                        if ls20.init(frame).cursor == (10, 10):
                            r = sess.action(1)
                            print("final U", ls20.init(r["frame"]).cursor,
                                  r.get("levels_completed"))
                        return
    finally:
        sess.close()


if __name__ == "__main__":
    main()
