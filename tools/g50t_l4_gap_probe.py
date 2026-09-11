"""g50t L4: after persist36@(10,40), hunt 2nd shrink on y28 snake + right-col.

Short single-boot phases; retry RESET on GAME_NOT_STARTED.
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

OUT = ROOT / "tests/fixtures/g50t_l4_gap_probe.json"
FRAME = ROOT / "tests/fixtures/g50t_l4_y28_frame.json"
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
    nact = [0]
    log = []

    def new_game():
        return s.get(f"{BASE}/api/games/g50t", headers=H(key), timeout=20).json()["game_id"]

    gid = new_game()
    p("opened", gid)

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
        d = {"guid": guid, "levels_completed": 0}
        for a_ in seq:
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, False, True
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if not quiet:
                p(" ", a_, (prev["cx"], prev["cy"]) if prev else None, "e8", e8(g)["n"], "lv", d.get("levels_completed"), "n", nact[0])
            lv = d.get("levels_completed") or 0
            if stop_lv is not None and lv >= stop_lv:
                return guid, g, prev, d, True, False
            if lv > 3:
                return guid, g, prev, d, True, False
        return guid, g, prev, d, False, False

    def boot_to_1040():
        nonlocal gid
        for attempt in range(3):
            d = reset()
            if "guid" not in d:
                gid = new_game()
                p("reopen", gid)
                d = reset()
            nact[0] = 0
            guid = d["guid"]
            g = plane(d)
            prev = None
            guid, g, prev, d, ok, dead = play(guid, g, prev, L1_SEQ + [2] * 4 + [4] * 8, stop_lv=1)
            if dead or (d.get("levels_completed") or 0) < 1:
                p("L1 fail", attempt)
                continue
            d = act(guid, 3)
            if "guid" not in d:
                continue
            guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)
            guid, g, prev, d, ok, dead = play(guid, g, prev, TO_2840 + L2_ROUTE, stop_lv=2)
            if dead or (d.get("levels_completed") or 0) < 2:
                p("L2 fail", attempt)
                continue
            d = act(guid, 3)
            if "guid" not in d:
                continue
            guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)
            guid, g, prev, d, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
            if (d.get("levels_completed") or 0) < 3 and not dead:
                guid, g, prev, d, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
            if dead:
                continue
            guid, g, prev, d, ok, dead = play(guid, g, prev, TO_TIP2 + [5, 5])
            if (d.get("levels_completed") or 0) < 3 and not dead:
                guid, g, prev, d, ok, dead = play(guid, g, prev, TIP1_LEAVE)
                guid, g, prev, d, ok, dead = play(guid, g, prev, L3_WEST_CLEAR, stop_lv=3)
            if dead or (d.get("levels_completed") or 0) < 3:
                p("L3 fail", attempt, d.get("levels_completed"), "n", nact[0])
                continue
            d = act(guid, 4)
            if "guid" not in d:
                continue
            guid, g, prev = d["guid"], plane(d), actor(plane(d), None)
            guid, g, prev, d, ok, dead = play(guid, g, prev, TIP_A5 + TIP_LEAVE, quiet=False)
            if e8(g)["n"] != 36:
                p("persist fail", e8(g)["n"])
                continue
            guid, g, prev, d, ok, dead = play(guid, g, prev, TO_1040, quiet=False)
            pos = (prev["cx"], prev["cy"])
            p("at1040?", pos, e8(g)["n"], "nact", nact[0])
            return guid, g, prev, d, pos == (10.0, 40.0) or pos == (10, 40)
        return None, None, None, None, False

    def slog(label, guid, g, prev, seq):
        d = {"guid": guid}
        for a_ in seq:
            be = e8(g)["n"]
            before = (prev["cx"], prev["cy"])
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, True
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            pos = (prev["cx"], prev["cy"])
            de = e8(g)["n"] - be
            rec = {"label": label, "a": a_, "from": before, "to": pos, "e8": e8(g)["n"], "de": de, "lv": d.get("levels_completed")}
            if de:
                rec["einfo"] = einfo(g)
            log.append(rec)
            p(f"  {label}", a_, before, "->", pos, "e8", e8(g)["n"], "de", de, "lv", d.get("levels_completed"))
            if de < 0:
                p("  *** SHRINK", einfo(g))
            if (d.get("levels_completed") or 0) > 3:
                p("  *** CLEAR")
                return guid, g, prev, d, False
        return guid, g, prev, d, False

    guid, g, prev, d, ok = boot_to_1040()
    if not ok:
        OUT.write_text(json.dumps({"ok": False, "reason": "boot"}, indent=2), encoding="utf-8")
        p("READING boot fail")
        return

    # From (10,40): U to (10,28), R onto (16,28)/(22,28)/(28,28)
    # Buffer-aware: queue moves carefully
    p("## y28 east on snake")
    guid, g, prev, d, dead = slog(
        "y28",
        guid,
        g,
        prev,
        [
            1, 1,  # -> (10,28) ideally (buffer: may need extra)
            4,  # toward 16
            4,
            4,
            4,
            2,  # try stand / settle
            1,
            5,  # A5 if on tip2?
            5,
            1,
            3,
            2,
            2,
            2,
            2,
            2,
        ],
    )
    FRAME.write_text(
        json.dumps({"frame": d.get("frame") if d else None, "pos": (prev["cx"], prev["cy"]), "e8": einfo(g), "log": log}, default=str),
        encoding="utf-8",
    )

    cleared = (d.get("levels_completed") or 0) > 3 if d else False

    # If shrunk, dump and try push to y52
    if any(r.get("de", 0) < 0 for r in log) and not cleared:
        p("## post-shrink gap push")
        guid, g, prev, d, dead = slog("gap", guid, g, prev, [3, 3, 2, 2, 2, 2, 4, 4, 2, 3, 3, 2])

    # Fresh boot: right column via top from persist@ (34,22)
    if not cleared:
        p("## right-col boot")
        guid, g, prev, d, ok = boot_to_1040()
        if ok:
            # back to top then east — from (10,40) U to top R to 52 D
            guid, g, prev, d, dead = slog(
                "rc",
                guid,
                g,
                prev,
                [1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 2],
            )
            cleared = (d.get("levels_completed") or 0) > 3 if d else False

    result = {
        "cleared": cleared,
        "final_pos": (prev["cx"], prev["cy"]) if prev else None,
        "final_e8": einfo(g) if g is not None else None,
        "lv": d.get("levels_completed") if d else None,
        "nact": nact[0],
        "log": log,
    }
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    p("READING", {k: result[k] for k in result if k != "log"})
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
