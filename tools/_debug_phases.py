import json
from pathlib import Path
from collections import deque
from longquan.interactive import ls20
from longquan.interactive.match import carrying_bbox_from_cursor
from tools.ls20_seated_clear import MAX_FUEL, _ov, _ov_stamp, _pickup_mask
from tools.ls20_online_validate import DIR_TO_ACTION
from longquan.interactive.state import DIRS

data = json.loads(Path("tests/fixtures/ls20_l2_frame_from_rec.json").read_text())
frame = data["frame"]
state = ls20.init(frame)
offset = ls20.grid_offset(frame)
marker = [g.shape for g in state.goals if g.id == "ls20-marker"][0]
stamp = [g.shape for g in state.goals if g.id == "ls20-stamp"][0]
pickups = ls20.energy_pickups(frame)
walk_u = ls20.build_walkable(frame, offset, armed=False)
walk_a = ls20.build_walkable(frame, offset, armed=True)
print("pickups", pickups, "armed-only", sorted(walk_a - walk_u))

# replicate phase A
def bfs(start_cursor, start_fuel, start_mask, armed, goal_fn):
    start = (start_cursor[0], start_cursor[1], start_fuel, start_mask)
    q = deque([(start, [])])
    seen = {start}
    while q:
        (cx, cy, fuel, pmask), path = q.popleft()
        if goal_fn((cx, cy), fuel, pmask, path):
            return path, fuel, pmask, (cx, cy)
        if fuel <= 0:
            continue
        walk = walk_a if armed else walk_u
        for dx, dy in DIRS:
            nxt = (cx + dx, cy + dy)
            if nxt not in walk:
                continue
            n_fuel = fuel - 1
            n_mask, ref = _pickup_mask(nxt, offset, pickups, pmask)
            if ref:
                n_fuel = MAX_FUEL
            key = (nxt[0], nxt[1], n_fuel, n_mask)
            if key in seen:
                continue
            seen.add(key)
            q.append((key, path + [(dx, dy)]))
    return None, None, None, None

def goal_contact(c, fuel, pmask, _):
    return _ov(carrying_bbox_from_cursor(c, offset), marker) > 0 and pmask != 0 and fuel >= 5

pa, fuel, pmask, cur = bfs(state.cursor, 20, 0, False, goal_contact)
print("phaseA", len(pa) if pa else None, "fuel", fuel, "mask", pmask, "cur", cur)
if pa is None:
    raise SystemExit("A fail")

ritual = [(0, -1), (0, 1), (0, 1), (0, -1)]
for d in ritual:
    nxt = (cur[0] + d[0], cur[1] + d[1])
    print("ritual", d, "from", cur, "to", nxt, "ok", nxt in walk_u)
    fuel -= 1
    pmask, ref = _pickup_mask(nxt, offset, pickups, pmask)
    if ref:
        fuel = MAX_FUEL
    cur = nxt
print("after ritual", cur, "fuel", fuel, "mask", pmask)

pb, fuel2, pmask2, cur2 = bfs(cur, fuel, pmask, True, lambda c, f, m, p: _ov_stamp(c, offset, stamp) >= 10)
print("phaseB", len(pb) if pb else None, "fuel", fuel2, "cur", cur2, "seen check:")
# how many stamp cells in walk_a
print("stamp ov cells", [(c, _ov_stamp(c, offset, stamp)) for c in walk_a if _ov_stamp(c, offset, stamp) >= 10])
