"""r11l L2: park15 then migrate12; never touch parked wps; re-park if drift."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_fewhop_probe import floor_path, stagger
from tools.r11l_l2_probe import assign_wps, hollow_goals, plane, ships
from tools.r11l_l2_safe_probe import centroid_safe, improve_ship
from tools.r11l_seated_clear import act6, clear_l1, reset


def resync_owned12(frame, locked15):
    wps = r11l.waypoints(frame)
    out = []
    for w in wps:
        if any(abs(w["c"][0] - fx) + abs(w["c"][1] - fy) <= 2 for fx, fy in locked15):
            continue
        out.append(w["c"])
    return out


def move_wp_owned(sess, data, wp_c, dest, forbidden):
    """Move wp_c only if the selected live wp is not in forbidden set."""
    wps = r11l.waypoints(data["frame"])
    live = min(wps, key=lambda w: abs(w["c"][0] - wp_c[0]) + abs(w["c"][1] - wp_c[1]))
    for fx, fy in forbidden:
        if abs(live["c"][0] - fx) + abs(live["c"][1] - fy) <= 2:
            return data, wp_c, "forbidden"
    if abs(live["c"][0] - wp_c[0]) + abs(live["c"][1] - wp_c[1]) > 4:
        return data, wp_c, "lost"
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


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l2lock"]},
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
    print("owned", owned)

    d, owned, ok = improve_ship(sess, d, 15, g15, owned, lv0, budget_moves=8)
    print("15", ok, ships(d["frame"]), "wps15", owned[15])
    if d.get("state") == "GAME_OVER" or not ok:
        sess.close()
        return 1
    if (d.get("levels_completed") or 0) > lv0:
        print("CLEARED")
        sess.close()
        return 0

    locked15 = list(owned[15])
    # refresh 12 ownership from live assign, excluding locked
    asg = assign_wps(d["frame"])
    for s, a in asg[1]:
        if s["chrome"] == 12:
            owned[12] = [w["c"] for w in a]
    print("locked15", locked15, "owned12", owned[12])

    path = floor_path(d["frame"], next(s for s in ships(d["frame"]) if s["chrome"] == 12)["c"], g12, step=8)
    print("path12", path)
    if not path:
        sess.close()
        return 1

    blacklist = set()
    for hi in range(1, len(path)):
        hop = path[hi]
        # if 15 drifted, repark
        me15 = next(s for s in ships(d["frame"]) if s["chrome"] == 15)
        if abs(me15["c"][0] - g15[0]) + abs(me15["c"][1] - g15[1]) > 6:
            print("15 drifted", me15["c"], "repark")
            d, owned, ok = improve_ship(sess, d, 15, g15, owned, lv0, budget_moves=6)
            locked15 = list(owned[15])
            if d.get("state") == "GAME_OVER":
                sess.close()
                return 1
        targets = stagger(path, hi, len(owned[12]), plane(d["frame"]))
        print(f"hop {hop} targets={targets} wps12={owned[12]} locked={locked15}")
        for _round in range(len(owned[12]) + 1):
            moved_any = False
            order = sorted(
                range(len(owned[12])),
                key=lambda i: abs(owned[12][i][0] - hop[0]) + abs(owned[12][i][1] - hop[1]),
                reverse=True,
            )
            for i in order:
                wp = owned[12][i]
                if abs(wp[0] - hop[0]) + abs(wp[1] - hop[1]) <= 5:
                    continue
                g = plane(d["frame"])
                for dest in targets:
                    if (wp, dest) in blacklist:
                        continue
                    if any(
                        max(abs(dest[0] - owned[12][j][0]), abs(dest[1] - owned[12][j][1])) < 5
                        for j in range(len(owned[12]))
                        if j != i
                    ):
                        continue
                    trial = list(owned[12])
                    trial[i] = dest
                    if not centroid_safe(trial, g):
                        continue
                    d, newc, st = move_wp_owned(sess, d, wp, dest, locked15)
                    print(
                        f"  {wp}->{dest} {st}->{newc} "
                        f"ships={[(s['c'], s['chrome']) for s in ships(d['frame'])]} "
                        f"lv={d.get('levels_completed')} state={d.get('state')}"
                    )
                    if st == "dead":
                        sess.close()
                        return 1
                    if st in ("forbidden", "lost", "noop"):
                        blacklist.add((wp, dest))
                        continue
                    owned[12][i] = newc
                    owned[12] = resync_owned12(d["frame"], locked15)
                    moved_any = True
                    if (d.get("levels_completed") or 0) > lv0:
                        print("CLEARED L2")
                        sess.close()
                        return 0
                    break
                if moved_any:
                    break
            if not moved_any:
                # force resync and retry once
                owned[12] = resync_owned12(d["frame"], locked15)
                print("  resync", owned[12])
                if not owned[12]:
                    break
                # if still no move, leave hop
                break
        me12 = next(s for s in ships(d["frame"]) if s["chrome"] == 12)
        dist = abs(me12["c"][0] - g12[0]) + abs(me12["c"][1] - g12[1])
        print(f"  ship12={me12['c']} dist={dist} wps={owned[12]}")
        if dist <= 6:
            print("both close")
            break
        owned[12] = resync_owned12(d["frame"], locked15)

    print("FINAL", d.get("levels_completed"), d.get("state"), ships(d["frame"]))
    sess.close()
    return 0 if (d.get("levels_completed") or 0) > lv0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
