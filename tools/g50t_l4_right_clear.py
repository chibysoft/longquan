"""g50t L4: persist36 → (40,22) → top to (52,10) → right-col down → west (10,52).

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

OUT = ROOT / "tests/fixtures/g50t_l4_clear_attempt.json"
FRAME = ROOT / "tests/fixtures/g50t_l4_rightcol_live.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]
TIP_A5 = [2, 2, 2, 4, 2, 5, 5]
TIP_LEAVE = [2, 2, 2, 4, 2, 1, 1]
# persist ends (34,22) with pending U (often noop into hole).
# Path: flush, R→(40,22), U→(40,16)/(40,10), R→(46,10)/(52,10), D×…, L→(10,52)
TO_RIGHT_CLEAR = [
    4, 4,  # flush+ R → ~ (40,22)
    1, 1,  # → (40,10)
    4, 4,  # → (52,10)
    2, 2, 2, 2, 2, 2, 2,  # down right col toward y52
    3, 3, 3, 3, 3, 3, 3,  # west along bottom
]


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
    path = []

    def reset():
        return s.post(
            f"{BASE}/api/cmd/RESET",
            headers=H(key, True),
            json={"card_id": card, "game_id": gid},
            timeout=30,
        ).json()

    def act(guid, aid):
        nact[0] += 1
        d = s.post(
            f"{BASE}/api/cmd/ACTION{aid}",
            headers=H(key, True),
            json={"game_id": gid, "guid": guid},
            timeout=30,
        ).json()
        if "guid" not in d:
            p("  FAIL", nact[0], {k: d.get(k) for k in d if k != "frame"})
        return d

    def play(guid, g, prev, seq, stop_lv=None, quiet=True):
        d = {"guid": guid}
        for a_ in seq:
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, False, True
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            pos = (prev["cx"], prev["cy"]) if prev else None
            if pos and (not path or path[-1] != pos):
                path.append(pos)
            if not quiet:
                p(" ", a_, pos, "e8", e8(g)["n"], "lv", d.get("levels_completed"), "n", nact[0])
            lv = d.get("levels_completed") or 0
            if stop_lv is not None and lv >= stop_lv:
                return guid, g, prev, d, True, False
            if lv > 3:
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
    path.clear()
    guid, g, prev, d, ok, dead = play(guid, g, prev, TIP_A5 + TIP_LEAVE, quiet=False)
    p("persist", e8(g)["n"] == 36, (prev["cx"], prev["cy"]), e8(g)["n"], "nact", nact[0])

    p("## right top clear")
    for a_ in TO_RIGHT_CLEAR:
        before = (prev["cx"], prev["cy"])
        d = act(guid, a_)
        if "guid" not in d:
            break
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        pos = (prev["cx"], prev["cy"])
        if not path or path[-1] != pos:
            path.append(pos)
        p(" ", a_, before, "->", pos, "e8", e8(g)["n"], "lv", d.get("levels_completed"), "n", nact[0])
        if (d.get("levels_completed") or 0) > 3:
            break

    # if reached bottom-ish but not clear, extra west/settle
    if (d.get("levels_completed") or 0) <= 3:
        for a_ in [3, 3, 3, 2, 1, 3, 2, 3, 1, 2]:
            before = (prev["cx"], prev["cy"])
            d = act(guid, a_)
            if "guid" not in d:
                break
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            pos = (prev["cx"], prev["cy"])
            p("  +", a_, before, "->", pos, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
            if (d.get("levels_completed") or 0) > 3:
                break

    FRAME.write_text(
        json.dumps({"frame": d.get("frame"), "pos": (prev["cx"], prev["cy"]), "e8": einfo(g), "path": path}, default=str),
        encoding="utf-8",
    )
    cleared = (d.get("levels_completed") or 0) > 3
    result = {
        "cleared": cleared,
        "levels_completed": d.get("levels_completed"),
        "final_pos": (prev["cx"], prev["cy"]),
        "final_e8": einfo(g),
        "path": path,
        "nact": nact[0],
        "reading": "L4_CLEAR" if cleared else "L4_RIGHTCOL_PARTIAL",
    }
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    p("READING", result["reading"], result["final_pos"], result["final_e8"], "path", path)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
