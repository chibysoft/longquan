"""m0r0 L3 clear probe: relocate markers via gap, then test piece interactions.

Seated so far:
  - A6 on c9 selects (c9→c11); pieces 10→1 ghosts
  - A1-4 steers c11 (step 4); A6 on ghost deposits c9 at park site
  - Gap x≈26-29 lets marker reach y≥47 if ghosts not blocking
  - c1 / c9 block marker; c9 blocks pieces (not in WALKABLE)

Usage:
  python tools/m0r0_l3_clear_probe.py
"""
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


def safe_act(sess, aid, x=None, y=None):
    d = act(sess, aid, x, y)
    if "frame" not in d:
        raise RuntimeError(f"no frame aid={aid} keys={list(d)}")
    return d


def blobs(frame, color: int):
    a = np.asarray(frame)
    g = a[0] if a.ndim == 3 else a
    vis = np.zeros_like(g, dtype=bool)
    out = []
    h, w = g.shape
    for y in range(h):
        for x in range(w):
            if g[y, x] != color or vis[y, x]:
                continue
            q = deque([(x, y)])
            vis[y, x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and not vis[ny, nx] and g[ny, nx] == color:
                        vis[ny, nx] = True
                        q.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            out.append((min(xs), min(ys), max(xs), max(ys)))
    return sorted(out)


def c11(frame):
    b = blobs(frame, 11)
    return b[0] if b else None


def restore(sess, d):
    g = np.asarray(d["frame"][0])
    ys, xs = np.where(g == 1)
    if len(xs) == 0:
        return d
    return safe_act(sess, 6, int(xs[0]), int(ys[0]))


def snap(d):
    g = np.asarray(d["frame"][0])
    return {
        "lv": d.get("levels_completed") or 0,
        "n9": int((g == 9).sum()),
        "n11": int((g == 11).sum()),
        "n1": int((g == 1).sum()),
        "n10": int((g == 10).sum()),
        "ms": blobs(d["frame"], 9),
        "pcs": m0r0.locate_pieces(d["frame"]),
        "c11": c11(d["frame"]),
    }


def clear_pieces_from_gap(sess, d):
    """Move twins so gap column x=26-29 is free for marker descent."""
    for a in (1, 1, 3, 3, 3, 3):
        d = safe_act(sess, a)
        pcs = m0r0.locate_pieces(d["frame"])
        if len(pcs) == 2 and not any(26 <= p[0] <= 29 for p in pcs):
            return d
    return d


def steer_to(sess, d, tx, ty, limit=35):
    for _ in range(limit):
        cur = c11(d["frame"])
        if cur is None:
            return d, False
        if cur[0] == tx and cur[1] == ty:
            return d, True
        order = []
        if cur[1] < ty:
            order.append(2)
        if cur[1] > ty:
            order.append(1)
        if cur[0] < tx:
            order.append(4)
        if cur[0] > tx:
            order.append(3)
        moved = False
        for a in order + [2, 4, 1, 3]:
            d2 = safe_act(sess, a)
            n = c11(d2["frame"])
            if n and n != cur:
                d = d2
                moved = True
                break
            d = d2
        if not moved:
            return d, False
    return d, False


def park_via_gap(sess, d, home, tx, ty):
    d = safe_act(sess, 6, home[0], home[1])
    if c11(d["frame"]) is None:
        return d, False
    d, ok = steer_to(sess, d, tx, ty)
    if c11(d["frame"]):
        d = restore(sess, d)
    return d, ok


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["m0r0_l3_clear"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = sess.s.get(
        f"{BASE}/api/games/m0r0", headers=sess._headers(), timeout=60
    ).json()["game_id"]

    d = enter(sess)
    d = clear_pieces_from_gap(sess, d)
    print("cleared gap", snap(d))

    # Park three markers on bottom pads that pieces can return to
    targets = [(27, 47), (27, 51), (23, 47)]
    homes = blobs(d["frame"], 9)
    for tgt in targets:
        homes = blobs(d["frame"], 9)
        # prefer not-yet-low markers
        cand = [h for h in homes if h[1] < 40] or homes
        home = min(cand, key=lambda b: (b[1], b[0]))
        d = clear_pieces_from_gap(sess, d) if any(26 <= p[0] <= 29 for p in m0r0.locate_pieces(d["frame"])) else d
        d, ok = park_via_gap(sess, d, home, tgt[0], tgt[1])
        print("park", home, "->", tgt, "ok", ok, snap(d))
        if (d.get("levels_completed") or 0) >= 3:
            print("LEVELS 3 after park")
            sess.close()
            return

    print("all parked", snap(d))

    # Walk pieces toward markers; watch levels / n9
    for i in range(40):
        pcs_before = m0r0.locate_pieces(d["frame"])
        ms = blobs(d["frame"], 9)
        aid = (1, 2, 3, 4)[i % 4]
        # bias: if markers below pieces, press 2 more
        if ms and pcs_before and min(m[1] for m in ms) > max(p[1] for p in pcs_before):
            aid = 2
        d = safe_act(sess, aid)
        s = snap(d)
        if i % 4 == 0 or s["lv"] >= 3:
            print("walk", i, "A", aid, s)
        if s["lv"] >= 3:
            print("CLEARED")
            break
        # detect piece covering former marker cells via n9 drop
        if s["n9"] < 12:
            print("n9 drop", s)

    # A5 / A6 on marker
    for aid in (5,):
        d = safe_act(sess, aid)
        print("A5", snap(d))
    ms = blobs(d["frame"], 9)
    if ms:
        d = safe_act(sess, 6, ms[0][0], ms[0][1])
        print("A6mark", snap(d))

    sess.close()
    print("done", snap(d) if "frame" in d else d)


if __name__ == "__main__":
    main()
