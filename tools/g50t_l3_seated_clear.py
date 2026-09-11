"""g50t L3 seated clear (budget-aware): count acts; west-leave tip2; trim path.

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

OUT = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
# trimmed bottom: 8 D after top enough for 10→52
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]


def p(*a, **k):
    print(*a, **k, flush=True)


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
            p("  FAIL act", nact[0], {k: d.get(k) for k in d if k != "frame"})
            d["_nact"] = nact[0]
            return d
        return d

    def enter_l3():
        d = reset()
        nact[0] = 0
        guid = d["guid"]
        g = plane(d)
        prev = None
        for a_ in L1_SEQ + [2] * 4 + [4] * 8:
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, False
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) >= 1:
                break
        d = act(guid, 3)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        for a_ in TO_2840 + L2_ROUTE:
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, False
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) >= 2:
                break
        d = act(guid, 3)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        p("  entered L3 nact", nact[0], "pos", (prev["cx"], prev["cy"]) if prev else None)
        return guid, g, prev, d, True

    def play(guid, g, prev, seq):
        log = []
        for a_ in seq:
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, log, False, True  # dead
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            log.append((a_, (prev["cx"], prev["cy"]) if prev else None, e8(g)["n"], d.get("levels_completed")))
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, log, True, False
        return guid, g, prev, d, log, False, False

    guid, g, prev, d, ok = enter_l3()
    # tip1 latch
    guid, g, prev, d, log, cleared, dead = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
    if not cleared and not dead:
        guid, g, prev, d, log, cleared, dead = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
    p("tip1", e8(g)["n"], nact[0], (prev["cx"], prev["cy"]) if prev else None)
    if dead:
        return

    # tip2 A5
    guid, g, prev, d, log, cleared, dead = play(guid, g, prev, TO_TIP2 + [5, 5])
    p("tip2A5", e8(g)["n"], nact[0], (prev["cx"], prev["cy"]) if prev else None)
    if cleared:
        OUT.write_text(json.dumps({"cleared": True, "nact": nact[0]}, indent=2), encoding="utf-8")
        p("READING L3_CLEAR early")
        return
    if dead:
        return

    # tip1 releave
    guid, g, prev, d, log, cleared, dead = play(guid, g, prev, TIP1_LEAVE)
    p("releave", e8(g)["n"], nact[0])
    if dead:
        return

    # tip2 again — WEST leave directly for persist60
    # land tip2 pend U; L,L → (16,52) persist; L→ via U land (10,52) pend U; climb
    west_clear = TO_TIP2 + [
        3, 3,  # (16,52) e8=60
        1,  # (10,52) pend U
        1, 1, 1,  # (10,46/40/34)
        1,  # drain U at 34
        4,  # drain stay, pend R
        4,  # (16,34)
        1,  # (22,34) pend U
        1,  # (22,28)
        1,  # (22,22) CLEAR
    ]
    guid, g, prev, d, log, cleared, dead = play(guid, g, prev, west_clear)
    for a_, pos, en, lv in log[-15:]:
        p(" ", a_, pos, "e8", en, "lv", lv)
    p("end", (prev["cx"], prev["cy"]) if prev else None, "e8", e8(g)["n"] if g is not None and "guid" in d else None, "nact", nact[0], "cleared", cleared, "dead", dead)

    if cleared or (d.get("levels_completed") or 0) > 2:
        OUT.write_text(
            json.dumps(
                {
                    "cleared": True,
                    "levels_completed": d.get("levels_completed"),
                    "nact": nact[0],
                    "method": "persist60_west_clear",
                    "path_tail": log[-20:],
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        p("READING L3_CLEAR")
    else:
        OUT.write_text(
            json.dumps(
                {
                    "cleared": False,
                    "nact": nact[0],
                    "dead": dead,
                    "err": {k: d.get(k) for k in d if k != "frame"} if d else None,
                    "final": (prev["cx"], prev["cy"]) if prev else None,
                    "e8": e8(g)["n"] if prev else None,
                    "tail": log[-20:],
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        p("READING L3_PARTIAL")

    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
