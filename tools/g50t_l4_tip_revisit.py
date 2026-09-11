"""g50t L4: persist → reenter tip(c2) → leave toward left/bottom; watch e8/c15/y46/levels.

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

OUT = ROOT / "tests/fixtures/g50t_l4_tip_revisit.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]
TIP_A5 = [2, 2, 2, 4, 2, 5, 5]
TIP_LEAVE = [2, 2, 2, 4, 2, 1, 1]
TO_1040 = [3, 3, 1, 1, 3, 3, 3, 2, 2, 2, 2, 2, 2]


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
        d = {"guid": guid}
        for a_ in seq:
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, False, True
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if not quiet:
                p(" ", a_, (prev["cx"], prev["cy"]) if prev else None, "e8", e8(g)["n"], "c15", int((g == 15).sum()), "lv", d.get("levels_completed"))
            lv = d.get("levels_completed") or 0
            if stop_lv is not None and lv >= stop_lv:
                return guid, g, prev, d, True, False
            if lv > 3:
                return guid, g, prev, d, True, False
        return guid, g, prev, d, False, False

    def boot_persist():
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
        guid, g, prev, d, ok, dead = play(guid, g, prev, TIP_A5 + TIP_LEAVE, quiet=False)
        ok = e8(g)["n"] == 36
        p("persist", ok, (prev["cx"], prev["cy"]), einfo(g))
        return guid, g, prev, d, ok

    # After persist at (34,22): D onto tip, then leave U to top-west to (10,40) and try D past 40
    # Also: tip → U → east rightcol again after second tip visit
    guid, g, prev, d, ok = boot_persist()
    if not ok:
        return

    p("## revisit tip then left clear attempt")
    # D to tip, U leave, TO_1040-like, then spam D/R
    seq = [2, 2, 1, 1] + TO_1040 + [2, 2, 2, 2, 4, 2, 4, 2, 3, 2, 3, 2]
    for a_ in seq:
        be = e8(g)["n"]
        bc = int((g == 15).sum())
        before = (prev["cx"], prev["cy"])
        d = act(guid, a_)
        if "guid" not in d:
            break
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        pos = (prev["cx"], prev["cy"])
        p(" ", a_, before, "->", pos, "e8", e8(g)["n"], "de", e8(g)["n"] - be, "dc15", int((g == 15).sum()) - bc, "lv", d.get("levels_completed"))
        if (d.get("levels_completed") or 0) > 3:
            p("  *** CLEAR")
            break

    # Fresh: persist, tip revisit, A5 on tip again? skip — known unlock
    # Fresh: persist → rightcol → from (52,28) try U back then D with different phase
    if (d.get("levels_completed") or 0) <= 3:
        p("## persist rightcol second pass")
        guid, g, prev, d, ok = boot_persist()
        if ok:
            seq2 = [4, 4, 1, 1, 4, 4, 2, 2, 2, 2, 1, 2, 1, 2, 3, 2, 3, 2, 2, 2]
            for a_ in seq2:
                before = (prev["cx"], prev["cy"])
                d = act(guid, a_)
                if "guid" not in d:
                    break
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                p(" ", a_, before, "->", (prev["cx"], prev["cy"]), "e8", e8(g)["n"], "lv", d.get("levels_completed"))
                if (d.get("levels_completed") or 0) > 3:
                    p("  *** CLEAR")
                    break

    result = {
        "cleared": (d.get("levels_completed") or 0) > 3 if d else False,
        "final_pos": (prev["cx"], prev["cy"]) if prev else None,
        "final_e8": einfo(g) if g is not None else None,
        "lv": d.get("levels_completed") if d else None,
        "nact": nact[0],
    }
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    p("READING", result)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
