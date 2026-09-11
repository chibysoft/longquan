"""g50t L4: single boot — c15 hold-shrink @ (52,28) then deep pierce / grind / goal.

Key: (52,28) dc15=-10 on entry (hold-shrink analog of L3 c11).
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

OUT = ROOT / "tests/fixtures/g50t_l4_c15_hold.json"
FRAME = ROOT / "tests/fixtures/g50t_l4_c15_hold_frame.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]
TIP_A5 = [2, 2, 2, 4, 2, 5, 5]
TIP_LEAVE = [2, 2, 2, 4, 2, 1, 1]
TO_5228 = [4, 4, 1, 1, 4, 4, 2, 2, 2, 2, 2, 2]


def p(*a, **k):
    print(*a, **k, flush=True)


def einfo(g):
    e = dict(e8(g))
    ys, xs = np.where(g == 8)
    if len(xs):
        e.update(xmin=int(xs.min()), xmax=int(xs.max()), ymin=int(ys.min()), ymax=int(ys.max()))
    return e


def c15info(g):
    ys, xs = np.where(g == 15)
    if len(xs) == 0:
        return {"n": 0}
    return {"n": int(len(xs)), "xmin": int(xs.min()), "xmax": int(xs.max()), "ymin": int(ys.min()), "ymax": int(ys.max())}


def snap(label, g, prev, d):
    s = {
        "label": label,
        "pos": (prev["cx"], prev["cy"]) if prev else None,
        "e8": einfo(g),
        "c15": c15info(g),
        "lv": d.get("levels_completed") if d else None,
    }
    p("SNAP", label, s["pos"], "e8", s["e8"]["n"], "c15", s["c15"])
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
    log = []
    cleared = False

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
                p(" ", a_, (prev["cx"], prev["cy"]) if prev else None, "e8", e8(g)["n"], "c15", c15info(g)["n"])
            lv = d.get("levels_completed") or 0
            if stop_lv is not None and lv >= stop_lv:
                return guid, g, prev, d, True, False
            if lv > 3:
                return guid, g, prev, d, True, False
        return guid, g, prev, d, False, False

    def slog(label, guid, g, prev, seq):
        nonlocal cleared
        d = {"guid": guid}
        for a_ in seq:
            be = e8(g)["n"]
            bc = c15info(g)["n"]
            before = (prev["cx"], prev["cy"])
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            pos = (prev["cx"], prev["cy"])
            de = e8(g)["n"] - be
            dc = c15info(g)["n"] - bc
            rec = {"label": label, "a": a_, "from": before, "to": pos, "e8": e8(g)["n"], "de": de, "c15": c15info(g)["n"], "dc15": dc, "lv": d.get("levels_completed")}
            log.append(rec)
            if before != pos or de or dc:
                p(f"  {label}", a_, before, "->", pos, "e8", e8(g)["n"], "de", de, "c15", c15info(g)["n"], "dc", dc, "lv", d.get("levels_completed"))
            if de < 0:
                p("  *** E8 SHRINK", einfo(g))
            if dc:
                p("  *** C15", dc, c15info(g))
            if pos[1] >= 34 and pos[0] >= 46:
                snaps.append(snap(f"deep_{label}", g, prev, d))
                FRAME.write_text(json.dumps({"frame": d.get("frame"), "pos": pos, "e8": einfo(g), "c15": c15info(g)}, default=str), encoding="utf-8")
            if (d.get("levels_completed") or 0) > 3:
                cleared = True
                p("  *** CLEAR")
                return guid, g, prev, d
        return guid, g, prev, d

    # Single boot
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
    snaps.append(snap("persist", g, prev, d))

    # to (52,28)
    guid, g, prev, d = slog("to5228", guid, g, prev, TO_5228)
    snaps.append(snap("on5228", g, prev, d))

    if not cleared:
        # Phase 1: hold on (52,28), deep D while c15 shrunk
        p("## deep D from hold c15")
        guid, g, prev, d = slog("deepD", guid, g, prev, [2, 2, 2, 2, 2, 2, 2, 2, 2, 2])
        snaps.append(snap("after_deepD", g, prev, d))

    if not cleared:
        # Phase 2: buffer pierce D×2→L, D×2→R while holding
        p("## buffer pierce")
        # return to (52,28) if moved
        if (prev["cx"], prev["cy"]) != (52.0, 28.0):
            guid, g, prev, d = slog("back5228", guid, g, prev, [1, 1, 1, 4, 4, 2, 2, 2, 2, 2, 2])
        for name, seq in [("D2L", [2, 2, 3]), ("D2R", [2, 2, 4]), ("D3L", [2, 2, 2, 3]), ("L2D", [3, 3, 2])]:
            if cleared:
                break
            guid, g, prev, d = slog(name, guid, g, prev, seq)
            if (prev["cx"], prev["cy"])[1] >= 40:
                guid, g, prev, d = slog(f"{name}_w", guid, g, prev, [3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2])

    if not cleared:
        # Phase 3: leave (52,28) — c15 restore?
        p("## leave restore test")
        guid, g, prev, d = slog("leave", guid, g, prev, [1, 1, 3, 3])
        snaps.append(snap("after_leave", g, prev, d))
        # re-enter (52,28) — grind?
        guid, g, prev, d = slog("reenter", guid, g, prev, [4, 4, 2, 2, 2, 2, 2, 2])
        snaps.append(snap("reenter5228", g, prev, d))

    if not cleared:
        # Phase 4: from deepest point, west to (10,52)
        p("## west goal push")
        guid, g, prev, d = slog("west", guid, g, prev, [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2])

    if not cleared:
        # Phase 5: A5 @ (52,28) with c15 hold — armed tip2?
        p("## A5 on c15 hold")
        guid, g, prev, d = slog("a5c15", guid, g, prev, [4, 4, 2, 2, 2, 2, 2, 5, 5])
        snaps.append(snap("after_a5", g, prev, d))
        if e8(g)["n"] == 36:
            guid, g, prev, d = slog("post_a5", guid, g, prev, [2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2])

    result = {
        "cleared": cleared,
        "final_pos": (prev["cx"], prev["cy"]) if prev else None,
        "final_e8": einfo(g) if g is not None else None,
        "final_c15": c15info(g) if g is not None else None,
        "lv": d.get("levels_completed") if d else None,
        "nact": nact[0],
        "snaps": snaps,
        "c15_changes": [r for r in log if r.get("dc15", 0) != 0],
        "shrinks": [r for r in log if r.get("de", 0) < 0],
        "deep": [r for r in log if r.get("to", (0, 0))[1] >= 40],
        "log": log,
    }
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    p("READING", {k: result[k] for k in result if k not in ("log", "snaps")})
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
