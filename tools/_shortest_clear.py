"""Combined armed-state BFS for one ls20 level; report shortest clear length."""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20, match
from longquan.interactive.state import DIRS, WorldState
from tools.ls20_seated_clear import _ov_stamp


def shortest_clear(frame):
    state0 = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    walk_u = ls20.build_walkable(frame, offset, armed=False)
    walk_a = ls20.build_walkable(frame, offset, armed=True)
    markers = [g.shape for g in state0.goals if g.id == "ls20-marker"]
    stamps = [g.shape for g in state0.goals if g.id == "ls20-stamp"]
    if not markers or not stamps:
        raise RuntimeError("missing goals")
    marker, stamp = markers[0], stamps[0]

    # state key: (cx, cy, armed)
    start = (state0.cursor[0], state0.cursor[1], False)
    q = deque([(start, [])])
    seen = {start}
    best = None
    while q:
        (cx, cy, armed), path = q.popleft()
        walk = walk_a if armed else walk_u
        # goal check
        if armed and _ov_stamp((cx, cy), offset, stamp) > 0:
            best = path
            break
        for dx, dy in DIRS:
            nxt = (cx + dx, cy + dy)
            if nxt not in walk:
                continue
            # react arming
            st = WorldState(
                grid_w=64, grid_h=64, cursor=nxt, walkable=walk,
                carrying=True, goals=state0.goals, steps_used=len(path) + 1,
                steps_limit=99, armed=armed,
            )
            st2 = match.react(st, offset=offset)
            key = (nxt[0], nxt[1], st2.armed)
            if key in seen:
                continue
            seen.add(key)
            q.append((key, path + [(dx, dy)]))
    return best, len(best) if best else None, len(seen), marker, stamp, state0.cursor


def main():
    for name in [
        "tests/fixtures/ls20_l2_frame_from_rec.json",
        "tests/fixtures/ls20_l1_frame_live.json",
    ]:
        data = json.loads((ROOT / name).read_text(encoding="utf-8"))
        # for L2 rec fixture cursor is (5,7)/(29,35)
        path, n, seen, marker, stamp, cur = shortest_clear(data["frame"])
        print(name, "cursor", cur, "marker", marker, "stamp", stamp,
              "shortest", n, "seen", seen)
        if path and n <= 25:
            from tools.ls20_online_validate import DIR_TO_ACTION
            print("actions", [DIR_TO_ACTION[a] for a in path])


if __name__ == "__main__":
    main()
