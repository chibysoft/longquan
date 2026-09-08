"""r11l L2 probe: cluster-migrate along floor path with centroid safety."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_fewhop_probe import floor_path, move_wp, stagger
from tools.r11l_l2_probe import assign_wps, floor_ok, hollow_goals, plane, ships
from tools.r11l_l2_safe_probe import centroid, centroid_safe
from tools.r11l_seated_clear import act6, clear_l1, reset


def migrate(sess, data, chrome, goal, owned, lv0, step=10):
    me = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)
    path = floor_path(data["frame"], me["c"], goal, step=step)
    print(f"migrate {chrome} from {me['c']} path={path}")
    if not path:
        return data, owned, False
    blacklist = set()
    for hi in range(1, len(path)):
        hop = path[hi]
        sub = path[: hi + 1]
        g = plane(data["frame"])
        targets = stagger(sub, len(sub) - 1, len(owned[chrome]), g)
        print(f"  hop {hop} targets={targets} wps={owned[chrome]}")
        if not targets:
            continue
        # assign each wp to a target (farthest wp -> farthest target from hop? zip sorted)
        wps_idx = list(range(len(owned[chrome])))
        # move one at a time; re-evaluate safety
        progress = True
        rounds = 0
        while progress and rounds < len(owned[chrome]) + 2:
            progress = False
            rounds += 1
            g = plane(data["frame"])
            order = sorted(
                wps_idx,
                key=lambda i: abs(owned[chrome][i][0] - hop[0])
                + abs(owned[chrome][i][1] - hop[1]),
                reverse=True,
            )
            for i in order:
                wp = owned[chrome][i]
                # already near hop?
                if abs(wp[0] - hop[0]) + abs(wp[1] - hop[1]) <= 4:
                    continue
                for dest in targets:
                    key = (wp, dest)
                    if key in blacklist:
                        continue
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
                    # prefer dest closer to hop
                    data, newc, st = move_wp(sess, data, wp, dest)
                    print(
                        f"    {wp}->{dest} {st}->{newc} "
                        f"ships={[(s['c'], s['chrome']) for s in ships(data['frame'])]} "
                        f"lv={data.get('levels_completed')} state={data.get('state')}"
                    )
                    if st == "dead":
                        return data, owned, False
                    if st == "noop":
                        blacklist.add(key)
                        continue
                    owned[chrome][i] = newc
                    progress = True
                    if (data.get("levels_completed") or 0) > lv0:
                        return data, owned, True
                    break
                if progress:
                    break
        me = next(s for s in ships(data["frame"]) if s["chrome"] == chrome)
        dist = abs(me["c"][0] - goal[0]) + abs(me["c"][1] - goal[1])
        print(f"  after hop ship={me['c']} dist={dist}")
        if dist <= 6:
            return data, owned, True
    return data, owned, False


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l2mig"]},
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

    # park 15 with safe greedy (from safe_probe) — reuse migrate with large step
    from tools.r11l_l2_safe_probe import improve_ship

    d, owned, ok = improve_ship(sess, d, 15, g15, owned, lv0, budget_moves=8)
    print("15 ok", ok, ships(d["frame"]))
    if d.get("state") == "GAME_OVER":
        sess.close()
        return 1
    if (d.get("levels_completed") or 0) > lv0:
        print("CLEARED")
        sess.close()
        return 0

    d, owned, ok = migrate(sess, d, 12, g12, owned, lv0, step=6)
    print("FINAL", d.get("levels_completed"), d.get("state"), ships(d["frame"]), "ok", ok)
    sess.close()
    return 0 if (d.get("levels_completed") or 0) > lv0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
