"""g50t L4: from tip (34,28) after persist — try D (pierce?) and star dirs.

Also online BFS with live step probes from key nodes.
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

OUT = ROOT / "tests/fixtures/g50t_l4_star_bfs.json"
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
                p(" ", a_, (prev["cx"], prev["cy"]) if prev else None, "e8", e8(g)["n"], "c15", c15n(g))
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
        p("persist", ok, (prev["cx"], prev["cy"]), einfo(g), "c15", c15n(g), "nact", nact[0])
        return guid, g, prev, d, ok

    def flush_to(guid, g, prev, target, limit=12):
        """Nudge toward target with UDLR, return when at target or stuck."""
        for _ in range(limit):
            if prev and (prev["cx"], prev["cy"]) == target:
                return guid, g, prev, True
            x, y = prev["cx"], prev["cy"]
            tx, ty = target
            if abs(tx - x) >= abs(ty - y):
                a_ = 4 if tx > x else 3
            else:
                a_ = 2 if ty > y else 1
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, False
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        return guid, g, prev, prev and (prev["cx"], prev["cy"]) == target

    def star_from(label, start_seq, dirs=(1, 2, 3, 4)):
        """Boot persist, run start_seq to position, probe each dir twice, watch c15/e8/pos."""
        guid, g, prev, d, ok = boot_persist()
        if not ok:
            return None
        c0 = c15n(g)
        for a_ in start_seq:
            be = e8(g)["n"]
            bc = c15n(g)
            before = (prev["cx"], prev["cy"])
            d = act(guid, a_)
            if "guid" not in d:
                return None
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            rec = {
                "label": label,
                "a": a_,
                "from": before,
                "to": (prev["cx"], prev["cy"]),
                "e8": e8(g)["n"],
                "de": e8(g)["n"] - be,
                "c15": c15n(g),
                "dc15": c15n(g) - bc,
                "lv": d.get("levels_completed"),
            }
            log.append(rec)
            p(f"  {label}", a_, before, "->", rec["to"], "e8", rec["e8"], "c15", rec["c15"], "dc", rec["dc15"])
            if rec["dc15"] or rec["de"]:
                p("  *** CHANGE", einfo(g), "c15", c15n(g))
            if (d.get("levels_completed") or 0) > 3:
                p("  *** CLEAR")
                return {"cleared": True, "log": log}
        # star dirs
        for di in dirs:
            for rep in range(2):
                be = e8(g)["n"]
                bc = c15n(g)
                before = (prev["cx"], prev["cy"])
                d = act(guid, di)
                if "guid" not in d:
                    return None
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                rec = {
                    "label": f"{label}_star",
                    "a": di,
                    "from": before,
                    "to": (prev["cx"], prev["cy"]),
                    "e8": e8(g)["n"],
                    "de": e8(g)["n"] - be,
                    "c15": c15n(g),
                    "dc15": c15n(g) - bc,
                    "lv": d.get("levels_completed"),
                }
                log.append(rec)
                moved = before != rec["to"]
                if moved or rec["dc15"] or rec["de"]:
                    p(f"  star", di, before, "->", rec["to"], "mv", moved, "dc15", rec["dc15"], "de", rec["de"])
                if (d.get("levels_completed") or 0) > 3:
                    p("  *** CLEAR")
                    return {"cleared": True}
        return {"pos": (prev["cx"], prev["cy"]), "c15": c15n(g), "e8": einfo(g)}

    # A: back onto tip, try D (pierce south into c15?)
    p("## tip then D")
    r1 = star_from("tipD", [2, 2])  # flush + D onto tip

    # B: tip then D D
    p("## tip DD")
    r2 = star_from("tipDD", [2, 2, 2, 2])

    # C: to (40,22) star (maybe pierce east)
    p("## at4022 star")
    r3 = star_from("p4022", [4, 4])

    # D: to (10,40) then try weird dirs / A5 avoided
    p("## at1040 star")
    r4 = star_from("p1040", [3, 3, 1, 1, 3, 3, 3, 2, 2, 2, 2, 2, 2])

    result = {"r1": r1, "r2": r2, "r3": r3, "r4": r4, "log": log, "nact": nact[0]}
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    p("READING", {k: result[k] for k in ("r1", "r2", "r3", "r4", "nact")})
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
