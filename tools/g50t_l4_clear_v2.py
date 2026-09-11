"""g50t L4 clear v2: persist36, left to y40, second tip / gap cross / right path.

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
FRAME36 = ROOT / "tests/fixtures/g50t_l4_persist36_frame.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]
TIP_A5 = [2, 2, 2, 4, 2, 5, 5]
TIP_LEAVE = [2, 2, 2, 4, 2, 1, 1]
# persist then topwest to x10 and down to y40
TO_1040 = TIP_A5 + TIP_LEAVE + [1, 3, 3, 3, 3, 2, 2, 2, 2]


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
        for a_ in seq:
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, False, True
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if not quiet:
                p(" ", a_, (prev["cx"], prev["cy"]) if prev else None, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
            lv = d.get("levels_completed") or 0
            if stop_lv is not None and lv >= stop_lv:
                return guid, g, prev, d, True, False
            if lv > 3:
                return guid, g, prev, d, True, False
        return guid, g, prev, d, False, False

    def enter_persist36():
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
        if not ok and not dead:
            guid, g, prev, d, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        guid, g, prev, d, ok, dead = play(guid, g, prev, TO_TIP2 + [5, 5])
        if (d.get("levels_completed") or 0) < 3 and not dead:
            guid, g, prev, d, ok, dead = play(guid, g, prev, TIP1_LEAVE)
            guid, g, prev, d, ok, dead = play(guid, g, prev, L3_WEST_CLEAR, stop_lv=3)
        d = act(guid, 4)
        guid, g, prev = d["guid"], plane(d), actor(plane(d), None)
        guid, g, prev, d, ok, dead = play(guid, g, prev, TIP_A5 + TIP_LEAVE, quiet=False)
        p("persist", (prev["cx"], prev["cy"]), e8(g)["n"], einfo(g), "nact", nact[0])
        return guid, g, prev, d, e8(g)["n"] == 36

    cleared = False

    # A: dump persist36 frame at (10,40), scan y46
    p("## dump@1040")
    guid, g, prev, d, ok = enter_persist36()
    if not ok:
        p("no persist")
        return
    guid, g, prev, d, ok, dead = play(guid, g, prev, [1, 3, 3, 3, 3, 2, 2, 2, 2], quiet=False)
    p("at", (prev["cx"], prev["cy"]), e8(g)["n"])
    FRAME36.write_text(
        json.dumps({"frame": d.get("frame"), "pos": (prev["cx"], prev["cy"]), "e8": einfo(g), "lv": d.get("levels_completed")}, default=str),
        encoding="utf-8",
    )
    g = plane(d)
    # scan y46 landings
    y46 = {}
    for x in range(4, 58, 6):
        sub = g[44:49, x - 2 : x + 3]
        y46[x] = {int(k): int(v) for k, v in zip(*np.unique(sub, return_counts=True))}
    p("  y46 landings", y46)

    # from (10,40) try R along then D / toward goal
    for a_ in [4, 4, 4, 2, 2, 3, 2, 4, 2, 3, 3, 1, 2]:
        before_e = e8(g)["n"]
        d = act(guid, a_)
        if "guid" not in d:
            break
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        p("  A", a_, (prev["cx"], prev["cy"]), "e8", e8(g)["n"], "de", e8(g)["n"] - before_e, "lv", d.get("levels_completed"))
        if (d.get("levels_completed") or 0) > 3:
            cleared = True
            break
        if e8(g)["n"] < 36:
            p("  *** shrink")

    if cleared:
        OUT.write_text(json.dumps({"cleared": True, "method": "persist36_gap", "nact": nact[0]}, indent=2), encoding="utf-8")
        p("READING L4_CLEAR")
        s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)
        return

    # B: second tip — from persist go to (16,28) or (22,28) via left then R on y28
    p("## second tip via y28")
    guid, g, prev, d, ok = enter_persist36()
    # to (10,28) then R onto snake
    guid, g, prev, d, ok, dead = play(
        guid, g, prev, [1, 3, 3, 3, 3, 2, 2, 2, 4, 4, 4, 5, 5, 4, 2, 5, 5], quiet=False
    )
    p("end B", (prev["cx"], prev["cy"]) if prev else None, e8(g)["n"] if prev else None, "lv", d.get("levels_completed"))
    if (d.get("levels_completed") or 0) > 3:
        cleared = True

    if not cleared:
        # C: after further shrink if any, try goal; also try A5 latch on second tip
        p("## C rightcol after persist")
        guid, g, prev, d, ok = enter_persist36()
        # east on y22 then down through c15 zone
        for a_ in [4, 4, 4, 2, 2, 2, 2, 2, 2, 3, 3, 2, 2, 3, 3, 3]:
            before_e = e8(g)["n"]
            d = act(guid, a_)
            if "guid" not in d:
                p("  fail", {k: d.get(k) for k in d if k != "frame"})
                break
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            p("  C", a_, (prev["cx"], prev["cy"]), "e8", e8(g)["n"], "de", e8(g)["n"] - before_e, "lv", d.get("levels_completed"))
            if (d.get("levels_completed") or 0) > 3:
                cleared = True
                break

    result = {
        "cleared": cleared,
        "levels_completed": d.get("levels_completed") if d else None,
        "final_pos": (prev["cx"], prev["cy"]) if prev else None,
        "final_e8": einfo(g) if prev else None,
        "nact": nact[0],
        "y46": y46 if "y46" in dir() else None,
        "reading": "L4_CLEAR" if cleared else "L4_GAP_PARTIAL",
    }
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    p("READING", result["reading"], result.get("final_pos"), result.get("final_e8"))
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
