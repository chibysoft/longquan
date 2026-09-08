"""r11l L2: move all of a ship's waypoints together along a floor BFS path."""
from __future__ import annotations

import sys
from collections import Counter, deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_probe import (
    assign_wps,
    floor_ok,
    footprint_bad,
    hollow_goals,
    plane,
    safe_pads,
    ships,
)
from tools.r11l_seated_clear import act6, clear_l1, reset


def ship_floor_path(frame, start, goal, step: int = 6):
    """Coarse waypoints on floor (no hazard/wall) from start toward goal."""
    g = plane(frame)
    # BFS on floor cells
    q = deque([start])
    prev = {start: None}
    while q:
        x, y = q.popleft()
        if abs(x - goal[0]) + abs(y - goal[1]) <= 2:
            # reconstruct
            path = []
            cur = (x, y)
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            path.reverse()
            # subsample every `step`
            out = [path[0]]
            for p in path[1:]:
                if abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) >= step:
                    out.append(p)
            if out[-1] != path[-1]:
                out.append(path[-1])
            return out
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) in prev:
                continue
            if not floor_ok(g, nx, ny):
                continue
            if footprint_bad(g, nx, ny) > 8:
                continue
            prev[(nx, ny)] = (x, y)
            q.append((nx, ny))
    return None


def move_wp(sess, data, wp_approx, dest):
    wps = r11l.waypoints(data["frame"])
    live = min(
        wps, key=lambda w: abs(w["c"][0] - wp_approx[0]) + abs(w["c"][1] - wp_approx[1])
    )
    if not live["selected"]:
        data = act6(sess, *live["c"])
        st = data.get("state")
        if st not in (None, "NOT_FINISHED"):
            return data, live["c"], True
    for _ in range(2):
        data = act6(sess, *dest)
        st = data.get("state")
        if st not in (None, "NOT_FINISHED"):
            return data, dest, True
    return data, dest, False


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l2bfs"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"

    d = reset(sess)
    d, _ = clear_l1(sess, d)
    d = act6(sess, 32, 32)
    lv0 = d.get("levels_completed") or 0
    print("settle", ships(d["frame"]), hollow_goals(d["frame"]))

    goal15 = next(x for x in hollow_goals(d["frame"]) if x["chrome"] == 15)
    goal12 = next(x for x in hollow_goals(d["frame"]) if x["chrome"] == 12)

    # Park chrome-15 ship (nearer)
    asg = assign_wps(d["frame"])
    wps15 = [w["c"] for s, a in asg[1] if s["chrome"] == 15 for w in a]
    pads = safe_pads(d["frame"], goal15["c"])
    dest = pads[0]
    for wp in wps15:
        d, _, dead = move_wp(sess, d, wp, dest)
        print("park15", wp, "->", dest, "ships", ships(d["frame"]), "state", d.get("state"))
        if dead or (d.get("levels_completed") or 0) > lv0:
            break
        pads = safe_pads(d["frame"], goal15["c"])
        dest = pads[0] if pads else dest
    me15 = next(s for s in ships(d["frame"]) if s["chrome"] == 15)
    print("15 at", me15["c"], "dist", abs(me15["c"][0] - goal15["c"][0]) + abs(me15["c"][1] - goal15["c"][1]))

    # BFS path for ship12
    me12 = next(s for s in ships(d["frame"]) if s["chrome"] == 12)
    finals = safe_pads(d["frame"], goal12["c"], margin=8)
    gdest = finals[0] if finals else goal12["c"]
    path = ship_floor_path(d["frame"], me12["c"], gdest, step=5)
    print("BFS path", path, "len", None if path is None else len(path))
    if path is None:
        # try alternate starts / goals
        for alt in safe_pads(d["frame"], me12["c"], margin=5)[:5]:
            path = ship_floor_path(d["frame"], alt, gdest, step=5)
            if path:
                print("alt path from", alt, "len", len(path))
                break
    if path is None:
        print("NO PATH")
        sess.close()
        return 1

    # Filter path nodes to footprint-ok pads
    g = plane(d["frame"])
    path2 = []
    for p in path:
        if footprint_bad(g, *p) <= 5 and floor_ok(g, *p):
            path2.append(p)
        else:
            # snap to nearest safe pad
            pads = safe_pads(d["frame"], p, margin=6)
            if pads:
                path2.append(pads[0])
    if path2[-1] != gdest and gdest not in path2:
        path2.append(gdest)
    print("path2", path2)

    for hi, hop in enumerate(path2[1:], 1):
        asg = assign_wps(d["frame"])
        if asg is None:
            print("assign fail")
            break
        wps12 = [w["c"] for s, a in asg[1] if s["chrome"] == 12 for w in a]
        print(f"--- hop {hi}/{len(path2)-1} -> {hop} wps12={wps12}")
        for wp in list(wps12):
            d, newc, dead = move_wp(sess, d, wp, hop)
            print(
                f"  wp {wp}->{hop} ships={[(s['c'], s['chrome']) for s in ships(d['frame'])]} "
                f"lv={d.get('levels_completed')} state={d.get('state')}"
            )
            if dead:
                print("DEAD/END", d)
                sess.close()
                return 1
            if (d.get("levels_completed") or 0) > lv0:
                print("CLEARED L2")
                sess.close()
                return 0
        me12 = next(s for s in ships(d["frame"]) if s["chrome"] == 12)
        dist = abs(me12["c"][0] - goal12["c"][0]) + abs(me12["c"][1] - goal12["c"][1])
        print("  ship12", me12["c"], "dist", dist)
        me15 = next(s for s in ships(d["frame"]) if s["chrome"] == 15)
        print(
            "  ship15",
            me15["c"],
            "dist15",
            abs(me15["c"][0] - goal15["c"][0]) + abs(me15["c"][1] - goal15["c"][1]),
        )

    print("FINAL", d.get("levels_completed"), d.get("state"), ships(d["frame"]))
    sess.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
