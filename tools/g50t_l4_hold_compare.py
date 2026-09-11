"""g50t L4: dump frame while standing on tip (hold e8=36) vs after leave persist.

Also try tip2 BEFORE latch: rightcol@52 then tip. tags=["g50t_recon"]
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

HOLD = ROOT / "tests/fixtures/g50t_l4_hold_tip_frame.json"
OUT = ROOT / "tests/fixtures/g50t_l4_hold_compare.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]
TIP_STEP = [2, 2, 2, 4, 2]  # land tip, no A5
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


def y46_row(g):
    return {int(v): int((g[44:49] == v).sum()) for v in np.unique(g[44:49])}


def c15_info(g):
    ys, xs = np.where(g == 15)
    if not len(xs):
        return None
    return {
        "n": int(len(xs)),
        "xmin": int(xs.min()),
        "xmax": int(xs.max()),
        "ymin": int(ys.min()),
        "ymax": int(ys.max()),
    }


def grid_line(g, y):
    cells = []
    for x in range(10, 58, 6):
        sub = g[max(0, y - 2) : y + 3, max(0, x - 2) : x + 3]
        n5 = int((sub == 5).sum())
        n15 = int((sub == 15).sum())
        cells.append(f"{x}:{n5:02d}/{n15:02d}")
    return " ".join(cells)


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
            if not quiet:
                p(" ", a_, (prev["cx"], prev["cy"]) if prev else None, "e8", e8(g)["n"])
            lv = d.get("levels_completed") or 0
            if stop_lv is not None and lv >= stop_lv:
                return guid, g, prev, d, True, False
            if lv > 3:
                return guid, g, prev, d, True, False
        return guid, g, prev, d, False, False

    def enter_l4():
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
        return guid, g, prev, d

    guid, g, prev, d = enter_l4()
    # stand on tip hold
    guid, g, prev, d, ok, dead = play(guid, g, prev, TIP_STEP + [2], quiet=False)  # extra settle
    p("HOLD", (prev["cx"], prev["cy"]), einfo(g))
    p("  y46", y46_row(g), "c15", c15_info(g))
    p("  y40", grid_line(g, 40))
    p("  y46g", grid_line(g, 46))
    p("  y52", grid_line(g, 52))
    HOLD.write_text(
        json.dumps({"frame": d.get("frame"), "pos": (prev["cx"], prev["cy"]), "e8": einfo(g)}, default=str),
        encoding="utf-8",
    )
    hold_snap = {"e8": einfo(g), "y46": y46_row(g), "c15": c15_info(g), "y40": grid_line(g, 40), "y46g": grid_line(g, 46), "y52": grid_line(g, 52)}

    # leave without A5 → recover
    guid, g, prev, d, ok, dead = play(guid, g, prev, [1, 1], quiet=False)
    p("LEAVE_NO_A5", (prev["cx"], prev["cy"]), einfo(g))

    # fresh: A5 latch leave persist compare
    guid, g, prev, d = enter_l4()
    guid, g, prev, d, ok, dead = play(guid, g, prev, TIP_A5 + TIP_LEAVE, quiet=False)
    p("PERSIST", (prev["cx"], prev["cy"]), einfo(g))
    p("  y46", y46_row(g), "c15", c15_info(g))
    p("  y40", grid_line(g, 40))
    p("  y46g", grid_line(g, 46))
    p("  y52", grid_line(g, 52))
    persist_snap = {"e8": einfo(g), "y46": y46_row(g), "c15": c15_info(g), "y40": grid_line(g, 40), "y46g": grid_line(g, 46), "y52": grid_line(g, 52)}

    # from persist go to (52,28) and try L into denser c15 with alternate offsets — use 3 then 2 micro
    # also try from (52,28) U back and re-approach
    seq = [4, 4, 1, 1, 4, 4, 2, 2, 2, 2]
    for a_ in seq:
        before = (prev["cx"], prev["cy"])
        d = act(guid, a_)
        if "guid" not in d:
            break
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        p(" ", a_, before, "->", (prev["cx"], prev["cy"]), "e8", e8(g)["n"])

    # at ~52,28 try: L, L, D, L, D with logging pixel under feet
    for a_ in [3, 2, 3, 2, 3, 2, 2, 3, 3, 2]:
        before = (prev["cx"], prev["cy"])
        d = act(guid, a_)
        if "guid" not in d:
            break
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        pos = (prev["cx"], prev["cy"])
        cx, cy = int(pos[0]), int(pos[1])
        foot = int(g[cy, cx]) if 0 <= cy < 64 and 0 <= cx < 64 else -1
        p("  dig", a_, before, "->", pos, "foot", foot, "lv", d.get("levels_completed"))
        if (d.get("levels_completed") or 0) > 3:
            p("  *** CLEAR")
            break

    result = {"hold": hold_snap, "persist": persist_snap, "final": (prev["cx"], prev["cy"]), "e8": einfo(g), "lv": d.get("levels_completed"), "nact": nact[0]}
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    p("READING", result)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
