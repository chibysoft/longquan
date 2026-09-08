"""r11l L3: sync-follow chrome15 with fixed east offsets, then migrate chrome14."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import (
    clear_l2,
    free_wps_for,
    formation_migrate,
    move_wp,
    park_compact,
    step_budget,
    owned_map,
    goals_by_chrome,
    near_any,
)
from tools.r11l_l2_core import (
    clearance_path,
    centroid_path_ok,
    _plane,
)
from tools.r11l_l2_probe import ships
from tools.r11l_seated_clear import act6, clear_l1, reset

# East of ship; Chebyshev sep ≥6; survives full L3 chrome15 path.
OFFS15 = ((5, 0), (5, 6))


def sync_to(sess, data, locked, targets, label=""):
    """Move free wps onto absolute targets (assign by nearest)."""
    cur = free_wps_for(data["frame"], 15, locked)
    print(f"  sync_to {label} cur={cur} targets={targets} bud={step_budget(data['frame'])}")
    # greedy: farthest from its nearest target first
    for _ in range(len(targets) + 4):
        cur = free_wps_for(data["frame"], 15, locked)
        if len(cur) < len(targets):
            print("  lost wps", cur)
            return data, False
        # done?
        if all(
            min(abs(w[0] - t[0]) + abs(w[1] - t[1]) for t in targets) <= 2 for w in cur
        ):
            return data, True
        # pick wp farthest from nearest free target
        used = set()
        best = None
        for w in cur:
            opts = sorted(
                targets,
                key=lambda t: abs(t[0] - w[0]) + abs(t[1] - w[1]),
            )
            for t in opts:
                if t in used:
                    continue
                if any(
                    max(abs(t[0] - o[0]), abs(t[1] - o[1])) < 6
                    for o in cur
                    if o != w
                ):
                    continue
                if near_any(t, locked, cheb=6):
                    continue
                d = abs(t[0] - w[0]) + abs(t[1] - w[1])
                if d <= 2:
                    used.add(t)
                    break
                score = (-d, w, t)
                if best is None or score < best:
                    best = score
                break
        if best is None:
            print("  no sync_to move")
            return data, False
        _, wp, dest = best
        # if long, step halfway if needed
        g = _plane(data["frame"])
        trial = [dest if c == wp else c for c in cur]
        # rebuild trial properly
        trial = list(cur)
        wi = cur.index(wp)
        trial[wi] = dest
        if not centroid_path_ok(cur, trial, g, samples=14):
            # intermediate
            mid = (
                (wp[0] + dest[0]) // 2,
                (wp[1] + dest[1]) // 2,
            )
            if mid == wp or near_any(mid, [c for c in cur if c != wp], 5):
                print(f"  path_ok fail {wp}->{dest}")
                return data, False
            dest = mid
            trial[wi] = dest
            if not centroid_path_ok(cur, trial, g, samples=14):
                print(f"  path_ok fail mid {wp}->{dest}")
                return data, False
        data, newc, st = move_wp(sess, data, wp, dest, locked)
        print(
            f"    {wp}->{dest} {st}->{newc} "
            f"ships={[(s['c'], s['chrome']) for s in ships(data['frame'])]} "
            f"bud={step_budget(data['frame'])}"
        )
        if st == "dead":
            return data, False
        if st in ("noop", "forbidden", "lost", "near_locked", "occupied"):
            return data, False
        if (data.get("levels_completed") or 0) >= 3:
            return data, True
    return data, True


def park_chrome15_sync(sess, data, locked, lv0):
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    goal = goals_by_chrome(data["frame"])[15]
    fine = clearance_path(data["frame"], me["c"], goal, step=1)
    print(f"park15 sync from={me['c']} goal={goal} path_len={len(fine)}")
    if not fine:
        return data, False

    # Wave plan: reshape at start, then jump along coarse indices
    ship0 = fine[0]
    targets0 = [(ship0[0] + o[0], ship0[1] + o[1]) for o in OFFS15]
    data, ok = sync_to(sess, data, locked, targets0, "reshape")
    if not ok:
        return data, False
    if (data.get("levels_completed") or 0) > lv0:
        return data, True

    # coarse hops — fewer waves to save ACTION6 budget for chrome14
    idxs = list(range(22, len(fine), 22))
    if not idxs or idxs[-1] != len(fine) - 1:
        idxs.append(len(fine) - 1)
    for ii, j in enumerate(idxs):
        hop = fine[j]
        targets = [(hop[0] + o[0], hop[1] + o[1]) for o in OFFS15]
        data, ok = sync_to(sess, data, locked, targets, f"wave{ii}@{hop}")
        if not ok:
            return data, False
        if (data.get("levels_completed") or 0) > lv0:
            return data, True
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
        dist = abs(me["c"][0] - goal[0]) + abs(me["c"][1] - goal[1])
        print(f"  after wave ship={me['c']} dist={dist}")
        if dist <= 5:
            return data, True

    owned = {15: free_wps_for(data["frame"], 15, locked)}
    data, owned, ok = park_compact(
        sess, data, 15, goal, owned, locked, lv0, budget=10, max_spread=14
    )
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    dist = abs(me["c"][0] - goal[0]) + abs(me["c"][1] - goal[1])
    return data, dist <= 6


def clear_l3(sess, data):
    """L3: migrate chrome14 first (budget-heavy 4wp), then sync-park chrome15."""
    lv0 = data.get("levels_completed") or 0
    gmap = goals_by_chrome(data["frame"])
    owned = owned_map(data["frame"])
    print("L3 enter", ships(data["frame"]), gmap, owned)

    freeze15 = list(owned.get(15, []))
    print("freeze15", freeze15, "bud", step_budget(data["frame"]))

    data, ok = formation_migrate(
        sess, data, 14, gmap[14], freeze15, lv0, step=8
    )
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    dist14 = abs(me14["c"][0] - gmap[14][0]) + abs(me14["c"][1] - gmap[14][1])
    print(f"migrate14 ok={ok} ship={me14['c']} dist={dist14} bud={step_budget(data['frame'])}")
    if data.get("state") == "GAME_OVER":
        raise RuntimeError("GAME_OVER migrate14")
    if (data.get("levels_completed") or 0) > lv0:
        return data, []

    owned = owned_map(data["frame"])
    owned[14] = free_wps_for(data["frame"], 14, freeze15)
    data, owned, ok = park_compact(
        sess, data, 14, gmap[14], owned, freeze15, lv0, budget=12, max_spread=16
    )
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    dist14 = abs(me14["c"][0] - gmap[14][0]) + abs(me14["c"][1] - gmap[14][1])
    print(f"park14 ok={ok} ship={me14['c']} dist={dist14} bud={step_budget(data['frame'])}")
    if data.get("state") == "GAME_OVER":
        raise RuntimeError("GAME_OVER park14")
    if (data.get("levels_completed") or 0) > lv0:
        return data, []
    if dist14 > 6:
        raise RuntimeError(f"could not park chrome14 dist={dist14}")

    locked14 = [
        w["c"]
        for w in r11l.waypoints(data["frame"])
        if abs(w["c"][0] - me14["c"][0]) + abs(w["c"][1] - me14["c"][1]) <= 14
        and not near_any(w["c"], freeze15, cheb=3)
    ]
    print("locked14", locked14, "bud", step_budget(data["frame"]))

    data, ok = park_chrome15_sync(sess, data, locked14, lv0)
    print("park15", ok, ships(data["frame"]), "lv", data.get("levels_completed"))
    if data.get("state") == "GAME_OVER":
        raise RuntimeError("GAME_OVER park15")
    if (data.get("levels_completed") or 0) <= lv0:
        raise RuntimeError(
            f"L3 fail ships={ships(data['frame'])} lv={data.get('levels_completed')}"
        )
    return data, []


def sync_to_chrome(sess, data, chrome, locked, targets, label=""):
    """Like sync_to but for any chrome id."""
    cur = free_wps_for(data["frame"], chrome, locked)
    print(
        f"  sync_to {label} cur={cur} targets={targets[:6]} bud={step_budget(data['frame'])}"
    )
    for _ in range(len(targets) + 6):
        if step_budget(data["frame"]) < 6:
            return data, False
        cur = free_wps_for(data["frame"], chrome, locked)
        if len(cur) < 2:
            print("  lost wps", cur)
            return data, False
        if all(
            min(abs(w[0] - t[0]) + abs(w[1] - t[1]) for t in targets) <= 3 for w in cur
        ):
            return data, True
        best = None
        for w in cur:
            for t in sorted(targets, key=lambda t: abs(t[0] - w[0]) + abs(t[1] - w[1])):
                if any(max(abs(t[0] - o[0]), abs(t[1] - o[1])) < 6 for o in cur if o != w):
                    continue
                if near_any(t, locked, cheb=6):
                    continue
                d = abs(t[0] - w[0]) + abs(t[1] - w[1])
                if d <= 2:
                    continue
                score = (-d, w, t)
                if best is None or score < best:
                    best = score
                break
        if best is None:
            print("  no sync_to move")
            return data, False
        _, wp, dest = best
        g = _plane(data["frame"])
        trial = list(cur)
        wi = min(range(len(cur)), key=lambda i: abs(cur[i][0] - wp[0]) + abs(cur[i][1] - wp[1]))
        trial[wi] = dest
        if not centroid_path_ok(cur, trial, g, samples=12):
            mid = ((wp[0] + dest[0]) // 2, (wp[1] + dest[1]) // 2)
            if mid == wp:
                print(f"  path_ok fail {wp}->{dest}")
                return data, False
            dest = mid
            trial[wi] = dest
            if not centroid_path_ok(cur, trial, g, samples=12):
                print(f"  path_ok fail mid {wp}->{dest}")
                # skip this target
                continue
        data, newc, st = move_wp(sess, data, wp, dest, locked)
        print(
            f"    {wp}->{dest} {st}->{newc} "
            f"ships={[(s['c'], s['chrome']) for s in ships(data['frame'])]} "
            f"bud={step_budget(data['frame'])}"
        )
        if st == "dead":
            return data, False
        if st in ("noop", "forbidden", "lost", "near_locked", "occupied"):
            continue
        if (data.get("levels_completed") or 0) >= 3:
            return data, True
    return data, True


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3sync"]},
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
        print("PASS", d.get("levels_completed"), d.get("state"))
        code = 0
    except Exception as e:
        print("FAIL", e)
        print("ships", ships(d["frame"]), "lv", d.get("levels_completed"))
        code = 1
    sess.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
