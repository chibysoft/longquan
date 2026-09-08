"""Steer L3 selected color-11 marker; try deliver onto ghosts / other markers."""
from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import m0r0
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.m0r0_l3_probe import act, clear_to_l2


def enter(sess):
    d = clear_to_l2(sess)
    if len(m0r0.locate_pieces(d["frame"])) == 1:
        d = act(sess, 4)
    return d


def c11_tl(frame):
    a = np.asarray(frame)
    g = a[0] if a.ndim == 3 else a
    ys, xs = np.where(g == 11)
    if len(xs) == 0:
        return None
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


def c1_list(frame):
    a = np.asarray(frame)
    g = a[0] if a.ndim == 3 else a
    vis = np.zeros_like(g, dtype=bool)
    out = []
    h, w = g.shape
    for y in range(h):
        for x in range(w):
            if g[y, x] != 1 or vis[y, x]:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and not vis[ny, nx] and g[ny, nx] == 1:
                        vis[ny, nx] = True
                        q.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            out.append((min(xs), min(ys), max(xs), max(ys)))
    return sorted(out)


def snap(d):
    g = np.asarray(d["frame"][0])
    return {
        "lv": d.get("levels_completed") or 0,
        "n9": int((g == 9).sum()),
        "n11": int((g == 11).sum()),
        "n1": int((g == 1).sum()),
        "n10": int((g == 10).sum()),
        "c11": c11_tl(d["frame"]),
        "c1": c1_list(d["frame"]),
    }


def steer_to(sess, d, tx, ty, limit=50):
    path = []
    for _ in range(limit):
        cur = c11_tl(d["frame"])
        if cur is None:
            return d, path, "lost"
        x0, y0 = cur[0], cur[1]
        if abs(x0 - tx) <= 1 and abs(y0 - ty) <= 1:
            return d, path, "ok"
        if y0 > ty:
            a = 1
        elif y0 < ty:
            a = 2
        elif x0 > tx:
            a = 3
        else:
            a = 4
        d = act(sess, a)
        path.append(a)
        nxt = c11_tl(d["frame"])
        if nxt == cur:
            moved = False
            for a2 in (1, 2, 3, 4):
                if a2 == a:
                    continue
                d = act(sess, a2)
                path.append(a2)
                if c11_tl(d["frame"]) != cur:
                    moved = True
                    break
            if not moved:
                return d, path, "stuck"
    return d, path, "limit"


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["m0r0_l3steer"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = sess.s.get(
        f"{BASE}/api/games/m0r0", headers=sess._headers(), timeout=60
    ).json()["game_id"]

    d = enter(sess)
    d = act(sess, 6, 31, 15)
    print("selected", snap(d))
    for aid in (1, 2, 3, 4):
        d = enter(sess)
        d = act(sess, 6, 31, 15)
        before = c11_tl(d["frame"])
        d = act(sess, aid)
        print(f"steer A{aid} {before} -> {c11_tl(d['frame'])}")

    d = enter(sess)
    d = act(sess, 6, 31, 15)
    ghosts = c1_list(d["frame"])
    print("ghosts", ghosts)

    for gbb in ghosts:
        d = enter(sess)
        d = act(sess, 6, 31, 15)
        d, path, st = steer_to(sess, d, gbb[0], gbb[1])
        print(f"steer to {gbb} status={st} pathlen={len(path)} final", snap(d))
        # overlap test
        cur = c11_tl(d["frame"])
        if cur and gbb:
            overlap = not (
                cur[2] < gbb[0] or gbb[2] < cur[0] or cur[3] < gbb[1] or gbb[3] < cur[1]
            )
            print("  overlap ghost?", overlap)

        for ca in (5, 6):
            d = enter(sess)
            d = act(sess, 6, 31, 15)
            d, _, st = steer_to(sess, d, gbb[0], gbb[1])
            cur = c11_tl(d["frame"])
            if cur:
                d2 = act(sess, ca, (cur[0] + cur[2]) // 2, (cur[1] + cur[3]) // 2)
                s = snap(d2)
                print(f"  A{ca} on c11", s)
                if s["lv"] >= 3 or s["n9"] == 0:
                    print("  CLEAR?")
            d = enter(sess)
            d = act(sess, 6, 31, 15)
            d, _, _ = steer_to(sess, d, gbb[0], gbb[1])
            d2 = act(sess, ca, (gbb[0] + gbb[2]) // 2, (gbb[1] + gbb[3]) // 2)
            s = snap(d2)
            print(f"  A{ca} on ghost", s)
            if s["lv"] >= 3 or (s["n10"] and s["n9"] < 8):
                print("  INTERESTING")

    # Steer onto other c9
    for tx, ty in ((11, 19), (39, 31)):
        d = enter(sess)
        d = act(sess, 6, 31, 15)
        d, path, st = steer_to(sess, d, tx, ty)
        print(f"steer to c9 {tx,ty} {st} len={len(path)}", snap(d))
        d2 = act(sess, 6, tx, ty)
        print("  A6", snap(d2))

    # Vertical range
    d = enter(sess)
    d = act(sess, 6, 31, 15)
    print("A2 chain:")
    for i in range(20):
        b = c11_tl(d["frame"])
        d = act(sess, 2)
        a = c11_tl(d["frame"])
        print(i, b, "->", a)
        if a == b:
            break
        if a and a[1] >= 44:
            print("near bottom", snap(d))
            # try drop on ghost
            for gbb in c1_list(d["frame"]):
                if abs(a[0] - gbb[0]) <= 4:
                    print("aligned x with ghost", gbb)
                    d2 = act(sess, 6, (a[0] + a[2]) // 2, (a[1] + a[3]) // 2)
                    print("A6", snap(d2))
                    d2 = act(sess, 5, (a[0] + a[2]) // 2, (a[1] + a[3]) // 2)
                    print("A5", snap(d2))
            break

    sess.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
