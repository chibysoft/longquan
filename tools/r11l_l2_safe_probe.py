"""r11l L2: only execute wp moves whose resulting ship centroid stays on floor."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_fewhop_probe import floor_path, move_wp
from tools.r11l_l2_probe import assign_wps, floor_ok, hollow_goals, plane, ships
from tools.r11l_seated_clear import act6, clear_l1, reset


def centroid(wps):
    n = len(wps)
    return (sum(w[0] for w in wps) / n, sum(w[1] for w in wps) / n)


def centroid_safe(wps, g) -> bool:
    cx, cy = centroid(wps)
    x, y = int(round(cx)), int(round(cy))
    if not (0 <= x < 64 and 0 <= y < 64):
        return False
    # ship is 5x5 — wall/hazard in footprint = unsafe (chrome/floor/wp ok)
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < 64 and 0 <= ny < 64):
                return False
            if int(g[ny, nx]) in (2, 10):
                return False
    return True


def dest_candidates(frame, goal, path):
    g = plane(frame)
    cands = []
    # prefer path nodes + ring around goal
    pts = list(path or [])
    gx, gy = goal
    for rad in range(0, 10):
        for dy in range(-rad, rad + 1):
            for dx in range(-rad, rad + 1):
                if max(abs(dx), abs(dy)) != rad and rad > 0:
                    continue
                pts.append((gx + dx, gy + dy))
    seen = set()
    for p in pts:
        if p in seen:
            continue
        seen.add(p)
        if floor_ok(g, *p):
            cands.append(p)
    return cands


def improve_ship(sess, data, chrome, goal, owned, lv0, budget_moves=12):
    g = plane(data["frame"])
    me = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)
    path = floor_path(data["frame"], me["c"], goal, step=8) or []
    print(f"improve {chrome} ship={me['c']} path_len={len(path)} wps={owned[chrome]}")
    moves = 0
    while moves < budget_moves:
        me = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)
        dist = abs(me["c"][0] - goal[0]) + abs(me["c"][1] - goal[1])
        print(f"  dist={dist} ship={me['c']} wps={owned[chrome]}")
        if dist <= 6:
            return data, owned, True
        g = plane(data["frame"])
        cands = dest_candidates(data["frame"], goal, path)
        # also exclude current wp bboxes roughly by avoiding near other wps
        best = None  # (new_dist, wp_index, dest)
        cur_c = centroid(owned[chrome])
        cur_d = abs(cur_c[0] - goal[0]) + abs(cur_c[1] - goal[1])
        for i, wp in enumerate(owned[chrome]):
            for dest in cands:
                if max(abs(dest[0] - wp[0]), abs(dest[1] - wp[1])) < 1:
                    continue
                # separation from other wps
                if any(
                    max(abs(dest[0] - owned[chrome][j][0]), abs(dest[1] - owned[chrome][j][1])) < 5
                    for j in range(len(owned[chrome]))
                    if j != i
                ):
                    continue
                trial = list(owned[chrome])
                trial[i] = dest
                if not centroid_safe(trial, g):
                    continue
                nc = centroid(trial)
                nd = abs(nc[0] - goal[0]) + abs(nc[1] - goal[1])
                if nd + 0.5 < cur_d:
                    score = (nd, abs(dest[0] - goal[0]) + abs(dest[1] - goal[1]), i, dest)
                    if best is None or score < best:
                        best = score
        if best is None:
            print("  no safe improving move")
            return data, owned, dist <= 6
        _, __, i, dest = best
        wp = owned[chrome][i]
        data, newc, st = move_wp(sess, data, wp, dest)
        moves += 1
        print(
            f"  move#{moves} {wp}->{dest} {st}->{newc} "
            f"ships={[(s['c'], s['chrome']) for s in ships(data['frame'])]} "
            f"lv={data.get('levels_completed')} state={data.get('state')}"
        )
        if st == "dead":
            return data, owned, False
        if st == "noop":
            # blacklist? skip
            continue
        owned[chrome][i] = newc
        if (data.get("levels_completed") or 0) > lv0:
            return data, owned, True
    return data, owned, False


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l2safe"]},
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

    # nearest-first by current distance
    order = sorted(
        ships(d["frame"]),
        key=lambda s: abs(s["c"][0] - (g15 if s["chrome"] == 15 else g12)[0])
        + abs(s["c"][1] - (g15 if s["chrome"] == 15 else g12)[1]),
    )
    print("order", [(s["c"], s["chrome"]) for s in order])

    for s in order:
        goal = g15 if s["chrome"] == 15 else g12
        d, owned, ok = improve_ship(sess, d, s["chrome"], goal, owned, lv0)
        if d.get("state") == "GAME_OVER":
            print("GAME_OVER")
            sess.close()
            return 1
        if (d.get("levels_completed") or 0) > lv0:
            print("CLEARED L2")
            sess.close()
            return 0
        print(f"ship {s['chrome']} parked_ok={ok}")

    print("FINAL", d.get("levels_completed"), d.get("state"), ships(d["frame"]))
    sess.close()
    return 0 if (d.get("levels_completed") or 0) > lv0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
