"""g50t L4: after persist, watch color2 tip-markers / c15 / y46 while touring key cells.

tags=["g50t_recon"]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import deque

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import BASE, _api_key  # noqa: E402
from tools.g50t_l3_recon_probe import (  # noqa: E402
    L1_SEQ,
    TO_2840,
    L2_ROUTE,
    H,
    plane,
    actor,
    e8,
)

OUT = ROOT / "tests/fixtures/g50t_l4_marker_watch.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]
TIP_A5 = [2, 2, 2, 4, 2, 5, 5]
TIP_LEAVE = [2, 2, 2, 4, 2, 1, 1]


def p(*a, **k):
    print(*a, **k, flush=True)


def einfo(g):
    e = dict(e8(g))
    ys, xs = np.where(g == 8)
    if len(xs):
        e.update(xmin=int(xs.min()), xmax=int(xs.max()), ymin=int(ys.min()), ymax=int(ys.max()))
    return e


def comps(g, val):
    mask = g == val
    vis = np.zeros_like(mask)
    out = []
    for y in range(64):
        for x in range(64):
            if not mask[y, x] or vis[y, x]:
                continue
            q = deque([(y, x)])
            vis[y, x] = True
            pts = []
            while q:
                cy, cx = q.popleft()
                pts.append((cy, cx))
                for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < 64 and 0 <= nx < 64 and mask[ny, nx] and not vis[ny, nx]:
                        vis[ny, nx] = True
                        q.append((ny, nx))
            out.append(
                (
                    len(pts),
                    round(float(np.mean([p[1] for p in pts])), 1),
                    round(float(np.mean([p[0] for p in pts])), 1),
                )
            )
    return sorted(out, reverse=True)


def snap(label, g, prev, d):
    y46 = {int(v): int((g[44:49] == v).sum()) for v in np.unique(g[44:49])}
    s = {
        "label": label,
        "pos": (prev["cx"], prev["cy"]) if prev else None,
        "e8": einfo(g),
        "c2": comps(g, 2)[:6],
        "c15n": int((g == 15).sum()),
        "c9": comps(g, 9)[:6],
        "y46": y46,
        "lv": d.get("levels_completed") if d else None,
    }
    p("SNAP", label, "pos", s["pos"], "e8", s["e8"]["n"], "c2", s["c2"], "c15", s["c15n"], "y46", y46)
    return s


def main():
    key = _api_key()
    s = requests.Session()
    card = s.post(
        f"{BASE}/api/scorecard/open",
        headers=H(key, True),
        json={"tags": ["g50t_recon"]},
        timeout=30,
    ).json()["card_id"]
    gid = s.get(f"{BASE}/api/games/g50t", headers=H(key), timeout=20).json()["game_id"]
    p("opened", gid)
    nact = [0]
    snaps = []

    def reset():
        return s.post(
            f"{BASE}/api/cmd/RESET",
            headers=H(key, True),
            json={"card_id": card, "game_id": gid},
            timeout=30,
        ).json()

    def act(guid, aid):
        nact[0] += 1
        return s.post(
            f"{BASE}/api/cmd/ACTION{aid}",
            headers=H(key, True),
            json={"game_id": gid, "guid": guid},
            timeout=30,
        ).json()

    def play(guid, g, prev, seq, stop_lv=None, quiet=True):
        d = {"guid": guid}
        for a_ in seq:
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, False, True
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if not quiet:
                p(" ", a_, (prev["cx"], prev["cy"]) if prev else None, "e8", e8(g)["n"])
            lv = d.get("levels_completed") or 0
            if stop_lv is not None and lv >= stop_lv:
                return guid, g, prev, d, True, False
        return guid, g, prev, d, False, False

    d = reset()
    nact[0] = 0
    guid = d["guid"]
    g = plane(d)
    prev = None
    guid, g, prev, d, ok, dead = play(guid, g, prev, L1_SEQ + [2] * 4 + [4] * 8, stop_lv=1)
    d = act(guid, 3)
    guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)
    guid, g, prev, d, ok, dead = play(guid, g, prev, TO_2840 + L2_ROUTE, stop_lv=2)
    d = act(guid, 3)
    guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)
    guid, g, prev, d, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
    if (d.get("levels_completed") or 0) < 3 and not dead:
        guid, g, prev, d, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
    guid, g, prev, d, ok, dead = play(guid, g, prev, TO_TIP2 + [5, 5])
    if (d.get("levels_completed") or 0) < 3 and not dead:
        guid, g, prev, d, ok, dead = play(guid, g, prev, TIP1_LEAVE)
        guid, g, prev, d, ok, dead = play(guid, g, prev, L3_WEST_CLEAR, stop_lv=3)
    d = act(guid, 4)
    guid, g, prev = d["guid"], plane(d), actor(plane(d), None)
    snaps.append(snap("L4_spawn", g, prev, d))

    guid, g, prev, d, ok, dead = play(guid, g, prev, TIP_A5 + TIP_LEAVE, quiet=False)
    snaps.append(snap("persist", g, prev, d))

    tours = [
        ("to1040", [3, 3, 1, 1, 3, 3, 3, 2, 2, 2, 2, 2, 2]),
        ("to2840", [4, 4, 4, 4, 4, 4]),
        ("back_top_right", [1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 2, 2, 2]),
        ("to_tip", [1, 1, 1, 3, 3, 3, 2, 2]),
    ]
    for name, seq in tours:
        for a_ in seq:
            d = act(guid, a_)
            if "guid" not in d:
                break
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) > 3:
                snaps.append(snap("CLEAR", g, prev, d))
                break
        snaps.append(snap(name, g, prev, d))
        if (d.get("levels_completed") or 0) > 3:
            break

    OUT.write_text(json.dumps({"snaps": snaps, "nact": nact[0]}, indent=2, default=str), encoding="utf-8")
    p("READING", [{"l": s["label"], "pos": s["pos"], "c2": s["c2"], "c15": s["c15n"], "y46_5": s["y46"].get(5)} for s in snaps])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
