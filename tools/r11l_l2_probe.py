"""Online probe: r11l L2 dual-ship chrome goals + hazard-aware hops."""
from __future__ import annotations

import sys
from collections import Counter, deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_seated_clear import act6, clear_l1, reset


def plane(frame):
    a = np.asarray(frame)
    return a[0] if a.ndim == 3 else a


def ships(frame):
    g = plane(frame)
    ys, xs = np.where(g == 6)
    out = []
    for x, y in zip(xs.tolist(), ys.tolist()):
        colors: Counter = Counter()
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                ny, nx = y + dy, x + dx
                if 0 <= ny < 64 and 0 <= nx < 64:
                    c = int(g[ny, nx])
                    if c not in (5, 6, 0, 1, 2, 10, 3):
                        colors[c] += 1
        chrome = colors.most_common(1)[0][0] if colors else 15
        out.append({"c": (x, y), "chrome": chrome})
    return out


def hollow_goals(frame):
    g = plane(frame)
    sh = ships(frame)
    ship_pts = [s["c"] for s in sh]
    goals = []
    for col in {s["chrome"] for s in sh}:
        pts = [
            (x, y)
            for y in range(64)
            for x in range(64)
            if g[y, x] == col
            and min(abs(x - sx) + abs(y - sy) for sx, sy in ship_pts) > 5
        ]
        unused = set(pts)
        while unused:
            seed = next(iter(unused))
            q = deque([seed])
            unused.remove(seed)
            cl = [seed]
            while q:
                cx, cy = q.popleft()
                for p in list(unused):
                    if abs(p[0] - cx) + abs(p[1] - cy) <= 3:
                        unused.remove(p)
                        q.append(p)
                        cl.append(p)
            if len(cl) >= 8:
                xs = [p[0] for p in cl]
                ys = [p[1] for p in cl]
                goals.append(
                    {
                        "c": (int(sum(xs) / len(xs)), int(sum(ys) / len(ys))),
                        "chrome": col,
                        "n": len(cl),
                        "bbox": (min(xs), min(ys), max(xs), max(ys)),
                    }
                )
    return goals


def assign_wps(frame):
    sh = ships(frame)
    wps = r11l.waypoints(frame)
    n = len(wps)
    if len(sh) != 2 or n < 2:
        return None
    best = None
    for mask in range(1, 2**n - 1):
        a = [wps[i] for i in range(n) if mask & (1 << i)]
        b = [wps[i] for i in range(n) if not mask & (1 << i)]
        if not a or not b:
            continue
        ca = (sum(w["c"][0] for w in a) / len(a), sum(w["c"][1] for w in a) / len(a))
        cb = (sum(w["c"][0] for w in b) / len(b), sum(w["c"][1] for w in b) / len(b))
        for s0, s1 in (sh, sh[::-1]):
            e = (
                abs(ca[0] - s0["c"][0])
                + abs(ca[1] - s0["c"][1])
                + abs(cb[0] - s1["c"][0])
                + abs(cb[1] - s1["c"][1])
            )
            if best is None or e < best[0]:
                best = (e, [(s0, a), (s1, b)])
    return best


def floor_ok(g, x, y):
    return 0 <= x < 64 and 0 <= y < 64 and int(g[y, x]) == 5


def footprint_bad(g, x, y) -> int:
    bad = 0
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < 64 and 0 <= ny < 64) or int(g[ny, nx]) in (2, 10):
                bad += 1
    return bad


def safe_pads(frame, goal, margin: int = 12):
    g = plane(frame)
    gx, gy = goal
    bbs = [w["bbox"] for w in r11l.waypoints(frame)]
    cands = []
    for y in range(max(0, gy - margin), min(64, gy + margin + 1)):
        for x in range(max(0, gx - margin), min(64, gx + margin + 1)):
            if not floor_ok(g, x, y):
                continue
            if any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in bbs):
                continue
            bad = footprint_bad(g, x, y)
            if bad > 3:
                continue
            cands.append((bad, abs(x - gx) + abs(y - gy), x, y))
    cands.sort()
    return [(x, y) for _, __, x, y in cands]


def move_wp_to(sess, data, wp_c, dest, label=""):
    wps = r11l.waypoints(data["frame"])
    live = min(wps, key=lambda w: abs(w["c"][0] - wp_c[0]) + abs(w["c"][1] - wp_c[1]))
    if not live["selected"]:
        data = act6(sess, *live["c"])
        print(f"  [{label}] select {live['c']} lv={data.get('levels_completed')}")
    before = ships(data["frame"])
    for _ in range(2):
        data = act6(sess, *dest)
    after = ships(data["frame"])
    print(
        f"  [{label}] ->{dest} "
        f"{[(s['c'], s['chrome']) for s in before]} => {[(s['c'], s['chrome']) for s in after]} "
        f"lv={data.get('levels_completed')}"
    )
    return data


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l2c"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"

    d = reset(sess)
    d, _ = clear_l1(sess, d)
    d = act6(sess, 32, 32)
    print("L2 ships", ships(d["frame"]))
    print("L2 goals", hollow_goals(d["frame"]))
    g = plane(d["frame"])
    pads = safe_pads(d["frame"], (40, 51), margin=14)
    print("pads near g12", pads[:8])
    print("cell(40,51)", int(g[51, 40]))

    # Left corridor floor samples
    for y in range(12, 56, 4):
        n = sum(1 for x in range(1, 22) if int(g[y, x]) == 5)
        print(f"y={y} left-floor={n}")

    goal15 = next(x for x in hollow_goals(d["frame"]) if x["chrome"] == 15)
    goal12 = next(x for x in hollow_goals(d["frame"]) if x["chrome"] == 12)
    asg = assign_wps(d["frame"])
    assert asg
    wps15 = [w for s, a in asg[1] if s["chrome"] == 15 for w in a]
    wps12 = [w for s, a in asg[1] if s["chrome"] == 12 for w in a]
    print("wps15", [w["c"] for w in wps15], "wps12", [w["c"] for w in wps12])

    lv0 = d.get("levels_completed") or 0
    pads15 = safe_pads(d["frame"], goal15["c"])
    dest15 = pads15[0] if pads15 else goal15["c"]
    for w in sorted(
        wps15,
        key=lambda w: abs(w["c"][0] - goal15["c"][0]) + abs(w["c"][1] - goal15["c"][1]),
        reverse=True,
    ):
        d = move_wp_to(sess, d, w["c"], dest15, "15")
        pads15 = safe_pads(d["frame"], goal15["c"])
        dest15 = pads15[0] if pads15 else goal15["c"]
        me = next(s for s in ships(d["frame"]) if s["chrome"] == 15)
        if abs(me["c"][0] - goal15["c"][0]) + abs(me["c"][1] - goal15["c"][1]) <= 6:
            print("15 parked", me["c"])
            break
        if (d.get("levels_completed") or 0) > lv0:
            print("LEVEL UP while parking 15")
            sess.close()
            return 0

    # Hand hops on left/bottom floor toward goal12
    hand = [(10, 28), (10, 40), (10, 50), (22, 52), (34, 52)]
    valid = []
    g = plane(d["frame"])
    for p in hand:
        bad = footprint_bad(g, *p) if floor_ok(g, *p) else 99
        print("hop", p, "cell", int(g[p[1], p[0]]) if 0 <= p[1] < 64 else None, "bad", bad)
        if bad <= 5:
            valid.append(p)
    finals = safe_pads(d["frame"], goal12["c"], margin=10)
    final = finals[0] if finals else (38, 50)
    print("valid hops", valid, "final", final, "finals", finals[:5])

    asg = assign_wps(d["frame"])
    wps12 = [w for s, a in asg[1] if s["chrome"] == 12 for w in a]
    for wi, w in enumerate(list(wps12)):
        chain = valid + [final]
        cur = w["c"]
        for dest in chain:
            d = move_wp_to(sess, d, cur, dest, f"12wp{wi}")
            sel = next((x for x in r11l.waypoints(d["frame"]) if x["selected"]), None)
            if sel:
                cur = sel["c"]
            me12 = next(s for s in ships(d["frame"]) if s["chrome"] == 12)
            dist = abs(me12["c"][0] - goal12["c"][0]) + abs(me12["c"][1] - goal12["c"][1])
            print("   ship12", me12["c"], "dist", dist)
            if (d.get("levels_completed") or 0) > lv0:
                print("LEVEL UP")
                print("DONE", d.get("levels_completed"), d.get("state"))
                sess.close()
                return 0
            # stop hopping this wp once near final
            if abs(cur[0] - final[0]) + abs(cur[1] - final[1]) <= 4:
                break

    print("FINAL", d.get("levels_completed"), d.get("state"), ships(d["frame"]))
    for s in ships(d["frame"]):
        gs = hollow_goals(d["frame"])
        gg = next((x for x in gs if x["chrome"] == s["chrome"]), None)
        dist = (
            abs(s["c"][0] - gg["c"][0]) + abs(s["c"][1] - gg["c"][1]) if gg else None
        )
        print(" ship", s, "goal", gg, "dist", dist)
    sess.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
