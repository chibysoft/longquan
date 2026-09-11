"""g50t L4: buffer overshoot pierce into c15 interior + west entry.

Hold-shrink @ (52,28) opens c15 ymin 27→31; need buffer to land deeper.
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

OUT = ROOT / "tests/fixtures/g50t_l4_c15_buffer.json"
FRAME = ROOT / "tests/fixtures/g50t_l4_c15_buffer_frame.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]
TIP_A5 = [2, 2, 2, 4, 2, 5, 5]
TIP_LEAVE = [2, 2, 2, 4, 2, 1, 1]
TO_5222 = [4, 4, 1, 1, 4, 4, 2, 2, 2, 2, 2]


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
        return guid, g, prev, d, e8(g)["n"] == 36

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
            rec = {"label": label, "a": a_, "from": before, "to": pos, "e8": e8(g)["n"], "de": de, "c15": c15info(g), "dc15": dc, "lv": d.get("levels_completed")}
            log.append(rec)
            if before != pos or de or dc:
                p(f"  {label}", a_, before, "->", pos, "e8", e8(g)["n"], "c15", c15info(g)["n"], "dc", dc, "lv", d.get("levels_completed"))
            if pos[1] >= 34 or (pos[0] <= 40 and pos[1] >= 46):
                FRAME.write_text(json.dumps({"frame": d.get("frame"), "pos": pos, "e8": einfo(g), "c15": c15info(g), "label": label}, default=str), encoding="utf-8")
                p("  *** FRAME", pos, c15info(g))
            if (d.get("levels_completed") or 0) > 3:
                cleared = True
                p("  *** CLEAR")
                return guid, g, prev, d
        return guid, g, prev, d

    trials = [
        # A: buffer overshoot D from (52,22) — land (52,28) with pending D into (52,34)
        ("buf5222", TO_5222 + [2, 2, 2, 2, 2]),
        # B: hold (52,28) then buffer D×3→L
        ("holdD3L", TO_5222 + [2] + [2, 2, 2, 3]),
        # C: from (40,22) go E into c15 at y28 while holding prior shrink — approach from west
        ("westE", TO_5222[:2] + [3, 3, 3, 4, 4, 4, 2, 2, 4, 4, 4, 2, 2, 2]),
        # D: from (52,28) hold, go L along y28 into c15 body
        ("holdL", TO_5222 + [2] + [3, 3, 3, 3, 3, 2, 2, 2, 2, 2]),
        # E: top approach (52,10) extra D down through shrunk gate
        ("topdown", TO_5222 + [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]),
        # F: persist → (52,28) hold → U leave c15 restore → re-enter with different buffer
        ("grind", TO_5222 + [2, 1, 1, 2, 2, 2, 2, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2]),
    ]

    for name, seq in trials:
        if cleared:
            break
        p(f"## {name}")
        guid, g, prev, d, ok = boot_persist()
        if not ok:
            p("  no persist")
            continue
        p("  start", (prev["cx"], prev["cy"]), e8(g)["n"])
        guid, g, prev, d = slog(name, guid, g, prev, seq)
        p("  end", (prev["cx"], prev["cy"]), einfo(g), c15info(g))
        if (d.get("levels_completed") or 0) > 3:
            break

    result = {
        "cleared": cleared,
        "final_pos": (prev["cx"], prev["cy"]) if prev else None,
        "final_e8": einfo(g) if g is not None else None,
        "final_c15": c15info(g) if g is not None else None,
        "lv": d.get("levels_completed") if d else None,
        "nact": nact[0],
        "new_cells": list({tuple(r["to"]) for r in log if r.get("to", (0, 0))[1] >= 34}),
        "c15_changes": [r for r in log if r.get("dc15", 0) != 0],
        "log": log,
    }
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    p("READING", {k: result[k] for k in result if k != "log"})
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
