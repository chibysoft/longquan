"""Exact-replay recording L5 cursor deltas from live L4 clear spawn."""
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

DIR_FROM_DELTA = {
    (0, -1): (0, -1),
    (0, 1): (0, 1),
    (-1, 0): (-1, 0),
    (1, 0): (1, 0),
}


def rec_cursors():
    out = []
    with open(REC, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            o = json.loads(line)["data"]
            if (o.get("levels_completed") or 0) < 4:
                continue
            if (o.get("levels_completed") or 0) >= 5:
                out.append((i, ls20.init(o["frame"]).cursor, o["levels_completed"]))
                break
            out.append((i, ls20.init(o["frame"]).cursor, o["levels_completed"]))
    return out


def main():
    curs = rec_cursors()
    # skip first (1,1) end of L4; start from (9,7) spawn
    while curs and curs[0][1] != (9, 7):
        curs.pop(0)
    print("rec len from spawn", len(curs), "first", curs[0], "last", curs[-1])

    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l5_exact_replay"])
        frame, _ = clear_l4(sess)
        cur = ls20.init(frame).cursor
        print("live spawn", cur, "ui", ls20.ui_energy(frame))
        assert cur == (9, 7), cur

        for j in range(1, len(curs)):
            i_prev, prev, _ = curs[j - 1]
            i_now, want, lv = curs[j]
            live = ls20.init(frame).cursor
            if live != prev:
                print(f"DESYNC before step to {want}: live={live} expected_prev={prev} "
                      f"rec_i={i_now}")
                # try to continue from live toward want using delta from prev->want
            dx = want[0] - prev[0]
            dy = want[1] - prev[1]
            # map large deltas to portal single actions — try each cardinal that
            # recording likely used; if |dx|+|dy|!=1, fire the primary axis
            if abs(dx) + abs(dy) == 1:
                a = (dx, dy)
            elif abs(dx) >= abs(dy) and dx != 0:
                a = (1 if dx > 0 else -1, 0)
            elif dy != 0:
                a = (0, 1 if dy > 0 else -1)
            else:
                print("zero delta", prev, want)
                continue
            before = ls20.init(frame).cursor
            r = sess.action(DIR_TO_ACTION[a])
            frame = r["frame"]
            live = ls20.init(frame).cursor
            ok = live == want
            mark = "OK" if ok else "BAD"
            print(
                f"{j:02d} rec{i_now} {before} {a} -> {live} want={want} {mark} "
                f"ui={ls20.ui_energy(frame)} lv={r.get('levels_completed')}"
            )
            if int(r.get("levels_completed") or 0) >= 5:
                print("PASS L5")
                return
            if not ok:
                # if we landed elsewhere but same as a warp destination, note
                if j >= len(curs) - 3:
                    # try other dirs from before
                    print(" trying alts from restore — stop")
                    break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
