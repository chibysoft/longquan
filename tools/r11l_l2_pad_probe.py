"""r11l L2 probe: distinct pads per waypoint (no stack = no false select)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_bfs_probe import ship_floor_path
from tools.r11l_l2_probe import (
    assign_wps,
    footprint_bad,
    hollow_goals,
    plane,
    safe_pads,
    ships,
    floor_ok,
)
from tools.r11l_seated_clear import act6, clear_l1, reset
from longquan.interactive import r11l


def distinct_pads(frame, center, n: int, spread: int = 6):
    """n floor pads near center, pairwise Chebyshev distance >= 5."""
    g = plane(frame)
    raw = safe_pads(frame, center, margin=spread + 4)
    # also include center ring even if not in safe_pads ranking
    extras = []
    cx, cy = center
    for y in range(max(0, cy - spread), min(64, cy + spread + 1)):
        for x in range(max(0, cx - spread), min(64, cx + spread + 1)):
            if floor_ok(g, x, y) and footprint_bad(g, x, y) <= 5:
                extras.append((x, y))
    pool = []
    seen = set()
    for p in raw + extras + [center]:
        if p not in seen:
            seen.add(p)
            pool.append(p)
    chosen = []
    for p in pool:
        if all(max(abs(p[0] - q[0]), abs(p[1] - q[1])) >= 5 for q in chosen):
            chosen.append(p)
            if len(chosen) >= n:
                return chosen
    # relax to >= 4
    chosen = []
    for p in pool:
        if all(max(abs(p[0] - q[0]), abs(p[1] - q[1])) >= 4 for q in chosen):
            chosen.append(p)
            if len(chosen) >= n:
                return chosen
    return chosen


def move_wp(sess, data, wp_approx, dest):
    wps = r11l.waypoints(data["frame"])
    live = min(
        wps, key=lambda w: abs(w["c"][0] - wp_approx[0]) + abs(w["c"][1] - wp_approx[1])
    )
    if not live["selected"]:
        data = act6(sess, *live["c"])
        if data.get("state") == "GAME_OVER":
            return data, True
    before = {w["c"] for w in r11l.waypoints(data["frame"])}
    for _ in range(2):
        data = act6(sess, *dest)
        if data.get("state") == "GAME_OVER":
            return data, True
    after = {w["c"] for w in r11l.waypoints(data["frame"])}
    moved = before != after
    return data, not moved and data.get("state") == "GAME_OVER"


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l2pad"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"

    d = reset(sess)
    d, _ = clear_l1(sess, d)
    d = act6(sess, 32, 32)
    lv0 = d.get("levels_completed") or 0
    print("ships", ships(d["frame"]), "goals", hollow_goals(d["frame"]))

    goal15 = next(x for x in hollow_goals(d["frame"]) if x["chrome"] == 15)
    goal12 = next(x for x in hollow_goals(d["frame"]) if x["chrome"] == 12)
    asg = assign_wps(d["frame"])
    wps15 = [w["c"] for s, a in asg[1] if s["chrome"] == 15 for w in a]

    pads = distinct_pads(d["frame"], goal15["c"], n=len(wps15), spread=8)
    print("park15 pads", pads)
    for wp, dest in zip(wps15, pads):
        d, dead = move_wp(sess, d, wp, dest)
        me = next(s for s in ships(d["frame"]) if s["chrome"] == 15)
        print(" 15", wp, "->", dest, "ship", me["c"], "lv", d.get("levels_completed"), "state", d.get("state"))
        if dead or (d.get("levels_completed") or 0) > lv0:
            break
    me15 = next(s for s in ships(d["frame"]) if s["chrome"] == 15)
    print(
        "15 parked?",
        me15["c"],
        "dist",
        abs(me15["c"][0] - goal15["c"][0]) + abs(me15["c"][1] - goal15["c"][1]),
    )

    me12 = next(s for s in ships(d["frame"]) if s["chrome"] == 12)
    finals = safe_pads(d["frame"], goal12["c"], margin=8)
    gdest = finals[0]
    path = ship_floor_path(d["frame"], me12["c"], gdest, step=6)
    if path is None:
        for alt in safe_pads(d["frame"], me12["c"], margin=6)[:8]:
            path = ship_floor_path(d["frame"], alt, gdest, step=6)
            if path:
                break
    print("path", path)
    if not path:
        sess.close()
        return 1

    # coarsen path a bit more to save steps
    coarse = [path[0]]
    for p in path[1:]:
        if abs(p[0] - coarse[-1][0]) + abs(p[1] - coarse[-1][1]) >= 8:
            coarse.append(p)
    if coarse[-1] != path[-1]:
        coarse.append(path[-1])
    print("coarse", coarse)

    for hi, hop in enumerate(coarse[1:], 1):
        asg = assign_wps(d["frame"])
        wps12 = [w["c"] for s, a in asg[1] if s["chrome"] == 12 for w in a]
        pads = distinct_pads(d["frame"], hop, n=len(wps12), spread=8)
        print(f"hop {hi} center={hop} pads={pads} wps={wps12}")
        if len(pads) < len(wps12):
            print("not enough pads")
            pads = (pads + [hop] * len(wps12))[: len(wps12)]
        # match farthest wp to farthest pad? just zip sorted
        wps_sorted = sorted(wps12)
        pads_sorted = sorted(pads)
        for wp, dest in zip(wps_sorted, pads_sorted):
            before_w = [w["c"] for w in r11l.waypoints(d["frame"])]
            d, dead = move_wp(sess, d, wp, dest)
            after_w = [w["c"] for w in r11l.waypoints(d["frame"])]
            print(
                f"  {wp}->{dest} moved={before_w!=after_w} "
                f"ships={[(s['c'],s['chrome']) for s in ships(d['frame'])]} "
                f"lv={d.get('levels_completed')} state={d.get('state')}"
            )
            if dead or d.get("state") == "GAME_OVER":
                print("GAME_OVER")
                sess.close()
                return 1
            if (d.get("levels_completed") or 0) > lv0:
                print("CLEARED L2")
                sess.close()
                return 0
        me12 = next(s for s in ships(d["frame"]) if s["chrome"] == 12)
        dist = abs(me12["c"][0] - goal12["c"][0]) + abs(me12["c"][1] - goal12["c"][1])
        me15 = next(s for s in ships(d["frame"]) if s["chrome"] == 15)
        d15 = abs(me15["c"][0] - goal15["c"][0]) + abs(me15["c"][1] - goal15["c"][1])
        print(f"  now12={me12['c']} dist12={dist} 15={me15['c']} dist15={d15}")

    print("FINAL", d.get("levels_completed"), d.get("state"), ships(d["frame"]))
    sess.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
