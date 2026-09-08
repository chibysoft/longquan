"""r11l L2 online clear: compact-park chrome15, formation-migrate chrome12."""
from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_core import (
    centroid,
    centroid_ok,
    centroid_path_ok,
    clearance_path,
    nonlocked_wps,
    stagger_pads,
    _plane,
)
from tools.r11l_l2_probe import assign_wps, hollow_goals, ships
from tools.r11l_seated_clear import act6, clear_l1, reset

FLOOR = 5


def goals_by_chrome(frame):
    return {g["chrome"]: g["c"] for g in hollow_goals(frame)}


def owned_map(frame):
    asg = assign_wps(frame)
    if not asg or not asg[1]:
        return {}
    return {s["chrome"]: [w["c"] for w in wps] for s, wps in asg[1]}


def near_any(p, pts, cheb=5) -> bool:
    return any(max(abs(p[0] - q[0]), abs(p[1] - q[1])) < cheb for q in pts)


def step_budget(frame) -> int:
    """Left-column color-0 count ≈ remaining ACTION6 budget."""
    g = _plane(frame)
    return int((g[:, 0] == 0).sum())


def move_wp(sess, data, wp_c, dest, locked):
    wps = r11l.waypoints(data["frame"])
    live = min(wps, key=lambda w: abs(w["c"][0] - wp_c[0]) + abs(w["c"][1] - wp_c[1]))
    if any(abs(live["c"][0] - fx) + abs(live["c"][1] - fy) <= 2 for fx, fy in locked):
        return data, wp_c, "forbidden"
    if abs(live["c"][0] - wp_c[0]) + abs(live["c"][1] - wp_c[1]) > 3:
        return data, wp_c, "lost"
    if near_any(dest, locked, cheb=5):
        return data, wp_c, "near_locked"
    if any(
        abs(w["c"][0] - dest[0]) + abs(w["c"][1] - dest[1]) <= 1
        and abs(w["c"][0] - live["c"][0]) + abs(w["c"][1] - live["c"][1]) > 1
        for w in wps
    ):
        return data, wp_c, "occupied"
    if not live["selected"]:
        data = act6(sess, *live["c"])
        if data.get("state") == "GAME_OVER":
            return data, wp_c, "dead"
    before = {w["c"] for w in r11l.waypoints(data["frame"])}
    # one arm click + one animate; stop early if already moved
    for k in range(2):
        data = act6(sess, *dest)
        if data.get("state") == "GAME_OVER":
            return data, wp_c, "dead"
        after = {w["c"] for w in r11l.waypoints(data["frame"])}
        appeared = after - before
        if appeared:
            newc = min(appeared, key=lambda c: abs(c[0] - dest[0]) + abs(c[1] - dest[1]))
            return data, newc, "moved"
    after = {w["c"] for w in r11l.waypoints(data["frame"])}
    if any(abs(c[0] - dest[0]) + abs(c[1] - dest[1]) <= 1 for c in after):
        return (
            data,
            min(after, key=lambda c: abs(c[0] - dest[0]) + abs(c[1] - dest[1])),
            "already",
        )
    return data, wp_c, "noop"


def _wp_walkable(g, x, y) -> bool:
    """Cells a waypoint may land on: floor, or existing cross colors."""
    if not (0 <= x < 64 and 0 <= y < 64):
        return False
    return int(g[y, x]) in (FLOOR, 3, 0, 6)


def floor_dist(g, start, goal, limit=80):
    """Manhattan-on-floor distance, or None if unreachable within limit."""
    if start == goal:
        return 0
    q = deque([(start, 0)])
    seen = {start}
    while q:
        (x, y), d = q.popleft()
        if d >= limit:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) in seen:
                continue
            if (nx, ny) != goal and not _wp_walkable(g, nx, ny):
                continue
            if (nx, ny) == goal:
                return d + 1
            seen.add((nx, ny))
            q.append(((nx, ny), d + 1))
    return None


def floor_bfs(g, start, goal, max_step=14):
    """Short walkable path; return next hop ≤ max_step toward goal.

    Start may sit on a waypoint color (not floor); still allow leaving it.
    """
    if start == goal:
        return goal
    q = deque([start])
    prev = {start: None}
    found = None
    while q:
        x, y = q.popleft()
        if (x, y) == goal:
            found = (x, y)
            break
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) in prev:
                continue
            if (nx, ny) != goal and not _wp_walkable(g, nx, ny):
                continue
            prev[(nx, ny)] = (x, y)
            q.append((nx, ny))
    if found is None:
        best = None
        for p in prev:
            d = abs(p[0] - goal[0]) + abs(p[1] - goal[1])
            if best is None or d < best[0]:
                best = (d, p)
        if best is None or best[1] == start:
            bx, by = start
            gx, gy = goal
            for rad in range(1, max_step + 1):
                for dy in range(-rad, rad + 1):
                    for dx in range(-rad, rad + 1):
                        if abs(dx) + abs(dy) != rad:
                            continue
                        nx, ny = bx + dx, by + dy
                        if abs(nx - gx) + abs(ny - gy) >= abs(bx - gx) + abs(by - gy):
                            continue
                        if not _wp_walkable(g, nx, ny) and (nx, ny) != goal:
                            continue
                        return (nx, ny)
            return None
        found = best[1]
    path = []
    cur = found
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    if len(path) == 1:
        return path[0]
    acc = 0
    dest = path[0]
    for p in path[1:]:
        step_d = abs(p[0] - dest[0]) + abs(p[1] - dest[1])
        if acc + step_d > max_step and acc > 0:
            break
        acc += step_d
        dest = p
        if acc >= max_step:
            break
    return dest


def compact_cands(g, goal, radius=10):
    gx, gy = goal
    out = []
    for rad in range(0, radius + 1):
        for dy in range(-rad, rad + 1):
            for dx in range(-rad, rad + 1):
                if rad and max(abs(dx), abs(dy)) != rad:
                    continue
                p = (gx + dx, gy + dy)
                if 0 <= p[0] < 64 and 0 <= p[1] < 64 and int(g[p[1], p[0]]) == FLOOR:
                    out.append(p)
    return out


def park_compact(sess, data, chrome, goal, owned, locked, lv0, budget=14, max_spread=12):
    blacklist = set()
    for _ in range(budget):
        me = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)
        dist = abs(me["c"][0] - goal[0]) + abs(me["c"][1] - goal[1])
        spread = max(
            (abs(p[0] - goal[0]) + abs(p[1] - goal[1]) for p in owned[chrome]),
            default=0,
        )
        print(
            f"  park{chrome} dist={dist} spread={spread} "
            f"ship={me['c']} wps={owned[chrome]}"
        )
        if dist <= 2 and spread <= max_spread:
            return data, owned, True
        if (data.get("levels_completed") or 0) > lv0:
            return data, owned, True
        g = _plane(data["frame"])
        cur = owned[chrome]
        cur_d = abs(centroid(cur)[0] - goal[0]) + abs(centroid(cur)[1] - goal[1])
        cands = compact_cands(g, goal, radius=12)
        best = None
        for i, wp in enumerate(cur):
            for dest in cands:
                if (wp, dest) in blacklist:
                    continue
                if max(abs(dest[0] - wp[0]), abs(dest[1] - wp[1])) < 1:
                    continue
                if abs(dest[0] - wp[0]) + abs(dest[1] - wp[1]) > 28:
                    continue
                if near_any(dest, [cur[j] for j in range(len(cur)) if j != i], cheb=5):
                    continue
                if near_any(dest, locked, cheb=5):
                    continue
                trial = list(cur)
                trial[i] = dest
                if not centroid_path_ok(cur, trial, g, samples=10):
                    continue
                nc = centroid(trial)
                nd = abs(nc[0] - goal[0]) + abs(nc[1] - goal[1])
                sp = max(abs(p[0] - goal[0]) + abs(p[1] - goal[1]) for p in trial)
                if nd + 0.3 < cur_d:
                    score = (0, nd, sp, i, dest)
                elif dist <= 2 and sp + 0.5 < spread:
                    score = (1, sp, nd, i, dest)
                else:
                    continue
                if best is None or score < best:
                    best = score
        if best is None:
            print(f"  park{chrome} stuck")
            return data, owned, dist <= 2
        *_, i, dest = best
        wp = owned[chrome][i]
        data, newc, st = move_wp(sess, data, wp, dest, locked)
        print(
            f"    {wp}->{dest} {st}->{newc} "
            f"ships={[(s['c'], s['chrome']) for s in ships(data['frame'])]}"
        )
        if st == "dead":
            return data, owned, False
        if st in ("noop", "forbidden", "lost", "near_locked", "occupied", "already"):
            blacklist.add((wp, dest))
            continue
        om = owned_map(data["frame"])
        if locked:
            owned[chrome] = free_wps_for(data["frame"], chrome, locked)
        elif chrome in om:
            owned[chrome] = om[chrome]
        else:
            owned[chrome][i] = newc
        if (data.get("levels_completed") or 0) > lv0:
            return data, owned, True
    me = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)
    return data, owned, abs(me["c"][0] - goal[0]) + abs(me["c"][1] - goal[1]) <= 2


def free_wps_for(frame, chrome, locked):
    """After locking the parked ship, every non-locked wp belongs to the migrant.

    Do NOT trust assign_waypoints mid-migrate — partitions drift and drop wps.
    """
    return nonlocked_wps(frame, locked)


def _floor_cell(g, p) -> bool:
    """Valid wp landing: floor or transient ship/wp ink (not wall/hazard)."""
    if not (0 <= p[0] < 64 and 0 <= p[1] < 64):
        return False
    return int(g[p[1], p[0]]) not in (2, 10)  # wall / hazard


def find_path_offsets(g, path, n: int):
    """Offsets that stay on floor for every path cell (tight-corridor sync)."""
    if not path or n < 2:
        return None
    preferred = [
        ((5, -3), (5, 3)),
        ((5, 0), (5, 5)),
        ((7, -3), (5, 3)),
        ((6, -3), (6, 3)),
        ((8, -2), (8, 8)),
        ((5, -5), (5, 5)),
        ((-5, -3), (-5, 3)),
    ]

    def lasts(offs):
        for cell in path:
            pts = [(cell[0] + o[0], cell[1] + o[1]) for o in offs]
            if not all(_floor_cell(g, p) for p in pts):
                return False
            if any(
                max(abs(pts[i][0] - pts[j][0]), abs(pts[i][1] - pts[j][1])) < 5
                for i in range(len(pts))
                for j in range(i + 1, len(pts))
            ):
                return False
        return True

    if n == 2:
        for offs in preferred:
            if lasts(offs):
                return offs
    # candidate ring offsets
    cands = []
    for rad in (5, 6, 7, 8):
        for dy in range(-rad, rad + 1):
            for dx in range(-rad, rad + 1):
                if max(abs(dx), abs(dy)) != rad:
                    continue
                cands.append((dx, dy))
    start = path[0]
    valid = [o for o in cands if _floor_cell(g, (start[0] + o[0], start[1] + o[1]))]
    valid.sort(key=lambda o: (-o[0], abs(o[1])))
    if n == 2:
        for i, a in enumerate(valid):
            for b in valid[i + 1 :]:
                if max(abs(a[0] - b[0]), abs(a[1] - b[1])) < 5:
                    continue
                offs = (a, b)
                if lasts(offs):
                    return offs
    chosen = []
    for o in valid:
        pts_try = chosen + [o]
        if any(max(abs(o[0] - c[0]), abs(o[1] - c[1])) < 5 for c in chosen):
            continue
        if lasts(tuple(pts_try)):
            chosen.append(o)
            if len(chosen) == n:
                return tuple(chosen)
    return None


def sync_follow_path(sess, data, chrome, goal, locked, lv0, max_wave=12):
    """Reshape to fixed offsets, then translate all free wps by the same delta."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)
    fine = clearance_path(data["frame"], me["c"], goal, step=1)
    print(f"sync{chrome} from={me['c']} goal={goal} fine_len={len(fine) if fine else 0}")
    if not fine:
        return data, False
    g = _plane(data["frame"])
    cur = free_wps_for(data["frame"], chrome, locked)
    if len(cur) < 2:
        return data, False
    offs = find_path_offsets(g, fine, len(cur))
    print(f"  offsets={offs} cur={cur}")
    if not offs:
        return data, False

    # reshape toward offsets at current ship
    ship = me["c"]
    targets = [(ship[0] + o[0], ship[1] + o[1]) for o in offs]
    pairs = assign_pads(cur, targets)
    blacklist = set()
    for _ in range(len(cur) + 3):
        cur = free_wps_for(data["frame"], chrome, locked)
        ship = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)["c"]
        targets = [(ship[0] + o[0], ship[1] + o[1]) for o in offs]
        # done reshaping?
        if all(
            min(abs(w[0] - t[0]) + abs(w[1] - t[1]) for t in targets) <= 2 for w in cur
        ):
            break
        pairs = assign_pads(cur, targets)
        moved = False
        for i, pad in pairs:
            wp = cur[i]
            if abs(wp[0] - pad[0]) + abs(wp[1] - pad[1]) <= 2:
                continue
            nxt = floor_bfs(g, wp, pad, max_step=14)
            if nxt is None or nxt == wp or (wp, nxt) in blacklist:
                continue
            if near_any(nxt, [cur[j] for j in range(len(cur)) if j != i], cheb=5):
                continue
            if near_any(nxt, locked, cheb=6):
                continue
            trial = list(cur)
            trial[i] = nxt
            if not centroid_path_ok(cur, trial, g, samples=12):
                continue
            data, newc, st = move_wp(sess, data, wp, nxt, locked)
            print(
                f"  reshape {wp}->{nxt} {st} ships={[(s['c'], s['chrome']) for s in ships(data['frame'])]} "
                f"bud={step_budget(data['frame'])}"
            )
            if st == "dead":
                return data, False
            if st in ("noop", "forbidden", "lost", "near_locked", "occupied", "already"):
                blacklist.add((wp, nxt))
                continue
            moved = True
            g = _plane(data["frame"])
            if (data.get("levels_completed") or 0) > lv0:
                return data, True
            break
        if not moved:
            break

    # sync waves along fine path
    cur = free_wps_for(data["frame"], chrome, locked)
    # recompute offsets from current formation relative to ship
    ship = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)["c"]
    # snap to chosen offs if close
    live_offs = offs
    idx = min(
        range(len(fine)),
        key=lambda i: abs(fine[i][0] - ship[0]) + abs(fine[i][1] - ship[1]),
    )
    for wave in range(max_wave):
        if (data.get("levels_completed") or 0) > lv0:
            return data, True
        if step_budget(data["frame"]) < 8:
            break
        ship = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)["c"]
        dist_goal = abs(ship[0] - goal[0]) + abs(ship[1] - goal[1])
        print(f"  sync wave{wave} ship={ship} d_goal={dist_goal} idx={idx} wps={cur}")
        if dist_goal <= 5:
            return data, True
        # find farthest reachable hop with same offsets
        g = _plane(data["frame"])
        best = None
        for j in range(min(len(fine) - 1, idx + 16), idx, -1):
            hop = fine[j]
            trial = [(hop[0] + o[0], hop[1] + o[1]) for o in live_offs]
            if not all(_floor_cell(g, p) for p in trial):
                continue
            if any(
                max(abs(trial[a][0] - trial[b][0]), abs(trial[a][1] - trial[b][1])) < 5
                for a in range(len(trial))
                for b in range(a + 1, len(trial))
            ):
                continue
            # match cur to trial by assign
            pairs = assign_pads(cur, trial)
            ordered = list(cur)
            for i, pad in pairs:
                ordered[i] = pad  # may be incomplete
            # build full trial aligned to cur order via pairs
            aligned = list(cur)
            for i, pad in pairs:
                aligned[i] = pad
            if len(pairs) < len(cur):
                continue
            if not centroid_path_ok(cur, aligned, g, samples=14):
                continue
            best = (j, hop, aligned)
            break
        if best is None:
            print("  sync stuck")
            break
        j, hop, aligned = best
        # move each wp to aligned target (farthest first)
        order = sorted(
            range(len(cur)),
            key=lambda i: abs(cur[i][0] - aligned[i][0])
            + abs(cur[i][1] - aligned[i][1]),
            reverse=True,
        )
        for i in order:
            cur = free_wps_for(data["frame"], chrome, locked)
            if len(cur) < len(live_offs):
                print("  sync lost wps", cur)
                return data, False
            # re-align after prior moves
            trial = [(hop[0] + o[0], hop[1] + o[1]) for o in live_offs]
            pairs = assign_pads(cur, trial)
            if len(pairs) < len(cur):
                break
            aligned = list(cur)
            for ii, pad in pairs:
                aligned[ii] = pad
            if i >= len(cur) or cur[i] == aligned[i]:
                continue
            if near_any(aligned[i], locked, cheb=6):
                continue
            data, newc, st = move_wp(sess, data, cur[i], aligned[i], locked)
            print(
                f"    sync {cur[i]}->{aligned[i]} {st}->{newc} "
                f"ships={[(s['c'], s['chrome']) for s in ships(data['frame'])]} "
                f"bud={step_budget(data['frame'])}"
            )
            if st == "dead":
                return data, False
            if st in ("noop", "forbidden", "lost", "near_locked", "occupied"):
                return data, False
            if (data.get("levels_completed") or 0) > lv0:
                return data, True
        idx = j
        cur = free_wps_for(data["frame"], chrome, locked)

    ship = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)["c"]
    return data, abs(ship[0] - goal[0]) + abs(ship[1] - goal[1]) <= 6


def formation_pads(g, center, n: int, ring_min=5, ring_max=10):
    """Pads on a ring around center so wps stay outside the ship's 5×5 body.

    For n≥3, also require the formation centroid near ``center`` and each pad
    Chebyshev ≥3 from that centroid (else a wp lands inside the hull).
    """
    from itertools import combinations

    cx, cy = center
    cands = []
    for rad in range(ring_min, ring_max + 1):
        for dy in range(-rad, rad + 1):
            for dx in range(-rad, rad + 1):
                if max(abs(dx), abs(dy)) != rad:
                    continue
                p = (cx + dx, cy + dy)
                if not (0 <= p[0] < 64 and 0 <= p[1] < 64):
                    continue
                if int(g[p[1], p[0]]) != FLOOR:
                    continue
                cands.append(p)

    # 2-wp: legacy greedy (L2 sync corridors); centroid constraint too strict.
    if n <= 2:
        out = []
        for p in cands:
            if all(max(abs(p[0] - q[0]), abs(p[1] - q[1])) >= 5 for q in out):
                out.append(p)
                if len(out) >= n:
                    return out
        extra = [p for p in stagger_pads(g, center, n + 3) if p not in out]
        return (out + extra)[:n]

    def ok_set(pads):
        for i in range(len(pads)):
            for j in range(i + 1, len(pads)):
                if max(abs(pads[i][0] - pads[j][0]), abs(pads[i][1] - pads[j][1])) < 5:
                    return False
        c = centroid(pads)
        ci = (int(round(c[0])), int(round(c[1])))
        if abs(ci[0] - cx) + abs(ci[1] - cy) > 4:
            return False
        if any(max(abs(p[0] - ci[0]), abs(p[1] - ci[1])) < 3 for p in pads):
            return False
        return True

    cands.sort(
        key=lambda p: (
            abs(abs(p[0] - cx) - abs(p[1] - cy)),
            abs(p[0] - cx) + abs(p[1] - cy),
        )
    )
    best = None
    for pool_n in (20, 36, 56):
        pool = cands[:pool_n]
        if len(pool) < n:
            continue
        for combo in combinations(pool, n):
            if not ok_set(combo):
                continue
            c = centroid(combo)
            score = (
                abs(c[0] - cx) + abs(c[1] - cy),
                sum(abs(p[0] - cx) + abs(p[1] - cy) for p in combo),
                max(abs(p[0] - cx) + abs(p[1] - cy) for p in combo),
            )
            if best is None or score < best[0]:
                best = (score, list(combo))
                if score[0] <= 1.5 and score[2] <= 12:
                    return best[1]
        if best is not None and best[0][0] <= 3 and best[0][2] <= 14:
            return best[1]
    if best is not None:
        return best[1]

    out = []
    for p in cands:
        if all(max(abs(p[0] - q[0]), abs(p[1] - q[1])) >= 5 for q in out):
            out.append(p)
            if len(out) >= n:
                return out
    extra = [p for p in stagger_pads(g, center, n + 3) if p not in out]
    return (out + extra)[:n]


def assign_pads(wps, pads, g=None):
    """Assign wps→pads. Prefer min total floor distance when grid given."""
    from itertools import permutations

    if not wps or not pads:
        return []
    n = min(len(wps), len(pads))
    wps_n = list(wps[:n])
    # Build mutually-separated pad shortlist (already separated by formation_pads).
    pad_pool = list(pads)
    best = None
    for chosen in permutations(pad_pool, n):
        # mutual sep already in pads; still guard
        ok = True
        for i in range(n):
            for j in range(i + 1, n):
                if max(abs(chosen[i][0] - chosen[j][0]), abs(chosen[i][1] - chosen[j][1])) < 5:
                    ok = False
                    break
            if not ok:
                break
        if not ok:
            continue
        cost = 0
        for i in range(n):
            if g is not None:
                d = floor_dist(g, wps_n[i], chosen[i])
                cost += 80 if d is None else d
            else:
                cost += abs(chosen[i][0] - wps_n[i][0]) + abs(chosen[i][1] - wps_n[i][1])
        if best is None or cost < best[0]:
            best = (cost, [(i, chosen[i]) for i in range(n)])
    if best is not None:
        return best[1]

    # Fallback: farthest wp → nearest free pad (legacy).
    remaining_w = list(range(len(wps)))
    remaining_p = list(pads)
    pairs = []
    while remaining_w and remaining_p:
        best_g = None
        for i in remaining_w:
            nearest = min(
                remaining_p,
                key=lambda p: abs(p[0] - wps[i][0]) + abs(p[1] - wps[i][1]),
            )
            d = abs(nearest[0] - wps[i][0]) + abs(nearest[1] - wps[i][1])
            score = (-d, i, nearest)
            if best_g is None or score < best_g:
                best_g = score
        _, i, pad = best_g
        pairs.append((i, pad))
        remaining_w.remove(i)
        remaining_p = [
            p for p in remaining_p if max(abs(p[0] - pad[0]), abs(p[1] - pad[1])) >= 5
        ]
    return pairs


def formation_migrate(sess, data, chrome, goal, locked, lv0, step=14):
    """At each path hop, walk lagging wps to ring pads; minimize ACTION6 uses."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)
    n_free0 = len(free_wps_for(data["frame"], chrome, locked))
    # 4-wp: fine path through the y=34 neck, then coarse to save budget.
    if n_free0 >= 4:
        fine = clearance_path(data["frame"], me["c"], goal, step=1)
        if not fine:
            return data, False
        path = [fine[0]]
        neck_done = False
        i = 0
        while i < len(fine) - 1:
            cell = fine[i]
            # Neck: stay south of hazard shelf (y>=34) and x advances.
            if not neck_done:
                if cell[1] >= 34 and cell[0] >= 24:
                    neck_done = True
                    stride = 12
                else:
                    stride = 5
            else:
                stride = 12
            j = min(len(fine) - 1, i + stride)
            path.append(fine[j])
            i = j
        if path[-1] != fine[-1]:
            path.append(fine[-1])
    else:
        path = clearance_path(data["frame"], me["c"], goal, step=step)
    print(f"migrate{chrome} from={me['c']} goal={goal} path={path} budget={step_budget(data['frame'])}")
    if not path:
        return data, False
    blacklist = set()
    last_pair = None  # (wp, dest) to block immediate reverse

    for hi in range(1, len(path)):
        hop = path[hi]
        n_free = max(2, len(free_wps_for(data["frame"], chrome, locked)))
        max_rnd = (n_free + 2) if n_free >= 4 else (n_free * 2 + 3)
        for rnd in range(max_rnd):
            bud = step_budget(data["frame"])
            me = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)
            dist_goal = abs(me["c"][0] - goal[0]) + abs(me["c"][1] - goal[1])
            dist_hop = abs(me["c"][0] - hop[0]) + abs(me["c"][1] - hop[1])
            cur = free_wps_for(data["frame"], chrome, locked)
            print(
                f"  hop#{hi} rnd{rnd} hop={hop} ship={me['c']} "
                f"d_hop={dist_hop} d_goal={dist_goal} bud={bud} wps={cur}"
            )
            goal_ok = 8 if n_free >= 4 else 5
            if dist_goal <= goal_ok:
                return data, True
            if bud < 8:
                print("  budget low, stop migrate")
                return data, dist_goal <= goal_ok
            if (data.get("levels_completed") or 0) > lv0:
                return data, True
            if len(cur) < 2:
                print("  too few free wps", cur)
                break

            g = _plane(data["frame"])
            if n_free >= 4:
                if dist_hop <= 3:
                    break
            elif dist_hop <= 5 and all(
                abs(w[0] - hop[0]) + abs(w[1] - hop[1]) <= 14 for w in cur
            ):
                break

            pads = formation_pads(
                g, hop, max(len(cur), 3) if n_free < 4 else len(cur), ring_min=5, ring_max=11
            )
            pairs = assign_pads(cur, pads, g if n_free >= 4 else None)
            candidates = []
            for i, pad in pairs:
                wp = cur[i]
                if abs(wp[0] - pad[0]) + abs(wp[1] - pad[1]) <= 3:
                    continue
                # Large hops often collide with sibling wps / hull; try shorter steps.
                chosen = None
                for max_step in (18, 10, 6, 3):
                    nxt = floor_bfs(g, wp, pad, max_step=max_step)
                    if nxt is None or nxt == wp:
                        continue
                    if (wp, nxt) in blacklist:
                        continue
                    if last_pair and last_pair == (nxt, wp):
                        continue
                    if near_any(nxt, [cur[j] for j in range(len(cur)) if j != i], cheb=5):
                        continue
                    if near_any(nxt, locked, cheb=6):
                        continue
                    trial = list(cur)
                    trial[i] = nxt
                    pc = centroid(trial)
                    pc_i = (int(round(pc[0])), int(round(pc[1])))
                    if any(max(abs(p[0] - pc_i[0]), abs(p[1] - pc_i[1])) < 3 for p in trial):
                        continue
                    if not centroid_path_ok(cur, trial, g, samples=14):
                        continue
                    nc = centroid(trial)
                    sc = (int(round(nc[0])), int(round(nc[1])))
                    d_goal_new = abs(sc[0] - goal[0]) + abs(sc[1] - goal[1])
                    d_hop_new = abs(sc[0] - hop[0]) + abs(sc[1] - hop[1])
                    lag = abs(wp[0] - pad[0]) + abs(wp[1] - pad[1])
                    lag_new = abs(nxt[0] - pad[0]) + abs(nxt[1] - pad[1])
                    # Graph distance handles hazard detours better than Manhattan.
                    gd0 = floor_dist(g, wp, pad)
                    gd1 = floor_dist(g, nxt, pad)
                    progress = d_hop_new < dist_hop or d_goal_new < dist_goal
                    lag_close = (
                        gd0 is not None
                        and gd1 is not None
                        and gd1 < gd0
                        and d_hop_new <= dist_hop + 8
                    ) or (lag_new < lag and d_hop_new <= dist_hop + 8)
                    if not progress and not lag_close:
                        continue
                    if d_goal_new > dist_goal + 12 and not lag_close:
                        continue
                    travel = abs(nxt[0] - wp[0]) + abs(nxt[1] - wp[1])
                    chosen = (
                        0 if progress else 1,
                        d_hop_new,
                        d_goal_new,
                        gd1 if gd1 is not None else lag_new,
                        -travel,
                        i,
                        nxt,
                        pad,
                    )
                    break
                if chosen is not None:
                    candidates.append(chosen)

            if not candidates:
                # Emergency micro-step toward hop when pad path_ok is blocked.
                for i, wp in enumerate(cur):
                    for dy in range(-3, 4):
                        for dx in range(-3, 4):
                            man = abs(dx) + abs(dy)
                            if man == 0 or man > 3:
                                continue
                            nxt = (wp[0] + dx, wp[1] + dy)
                            if not (0 <= nxt[0] < 64 and 0 <= nxt[1] < 64):
                                continue
                            if int(g[nxt[1], nxt[0]]) in (2, 10):
                                continue
                            if (wp, nxt) in blacklist:
                                continue
                            if near_any(nxt, [cur[j] for j in range(len(cur)) if j != i], cheb=5):
                                continue
                            if near_any(nxt, locked, cheb=6):
                                continue
                            trial = list(cur)
                            trial[i] = nxt
                            pc = centroid(trial)
                            pc_i = (int(round(pc[0])), int(round(pc[1])))
                            if any(
                                max(abs(p[0] - pc_i[0]), abs(p[1] - pc_i[1])) < 3
                                for p in trial
                            ):
                                continue
                            if not centroid_path_ok(cur, trial, g, samples=14):
                                continue
                            d_hop_new = abs(pc_i[0] - hop[0]) + abs(pc_i[1] - hop[1])
                            d_goal_new = abs(pc_i[0] - goal[0]) + abs(pc_i[1] - goal[1])
                            if d_hop_new >= dist_hop and d_goal_new >= dist_goal:
                                continue
                            candidates.append(
                                (0, d_hop_new, d_goal_new, 0, -man, i, nxt, hop)
                            )
                if not candidates:
                    print("  no formation step")
                    break
            candidates.sort()
            *_, i, dest, pad = candidates[0]
            wp = cur[i]
            data, newc, st = move_wp(sess, data, wp, dest, locked)
            print(
                f"    {wp}->{dest} (pad{pad}) {st}->{newc} "
                f"ships={[(s['c'], s['chrome']) for s in ships(data['frame'])]} "
                f"lv={data.get('levels_completed')} bud={step_budget(data['frame'])}"
            )
            if st == "dead":
                return data, False
            if st in ("noop", "forbidden", "lost", "near_locked", "occupied", "already"):
                blacklist.add((wp, dest))
                continue
            last_pair = (wp, dest)
            if (data.get("levels_completed") or 0) > lv0:
                return data, True

        me = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)
        dist_goal = abs(me["c"][0] - goal[0]) + abs(me["c"][1] - goal[1])
        print(f"  after hop#{hi} ship={me['c']} dist_goal={dist_goal} bud={step_budget(data['frame'])}")
        if dist_goal <= 5:
            return data, True
        if (data.get("levels_completed") or 0) > lv0:
            return data, True
    return data, False


def clear_dual(sess, data, label: str = "L?") -> tuple:
    """Park nearest chrome ship, formation-migrate the other onto its goal."""
    lv0 = data.get("levels_completed") or 0
    sh = ships(data["frame"])
    if len(sh) < 2:
        data = act6(sess, 32, 32)
        print(f"  {label} settle", ships(data["frame"]))

    gmap = goals_by_chrome(data["frame"])
    owned = owned_map(data["frame"])
    print(f"  {label} enter ships", ships(data["frame"]), "goals", gmap, "owned", owned)
    if len(gmap) < 2 or len(ships(data["frame"])) < 2:
        raise RuntimeError(
            f"{label} need 2 ships+goals: ships={ships(data['frame'])} goals={gmap}"
        )

    # L3: park chrome14 first (open west path); chrome15 corridor is tight
    if label.startswith("L3") and 14 in gmap and 15 in gmap:
        first, second = 14, 15
    else:
        order = sorted(
            ships(data["frame"]),
            key=lambda s: abs(s["c"][0] - gmap[s["chrome"]][0])
            + abs(s["c"][1] - gmap[s["chrome"]][1]),
        )
        first, second = order[0]["chrome"], order[1]["chrome"]

    # While moving first, freeze second's current wps
    freeze_second = list(owned.get(second, []))
    print(f"  freeze chrome{second}", freeze_second)

    me = next(s for s in ships(data["frame"]) if s["chrome"] == first)
    dist0 = abs(me["c"][0] - gmap[first][0]) + abs(me["c"][1] - gmap[first][1])
    if dist0 > 8:
        n_free = len(free_wps_for(data["frame"], first, freeze_second))
        ok = False
        if n_free == 2 and label.startswith("L3"):
            # L3 tight corridor: sync-follow with fixed offsets
            data, ok = sync_follow_path(
                sess, data, first, gmap[first], freeze_second, lv0
            )
        me = next(s for s in ships(data["frame"]) if s["chrome"] == first)
        dist_m = abs(me["c"][0] - gmap[first][0]) + abs(me["c"][1] - gmap[first][1])
        if dist_m > 10:
            data, ok = formation_migrate(
                sess, data, first, gmap[first], freeze_second, lv0,
                step=8 if label.startswith("L3") else 14,
            )
            me = next(s for s in ships(data["frame"]) if s["chrome"] == first)
            dist_m = abs(me["c"][0] - gmap[first][0]) + abs(me["c"][1] - gmap[first][1])
            if dist_m > 12 and n_free == 2:
                data, ok = sync_follow_path(
                    sess, data, first, gmap[first], freeze_second, lv0
                )
                me = next(s for s in ships(data["frame"]) if s["chrome"] == first)
                dist_m = abs(me["c"][0] - gmap[first][0]) + abs(me["c"][1] - gmap[first][1])
        print(f"  migrate-park{first} ok={ok} dist={dist_m}", ships(data["frame"]))
        if data.get("state") == "GAME_OVER":
            raise RuntimeError(f"GAME_OVER migrate-parking first ({label})")
        if (data.get("levels_completed") or 0) > lv0:
            return data, []

    owned = owned_map(data["frame"])
    # refresh freeze in case second drifted (shouldn't)
    freeze_second = list(owned.get(second, freeze_second))
    owned[first] = [
        p
        for p in owned.get(first, free_wps_for(data["frame"], first, freeze_second))
        if not near_any(p, freeze_second, cheb=3)
    ]
    data, owned, ok = park_compact(
        sess,
        data,
        first,
        gmap[first],
        owned,
        freeze_second,
        lv0,
        budget=16,
        max_spread=14,
    )
    print(f"  park{first} ok={ok}", ships(data["frame"]), owned.get(first))
    if data.get("state") == "GAME_OVER":
        raise RuntimeError(f"GAME_OVER parking first ({label})")
    if (data.get("levels_completed") or 0) > lv0:
        return data, []
    me = next(s for s in ships(data["frame"]) if s["chrome"] == first)
    dist_f = abs(me["c"][0] - gmap[first][0]) + abs(me["c"][1] - gmap[first][1])
    if dist_f > 6:
        raise RuntimeError(f"could not park chrome {first} dist={dist_f}")

    locked = list(owned.get(first, []))
    # if assign drifted, lock whatever is near the parked ship centroid
    if len(locked) < 2:
        locked = [
            w["c"]
            for w in r11l.waypoints(data["frame"])
            if abs(w["c"][0] - me["c"][0]) + abs(w["c"][1] - me["c"][1]) <= 12
        ]
        # keep only those that aren't clearly the other ship's far wps
        locked = locked[: max(2, len(owned.get(first, [])))]
    print(f"  locked chrome{first}", locked)

    data, ok = formation_migrate(
        sess, data, second, gmap[second], locked, lv0,
        step=8 if label.startswith("L3") else 14,
    )
    me2 = next(s for s in ships(data["frame"]) if s["chrome"] == second)
    dist2 = abs(me2["c"][0] - gmap[second][0]) + abs(me2["c"][1] - gmap[second][1])
    if dist2 > 12 and len(free_wps_for(data["frame"], second, locked)) == 2:
        data, ok = sync_follow_path(
            sess, data, second, gmap[second], locked, lv0
        )
    if data.get("state") == "GAME_OVER":
        raise RuntimeError(f"GAME_OVER migrating ({label})")
    if (data.get("levels_completed") or 0) > lv0:
        return data, []

    owned = owned_map(data["frame"])
    owned[second] = free_wps_for(data["frame"], second, locked)
    print(f"  last-mile wps{second}", owned[second], "bud", step_budget(data["frame"]))
    data, owned, ok = park_compact(
        sess, data, second, gmap[second], owned, locked, lv0, budget=18, max_spread=18
    )
    print(f"  final park{second} ok={ok}", ships(data["frame"]))

    if (data.get("levels_completed") or 0) <= lv0:
        sh = ships(data["frame"])
        gmap = goals_by_chrome(data["frame"])
        dists = []
        for s in sh:
            gg = gmap.get(s["chrome"])
            if not gg:
                dists.append(("?", s["chrome"], s["c"]))
                continue
            dists.append(
                (
                    abs(s["c"][0] - gg[0]) + abs(s["c"][1] - gg[1]),
                    s["chrome"],
                    s["c"],
                )
            )
        raise RuntimeError(f"{label} clear failed; dists={dists} lv={data.get('levels_completed')} state={data.get('state')}")
    return data, []


def clear_l2(sess, data) -> tuple:
    return clear_dual(sess, data, label="L2")


def clear_l3(sess, data) -> tuple:
    return clear_dual(sess, data, label="L3")


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3clear"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    d = reset(sess)
    d, _ = clear_l1(sess, d)
    print("=== L2 ===")
    d, _ = clear_l2(sess, d)
    print("=== L3 ===")
    try:
        d, _ = clear_l3(sess, d)
        print("PASS levels", d.get("levels_completed"), d.get("state"))
        code = 0
    except Exception as e:
        print("FAIL", e)
        print("ships", ships(d["frame"]), "lv", d.get("levels_completed"), d.get("state"))
        code = 1
    sess.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
