"""r11l L2: direct teleport wps to goal pads (verify each move)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_probe import assign_wps, hollow_goals, plane, safe_pads, ships
from tools.r11l_l2_pad_probe import distinct_pads
from tools.r11l_seated_clear import act6, clear_l1, reset


def move_wp_verify(sess, data, wp_c, dest):
    wps = r11l.waypoints(data["frame"])
    live = min(wps, key=lambda w: abs(w["c"][0] - wp_c[0]) + abs(w["c"][1] - wp_c[1]))
    print(f"  select nearest {live['c']} (want {wp_c}) selected={live['selected']}")
    if not live["selected"]:
        data = act6(sess, *live["c"])
        if data.get("state") == "GAME_OVER":
            return data, False, "game_over_select"
    before = [w["c"] for w in r11l.waypoints(data["frame"])]
    for i in range(2):
        data = act6(sess, *dest)
        if data.get("state") == "GAME_OVER":
            return data, False, "game_over_move"
    after = [w["c"] for w in r11l.waypoints(data["frame"])]
    # Did any wp appear near dest?
    near = any(abs(c[0] - dest[0]) + abs(c[1] - dest[1]) <= 2 for c in after)
    print(f"  before={before}")
    print(f"  after={after} near_dest={near} ships={ships(data['frame'])} lv={data.get('levels_completed')}")
    return data, near, "ok" if near else "no_move"


def park_ship(sess, data, chrome, goal_c, lv0):
    asg = assign_wps(data["frame"])
    wps = [w["c"] for s, a in asg[1] if s["chrome"] == chrome for w in a]
    pads = distinct_pads(data["frame"], goal_c, n=max(2, len(wps)), spread=10)
    # Prefer pads that are NOT the exact goal center if that failed before; offset ring
    print(f"park chrome={chrome} wps={wps} pads={pads} goal={goal_c}")
    # Use up to len(wps) pads
    pads = pads[: len(wps)]
    if len(pads) < len(wps):
        # fallback safe_pads
        pads = safe_pads(data["frame"], goal_c, margin=12)[: len(wps)]
    for wp, dest in zip(list(wps), pads):
        data, ok, why = move_wp_verify(sess, data, wp, dest)
        print(f"  result {why}")
        if data.get("state") == "GAME_OVER":
            return data, False
        if (data.get("levels_completed") or 0) > lv0:
            return data, True
        # refresh remaining
        asg = assign_wps(data["frame"])
        if asg:
            wps = [w["c"] for s, a in asg[1] if s["chrome"] == chrome for w in a]
    me = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)
    dist = abs(me["c"][0] - goal_c[0]) + abs(me["c"][1] - goal_c[1])
    print(f"park done ship={me['c']} dist={dist}")
    return data, dist <= 6


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l2direct"]},
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

    # Nearest first = chrome 15
    d, ok = park_ship(sess, d, 15, g15["c"], lv0)
    if d.get("state") == "GAME_OVER":
        print("died parking 15")
        sess.close()
        return 1
    if (d.get("levels_completed") or 0) > lv0:
        print("CLEARED while parking 15")
        sess.close()
        return 0
    if not ok:
        # force more moves on remaining far wps of 15
        print("15 not close enough, retry far wps")
        for _ in range(4):
            me = next(s for s in ships(d["frame"]) if s["chrome"] == 15)
            if abs(me["c"][0] - g15["c"][0]) + abs(me["c"][1] - g15["c"][1]) <= 6:
                break
            asg = assign_wps(d["frame"])
            wps = [w["c"] for s, a in asg[1] if s["chrome"] == 15 for w in a]
            far = max(wps, key=lambda c: abs(c[0] - g15["c"][0]) + abs(c[1] - g15["c"][1]))
            pads = distinct_pads(d["frame"], g15["c"], n=3, spread=10)
            # pick pad farthest from other wps
            dest = pads[0]
            d, ok2, why = move_wp_verify(sess, d, far, dest)
            print("retry15", why, ships(d["frame"]))
            if d.get("state") == "GAME_OVER":
                sess.close()
                return 1
            if (d.get("levels_completed") or 0) > lv0:
                print("CLEARED")
                sess.close()
                return 0

    me15 = next(s for s in ships(d["frame"]) if s["chrome"] == 15)
    print("15 status", me15, "dist", abs(me15["c"][0] - g15["c"][0]) + abs(me15["c"][1] - g15["c"][1]))

    # Direct park chrome 12 at goal
    d, ok = park_ship(sess, d, 12, g12["c"], lv0)
    print("12 park ok", ok, "lv", d.get("levels_completed"), "state", d.get("state"), ships(d["frame"]))
    if (d.get("levels_completed") or 0) > lv0:
        print("CLEARED L2")
        sess.close()
        return 0

    # If 12 close but no level, nudge 15 again
    for _ in range(6):
        sh = ships(d["frame"])
        gs = hollow_goals(d["frame"])
        todo = []
        for s in sh:
            g = next(x for x in gs if x["chrome"] == s["chrome"])
            dist = abs(s["c"][0] - g["c"][0]) + abs(s["c"][1] - g["c"][1])
            todo.append((dist, s, g))
        todo.sort(reverse=True)
        print("todo", [(t[1]["c"], t[0], t[1]["chrome"]) for t in todo])
        if todo[0][0] <= 6 and todo[1][0] <= 6:
            print("both close but no clear?")
            break
        dist, s, g = todo[0]
        asg = assign_wps(d["frame"])
        wps = [w["c"] for ss, a in asg[1] if ss["chrome"] == s["chrome"] for w in a]
        far = max(wps, key=lambda c: abs(c[0] - g["c"][0]) + abs(c[1] - g["c"][1]))
        pads = distinct_pads(d["frame"], g["c"], n=4, spread=10)
        d, ok2, why = move_wp_verify(sess, d, far, pads[0])
        print("nudge", why, "lv", d.get("levels_completed"), "state", d.get("state"))
        if d.get("state") == "GAME_OVER":
            break
        if (d.get("levels_completed") or 0) > lv0:
            print("CLEARED L2")
            sess.close()
            return 0

    print("FINAL", d.get("levels_completed"), d.get("state"), ships(d["frame"]))
    sess.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
