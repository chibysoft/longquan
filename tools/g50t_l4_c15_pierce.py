"""g50t L4: persist36 → c15 pierce / bottom tip2 / armed chain.

Phases:
  A) buffer pierce from (52,28) D×n→L/R (L3-analog)
  B) rightcol deep to (52,52) + A5 tip2 hunt
  C) L3-order: tip2 A5 → tip1 leave → tip2 leave → goal push
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

OUT = ROOT / "tests/fixtures/g50t_l4_c15_pierce.json"
FRAME = ROOT / "tests/fixtures/g50t_l4_c15_pierce_frame.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]
TIP_A5 = [2, 2, 2, 4, 2, 5, 5]
TIP_LEAVE = [2, 2, 2, 4, 2, 1, 1]
TO_1040 = [3, 3, 1, 1, 3, 3, 3, 2, 2, 2, 2, 2, 2]
# (34,22) → top-east → (52,28)
TO_5228 = [4, 4, 1, 1, 4, 4, 2, 2, 2, 2, 2, 2]


def p(*a, **k):
    print(*a, **k, flush=True)


def einfo(g):
    e = dict(e8(g))
    ys, xs = np.where(g == 8)
    if len(xs):
        e.update(xmin=int(xs.min()), xmax=int(xs.max()), ymin=int(ys.min()), ymax=int(ys.max()))
    return e


def c15n(g):
    return int((g == 15).sum())


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
                p(" ", a_, (prev["cx"], prev["cy"]) if prev else None, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
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
        p("persist", ok, (prev["cx"], prev["cy"]), einfo(g), "nact", nact[0])
        return guid, g, prev, d, ok

    def slog(label, guid, g, prev, seq):
        nonlocal cleared
        d = {"guid": guid}
        for a_ in seq:
            be = e8(g)["n"]
            bc = c15n(g)
            before = (prev["cx"], prev["cy"])
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, True
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            pos = (prev["cx"], prev["cy"])
            de = e8(g)["n"] - be
            dc = c15n(g) - bc
            rec = {
                "label": label,
                "a": a_,
                "from": before,
                "to": pos,
                "e8": e8(g)["n"],
                "de": de,
                "c15": c15n(g),
                "dc15": dc,
                "lv": d.get("levels_completed"),
            }
            log.append(rec)
            moved = before != pos
            if moved or de or dc:
                p(f"  {label}", a_, before, "->", pos, "e8", e8(g)["n"], "de", de, "c15", c15n(g), "dc", dc, "lv", d.get("levels_completed"))
            if de < 0:
                p("  *** SHRINK", einfo(g))
            if dc:
                p("  *** C15 CHANGE", dc)
            if pos[1] >= 46 and pos[0] <= 40:
                p("  *** BELOW GAP", pos)
                FRAME.write_text(
                    json.dumps({"frame": d.get("frame"), "pos": pos, "e8": einfo(g), "label": label}, default=str),
                    encoding="utf-8",
                )
            if (d.get("levels_completed") or 0) > 3:
                p("  *** CLEAR")
                cleared = True
                return guid, g, prev, d, False
        return guid, g, prev, d, False

    pierce_seqs = [
        ("D2L", [2, 2, 3]),
        ("D2R", [2, 2, 4]),
        ("D3L", [2, 2, 2, 3]),
        ("D3R", [2, 2, 2, 4]),
        ("D4L", [2, 2, 2, 2, 3]),
        ("L2D", [3, 3, 2]),
        ("R2D", [4, 4, 2]),
        ("Ddeep", [2, 2, 2, 2, 2, 2, 2, 2]),
        ("DLmicro", [2, 3, 2, 3, 2, 3, 2, 3]),
    ]

    # Phase A: pierce attempts from (52,28)
    p("## A pierce from 5228")
    guid, g, prev, d, ok = boot_persist()
    if ok:
        guid, g, prev, d, dead = slog("to5228", guid, g, prev, TO_5228)
        p("at5228", (prev["cx"], prev["cy"]), einfo(g), "c15", c15n(g))
        for name, seq in pierce_seqs:
            if cleared:
                break
            p(f"  try {name}")
            guid, g, prev, d, dead = slog(name, guid, g, prev, seq)
            if (prev["cx"], prev["cy"])[1] >= 40:
                p("  *** DEEP", (prev["cx"], prev["cy"]))
                guid, g, prev, d, dead = slog(f"{name}_w", guid, g, prev, [3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2])
            # reset position for next pierce try
            if not cleared and name != pierce_seqs[-1][0]:
                guid, g, prev, d, ok = boot_persist()
                if ok:
                    guid, g, prev, d, dead = slog("re5228", guid, g, prev, TO_5228)

    # Phase B: deep rightcol + A5 at bottom cells
    if not cleared:
        p("## B bottom A5 hunt")
        guid, g, prev, d, ok = boot_persist()
        if ok:
            guid, g, prev, d, dead = slog(
                "Bdown",
                guid,
                g,
                prev,
                TO_5228 + [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 5, 5, 2, 2, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2],
            )

    # Phase C: L3-order armed chain — rightcol bottom A5, tip1 leave, bottom leave, goal
    if not cleared:
        p("## C armed chain")
        guid, g, prev, d, ok = boot_persist()
        if ok:
            # to (52,52) area: east+down
            guid, g, prev, d, dead = slog(
                "Cto",
                guid,
                g,
                prev,
                TO_5228 + [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
            )
            pos = (prev["cx"], prev["cy"])
            p("  bottom?", pos, einfo(g))
            # A5 at bottom (buffer queue)
            guid, g, prev, d, dead = slog("Carm", guid, g, prev, [5, 5])
            # back to tip1 via top
            guid, g, prev, d, dead = slog(
                "Ctip1",
                guid,
                g,
                prev,
                [1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 2, 2, 1, 1],
            )
            # tip1 leave (U U from 34,22)
            guid, g, prev, d, dead = slog("Cleave", guid, g, prev, [1, 1])
            p("  after tip1 leave", (prev["cx"], prev["cy"]), einfo(g))
            # back to bottom tip2, west leave
            guid, g, prev, d, dead = slog(
                "Cback",
                guid,
                g,
                prev,
                [4, 4, 1, 1, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3],
            )
            p("  after tip2 leave", (prev["cx"], prev["cy"]), einfo(g))
            # push goal west along bottom or left col down
            guid, g, prev, d, dead = slog(
                "Cgoal",
                guid,
                g,
                prev,
                [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2],
            )

    # Phase D: hold-shrink pierce — step tip without A5, pierce while shrunk
    if not cleared:
        p("## D hold-shrink pierce")
        guid, g, prev, d, ok = boot_persist()
        if ok:
            # re-step tip (hold 36), then east top route
            guid, g, prev, d, dead = slog(
                "Dhold",
                guid,
                g,
                prev,
                [2, 2, 4, 4, 1, 1, 4, 4, 2, 2, 2, 2, 2, 2, 2, 3, 3, 2, 2, 3, 3, 3, 3, 3, 2, 2, 2],
            )

    result = {
        "cleared": cleared,
        "final_pos": (prev["cx"], prev["cy"]) if prev else None,
        "final_e8": einfo(g) if g is not None else None,
        "final_c15": c15n(g) if g is not None else None,
        "lv": d.get("levels_completed") if d else None,
        "nact": nact[0],
        "shrinks": [r for r in log if r.get("de", 0) < 0],
        "c15_changes": [r for r in log if r.get("dc15", 0) != 0],
        "deep_moves": [r for r in log if r.get("to", (0, 0))[1] >= 40 and r.get("to", (0, 0))[0] >= 46],
        "log": log,
    }
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    p("READING", {k: result[k] for k in result if k not in ("log",)})
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
