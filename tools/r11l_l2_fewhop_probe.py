"""r11l L2: few long floor hops, sticky wps, stagger pads."""
from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_probe import assign_wps, floor_ok, footprint_bad, hollow_goals, plane, ships
from tools.r11l_seated_clear import act6, clear_l1, reset


def floor_path(frame, start, goal, step: int = 12):
    g = plane(frame)

    def ship_ok(x, y) -> bool:
        if not (0 <= x < 64 and 0 <= y < 64):
            return False
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < 64 and 0 <= ny < 64):
                    return False
                if int(g[ny, nx]) in (2, 10):
                    return False
        return True

    seeds = []
    if ship_ok(*start):
        seeds = [start]
    else:
        for rad in range(1, 8):
            for dy in range(-rad, rad + 1):
                for dx in range(-rad, rad + 1):
                    if max(abs(dx), abs(dy)) != rad:
                        continue
                    p = (start[0] + dx, start[1] + dy)
                    if ship_ok(*p):
                        seeds.append(p)
            if seeds:
                break
    if not seeds:
        return None
    # goal may sit in chrome diamond — accept near-goal cells that are ship_ok
    q = deque()
    prev = {}
    for s in seeds:
        q.append(s)
        prev[s] = None
    end = None
    while q:
        x, y = q.popleft()
        if abs(x - goal[0]) + abs(y - goal[1]) <= 3 and ship_ok(x, y):
            end = (x, y)
            break
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) in prev:
                continue
            if not ship_ok(nx, ny):
                continue
            prev[(nx, ny)] = (x, y)
            q.append((nx, ny))
    if end is None:
        return None
    path = []
    cur = end
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    coarse = [path[0]]
    for p in path[1:]:
        if abs(p[0] - coarse[-1][0]) + abs(p[1] - coarse[-1][1]) >= step:
            coarse.append(p)
    if coarse[-1] != path[-1]:
        coarse.append(path[-1])
    return coarse


def stagger(path, hop_i, n, g):
    """Pads near path[hop_i] only (do not drag wps backward along early path)."""
    out = []
    cx, cy = path[hop_i]
    # prefer the hop itself and recent path nodes within manhattan 8
    recent = []
    for j in range(hop_i, -1, -1):
        p = path[j]
        if abs(p[0] - cx) + abs(p[1] - cy) <= 8:
            recent.append(p)
        else:
            break
    for p in recent:
        if floor_ok(g, *p) and all(
            max(abs(p[0] - q[0]), abs(p[1] - q[1])) >= 5 for q in out
        ):
            out.append(p)
        if len(out) >= n:
            return out
    rad = 1
    while len(out) < n and rad <= 14:
        for dy in range(-rad, rad + 1):
            for dx in range(-rad, rad + 1):
                if max(abs(dx), abs(dy)) != rad:
                    continue
                p = (cx + dx, cy + dy)
                if not floor_ok(g, *p) or footprint_bad(g, *p) > 8:
                    continue
                if all(max(abs(p[0] - q[0]), abs(p[1] - q[1])) >= 5 for q in out):
                    out.append(p)
                    if len(out) >= n:
                        return out
        rad += 1
    return out


def move_wp(sess, data, wp_c, dest):
    wps = r11l.waypoints(data["frame"])
    live = min(wps, key=lambda w: abs(w["c"][0] - wp_c[0]) + abs(w["c"][1] - wp_c[1]))
    if not live["selected"]:
        data = act6(sess, *live["c"])
        if data.get("state") == "GAME_OVER":
            return data, wp_c, "dead"
    before = {w["c"] for w in r11l.waypoints(data["frame"])}
    for _ in range(2):
        data = act6(sess, *dest)
        if data.get("state") == "GAME_OVER":
            return data, wp_c, "dead"
    after = {w["c"] for w in r11l.waypoints(data["frame"])}
    appeared = after - before
    if appeared:
        newc = min(appeared, key=lambda c: abs(c[0] - dest[0]) + abs(c[1] - dest[1]))
        return data, newc, "moved"
    return data, wp_c, "noop"


def park(sess, data, chrome, goal, owned, lv0, step=12):
    me = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)
    path = floor_path(data["frame"], me["c"], goal, step=step)
    print(f"park{chrome} from {me['c']} path={path}")
    if not path:
        return data, owned, False
    for hi in range(1, len(path)):
        hop = path[hi]
        sub = path[: hi + 1]
        targets = stagger(sub, len(sub) - 1, len(owned[chrome]), plane(data["frame"]))
        print(f"  hop {hop} targets={targets}")
        order = sorted(
            range(len(owned[chrome])),
            key=lambda i: abs(owned[chrome][i][0] - hop[0])
            + abs(owned[chrome][i][1] - hop[1]),
            reverse=True,
        )
        for j, i in enumerate(order):
            dest = targets[min(j, max(0, len(targets) - 1))] if targets else hop
            wp = owned[chrome][i]
            data, newc, st = move_wp(sess, data, wp, dest)
            print(
                f"  {chrome} {wp}->{dest} {st}->{newc} "
                f"ships={[(s['c'], s['chrome']) for s in ships(data['frame'])]} "
                f"lv={data.get('levels_completed')} state={data.get('state')}"
            )
            if st == "dead":
                return data, owned, False
            owned[chrome][i] = newc
            if (data.get("levels_completed") or 0) > lv0:
                return data, owned, True
        me = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)
        dist = abs(me["c"][0] - goal[0]) + abs(me["c"][1] - goal[1])
        print(f"  {chrome} now {me['c']} dist={dist}")
        if dist <= 6:
            return data, owned, True
    return data, owned, False


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l2few"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"

    d = reset(sess)
    d, _ = clear_l1(sess, d)
    d = act6(sess, 32, 32)
    lv0 = d.get("levels_completed") or 0
    g15 = next(x for x in hollow_goals(d["frame"]) if x["chrome"] == 15)["c"]
    g12 = next(x for x in hollow_goals(d["frame"]) if x["chrome"] == 12)["c"]
    asg = assign_wps(d["frame"])
    owned = {s["chrome"]: [w["c"] for w in a] for s, a in asg[1]}
    print("owned", owned, "goals", g15, g12)

    d, owned, _ = park(sess, d, 15, g15, owned, lv0, step=16)
    if d.get("state") == "GAME_OVER":
        print("died 15")
        sess.close()
        return 1
    if (d.get("levels_completed") or 0) > lv0:
        print("CLEARED L2")
        sess.close()
        return 0

    d, owned, ok = park(sess, d, 12, g12, owned, lv0, step=12)
    print("FINAL", d.get("levels_completed"), d.get("state"), ships(d["frame"]), ok)
    sess.close()
    return 0 if (d.get("levels_completed") or 0) > lv0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
