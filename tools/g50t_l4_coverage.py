"""g50t L4: single-session snake/coverage walk @ e8=52 — log any e8 drop.

tags=["g50t_recon"]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

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

OUT = ROOT / "tests/fixtures/g50t_l4_coverage.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]


def p(*a, **k):
    print(*a, **k, flush=True)


def einfo(g):
    e = dict(e8(g))
    ys, xs = np.where(g == 8)
    if len(xs):
        e.update(xmin=int(xs.min()), xmax=int(xs.max()), ymin=int(ys.min()), ymax=int(ys.max()))
    return e


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
    visited = []
    shrinks = []

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

    def play(guid, g, prev, seq, stop_lv=None):
        d = {"guid": guid}
        for a_ in seq:
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, False, True
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
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
    p("L4", (prev["cx"], prev["cy"]), einfo(g))

    # coverage route: top west, mid, tip approach, top east, rightcol, back
    # and systematic star at each stop
    route = (
        [3, 3, 3, 2, 1, 1, 4, 4, 4]  # wander top
        + [2, 2, 4, 2]  # toward tip
        + [1, 1, 4, 4, 1, 1, 4, 4, 2, 2, 2, 2]  # top right down
        + [1, 1, 1, 1, 3, 3, 3, 3, 2, 2, 3, 3, 2, 4, 4, 2]
        + [1, 3, 1, 3, 2, 4, 2, 4, 1, 4, 2, 3] * 3  # star-ish
    )

    for a_ in route:
        be = e8(g)["n"]
        before = (prev["cx"], prev["cy"])
        d = act(guid, a_)
        if "guid" not in d:
            p("FAIL", d)
            break
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        pos = (prev["cx"], prev["cy"])
        en = e8(g)["n"]
        if pos not in visited:
            visited.append(pos)
            p("  new", pos, "e8", en)
        if en < be:
            shrinks.append({"from": before, "to": pos, "e8": einfo(g), "a": a_})
            p("  *** SHRINK", before, "->", pos, einfo(g))
            # leave tip to recover and continue mapping
            for a2 in [1, 1]:
                d = act(guid, a2)
                if "guid" not in d:
                    break
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
            p("  recovered", (prev["cx"], prev["cy"]), e8(g)["n"])
        if (d.get("levels_completed") or 0) > 3:
            p("  *** CLEAR")
            break

    result = {"visited": visited, "shrinks": shrinks, "final": (prev["cx"], prev["cy"]), "e8": einfo(g), "nact": nact[0]}
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    p("READING", result)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
