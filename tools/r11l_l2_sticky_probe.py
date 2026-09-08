"""r11l L2: sticky wp ownership + stagger pads along safe path."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_bfs_probe import ship_floor_path
from tools.r11l_l2_probe import assign_wps, floor_ok, footprint_bad, hollow_goals, plane, ships
from tools.r11l_seated_clear import act6, clear_l1, reset


def move_wp(sess, data, wp_c, dest):
    """Select wp_c and double-click dest. Returns (data, new_wp_c_or_old, status)."""
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
    disappeared = before - after
    if appeared:
        # moved wp is the new position (pick closest to dest)
        newc = min(appeared, key=lambda c: abs(c[0] - dest[0]) + abs(c[1] - dest[1]))
        return data, newc, "moved"
    if disappeared:
        # vanished into dest exactly matching an existing?
        near = [c for c in after if abs(c[0] - dest[0]) + abs(c[1] - dest[1]) <= 2]
        if near:
            return data, near[0], "moved"
    return data, wp_c, "noop"


def stagger_targets(path, hop_i, n, g):
    """n targets along path ending at path[hop_i], walking backward."""
    out = []
    idx = hop_i
    while len(out) < n and idx >= 0:
        p = path[idx]
        if floor_ok(g, *p) and footprint_bad(g, *p) <= 6:
            # ensure separation from already chosen
            if all(max(abs(p[0] - q[0]), abs(p[1] - q[1])) >= 5 for q in out):
                out.append(p)
        idx -= 1
    # if still short, spiral around path[hop_i]
    cx, cy = path[hop_i]
    rad = 1
    while len(out) < n and rad <= 12:
        for dy in range(-rad, rad + 1):
            for dx in range(-rad, rad + 1):
                if max(abs(dx), abs(dy)) != rad:
                    continue
                p = (cx + dx, cy + dy)
                if not floor_ok(g, *p) or footprint_bad(g, *p) > 6:
                    continue
                if all(max(abs(p[0] - q[0]), abs(p[1] - q[1])) >= 5 for q in out):
                    out.append(p)
                    if len(out) >= n:
                        break
            if len(out) >= n:
                break
        rad += 1
    return out


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l2sticky"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"

    d = reset(sess)
    d, _ = clear_l1(sess, d)
    d = act6(sess, 32, 32)
    lv0 = d.get("levels_completed") or 0
    g15 = next(x for x in hollow_goals(d["frame"]) if x["chrome"] == 15)
    g12 = next(x for x in hollow_goals(d["frame"]) if x["chrome"] == 12)
    asg = assign_wps(d["frame"])
    assert asg
    owned = {}
    for s, a in asg[1]:
        owned[s["chrome"]] = [w["c"] for w in a]
    print("owned", owned, "goals", g15["c"], g12["c"])

    # Park 15 with stagger near goal (2 wps)
    g = plane(d["frame"])
    # mini-path for 15: current ship -> goal
    me15 = next(s for s in ships(d["frame"]) if s["chrome"] == 15)
    path15 = ship_floor_path(d["frame"], me15["c"], g15["c"], step=4)
    if path15 is None:
        path15 = [me15["c"], g15["c"]]
    print("path15", path15)
    # just place both at end stagger
    targets = stagger_targets(path15, len(path15) - 1, len(owned[15]), g)
    print("15 targets", targets)
    for i, wp in enumerate(list(owned[15])):
        dest = targets[min(i, len(targets) - 1)]
        d, newc, st = move_wp(sess, d, wp, dest)
        print(f"15 {wp}->{dest} {st} new={newc} ships={ships(d['frame'])} lv={d.get('levels_completed')}")
        if st == "dead":
            sess.close()
            return 1
        owned[15][i] = newc
        if (d.get("levels_completed") or 0) > lv0:
            print("CLEARED")
            sess.close()
            return 0
    # if still far, move again to goal stagger
    me15 = next(s for s in ships(d["frame"]) if s["chrome"] == 15)
    print("15 after", me15, "dist", abs(me15["c"][0] - g15["c"][0]) + abs(me15["c"][1] - g15["c"][1]))
    if abs(me15["c"][0] - g15["c"][0]) + abs(me15["c"][1] - g15["c"][1]) > 6:
        targets = stagger_targets([g15["c"]], 0, len(owned[15]), plane(d["frame"]))
        # force pads around goal
        if len(targets) < len(owned[15]):
            targets = [g15["c"], (g15["c"][0] - 5, g15["c"][1])]
        for i, wp in enumerate(list(owned[15])):
            dest = targets[min(i, len(targets) - 1)]
            d, newc, st = move_wp(sess, d, wp, dest)
            print(f"15b {wp}->{dest} {st} new={newc} ships={ships(d['frame'])}")
            if st == "dead":
                sess.close()
                return 1
            owned[15][i] = newc
            if (d.get("levels_completed") or 0) > lv0:
                print("CLEARED")
                sess.close()
                return 0
    me15 = next(s for s in ships(d["frame"]) if s["chrome"] == 15)
    print("15 parked", me15, "dist", abs(me15["c"][0] - g15["c"][0]) + abs(me15["c"][1] - g15["c"][1]))

    # Path for 12
    me12 = next(s for s in ships(d["frame"]) if s["chrome"] == 12)
    path12 = ship_floor_path(d["frame"], me12["c"], g12["c"], step=3)
    if path12 is None:
        print("no path12")
        sess.close()
        return 1
    # coarse every 7
    coarse = [path12[0]]
    for p in path12[1:]:
        if abs(p[0] - coarse[-1][0]) + abs(p[1] - coarse[-1][1]) >= 7:
            coarse.append(p)
    if coarse[-1] != path12[-1]:
        coarse.append(path12[-1])
    print("coarse12", coarse, "n", len(coarse))

    for hi in range(1, len(coarse)):
        g = plane(d["frame"])
        # map coarse index onto full path index approx
        # build targets staggered on coarse[0..hi]
        sub = coarse[: hi + 1]
        targets = stagger_targets(sub, len(sub) - 1, len(owned[12]), g)
        print(f"--- hop {hi} -> {coarse[hi]} targets={targets} owned12={owned[12]}")
        if len(targets) < len(owned[12]):
            print("pad short", len(targets))
        for i, wp in enumerate(list(owned[12])):
            dest = targets[min(i, len(targets) - 1)]
            d, newc, st = move_wp(sess, d, wp, dest)
            print(
                f"  {wp}->{dest} {st} new={newc} "
                f"ships={[(s['c'], s['chrome']) for s in ships(d['frame'])]} "
                f"lv={d.get('levels_completed')} state={d.get('state')}"
            )
            if st == "dead":
                print("GAME_OVER")
                sess.close()
                return 1
            owned[12][i] = newc
            if (d.get("levels_completed") or 0) > lv0:
                print("CLEARED L2")
                sess.close()
                return 0
        me12 = next(s for s in ships(d["frame"]) if s["chrome"] == 12)
        me15 = next(s for s in ships(d["frame"]) if s["chrome"] == 15)
        print(
            f"  ship12={me12['c']} d12={abs(me12['c'][0]-g12['c'][0])+abs(me12['c'][1]-g12['c'][1])} "
            f"ship15={me15['c']} d15={abs(me15['c'][0]-g15['c'][0])+abs(me15['c'][1]-g15['c'][1])}"
        )

    print("FINAL", d.get("levels_completed"), d.get("state"), ships(d["frame"]))
    sess.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
