"""g50t L3: exact (34,22) A5; pre-latch e8=92 right/bottom probes; tip-adjacent shrink.

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

OUT = ROOT / "tests/fixtures/g50t_l3_prelatch_hunt.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
# proven stop at (34,22) with pending LEFT
TO_3422 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 3]
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]


def p(*a, **k):
    print(*a, **k, flush=True)


def main():
    key = _api_key()
    s = requests.Session()
    card = s.post(
        f"{BASE}/api/scorecard/open", headers=H(key, True), json={"tags": ["g50t_recon"]}, timeout=30
    ).json()["card_id"]
    gid = s.get(f"{BASE}/api/games/g50t", headers=H(key), timeout=20).json()["game_id"]
    p("opened", gid)

    def reset():
        return s.post(
            f"{BASE}/api/cmd/RESET", headers=H(key, True), json={"card_id": card, "game_id": gid}, timeout=30
        ).json()

    def act(guid, aid):
        d = s.post(
            f"{BASE}/api/cmd/ACTION{aid}",
            headers=H(key, True),
            json={"game_id": gid, "guid": guid},
            timeout=30,
        ).json()
        if "guid" not in d:
            raise RuntimeError(str({k: d.get(k) for k in d if k != "frame"}))
        return d

    def enter_l3():
        d = reset()
        guid = d["guid"]
        g = plane(d)
        prev = None
        for a_ in L1_SEQ + [2] * 4 + [4] * 8:
            d = act(guid, a_)
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
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) >= 2:
                break
        d = act(guid, 3)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        return guid, g, prev, d

    def play(guid, g, prev, seq):
        log = []
        for a_ in seq:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            log.append(
                {
                    "a": a_,
                    "actor": prev,
                    "e8": e8(g)["n"],
                    "c11": int(np.sum(g == 11)),
                    "lv": d.get("levels_completed"),
                }
            )
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, log, True
        return guid, g, prev, d, log, False

    def flush(guid, g, prev, aid, n=2):
        for _ in range(n):
            d = act(guid, aid)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, True
        return guid, g, prev, d, False

    out = {"trials": {}, "cleared": False}
    cleared = False

    # A) exact (34,22) then A5 / L / R / settle
    p("## exact 3422")
    for name, tail in {
        "A5": [5, 5],
        "settle_L_A5": [3, 5, 5],
        "settle_R_A5": [4, 5, 5],
        "settle_D_A5": [2, 5, 5],
        "settle_U_A5": [1, 5, 5],
        "LLL": [3, 3, 3, 3, 3, 3],
        "RRR": [4, 4, 4, 4],
        "D_then_L": [2, 2, 3, 3, 3, 3],
    }.items():
        guid, g, prev, d = enter_l3()
        guid, g, prev, d, log, ok = play(guid, g, prev, TO_3422 + tail)
        path = []
        for r in log:
            if r["actor"]:
                t = (r["actor"]["cx"], r["actor"]["cy"])
                if not path or path[-1] != t:
                    path.append(t)
        p(f"  {name}", path[-4:], "e8", log[-1]["e8"], "c11", log[-1]["c11"], "lv", log[-1]["lv"], "final", prev)
        out["trials"][f"3422_{name}"] = {
            "path": path,
            "final": log[-1],
            "e8": log[-1]["e8"],
            "c11": log[-1]["c11"],
            "cleared": ok,
        }
        if ok:
            cleared = True
            CLEAR.write_text(
                json.dumps({"cleared": True, "method": f"3422_{name}", "log": log}, indent=2, default=str),
                encoding="utf-8",
            )
            break
        if log[-1]["e8"] < 76:
            p("  ** e8 drop", log[-1]["e8"])

    # B) pre-latch: top to x52 drop (e8=92)
    if not cleared:
        p("## prelatch right drop")
        guid, g, prev, d = enter_l3()
        guid, g, prev, d, _, _ = play(guid, g, prev, [1, 1, 1, 1] + [4] * 10)
        p("  at", prev, "e8", e8(g)["n"])
        steps = []
        for i in range(10):
            b = (prev["cx"], prev["cy"])
            e0 = e8(g)["n"]
            guid, g, prev, d, ok = flush(guid, g, prev, 2, 2)
            a = (prev["cx"], prev["cy"]) if prev else None
            steps.append({"from": b, "to": a, "e8": [e0, e8(g)["n"]]})
            p(f"  D{i}", b, a, e0, e8(g)["n"])
            if a == b or ok:
                break
            if e8(g)["n"] < 92:
                p("  ** shrink", a)
                break
        out["trials"]["prelatch_right"] = {"steps": steps, "final": prev, "e8": e8(g)["n"]}

    # C) pre-latch: go tip, HOLD, dump whether (22,28)/(16,34)/(10,28) centers open
    if not cleared:
        p("## hold tip center map vs leave")
        guid, g, prev, d = enter_l3()
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_3434 + [4, 4])
        hold = {y: {x: int(g[y, x]) for x in range(10, 55, 6)} for y in range(10, 55, 6)}
        p("  hold e8", e8(g)["n"], "y28", hold[28], "y34", hold[34])
        # leave L
        guid, g, prev, d, _ = flush(guid, g, prev, 3, 2)
        leave = {y: {x: int(g[y, x]) for x in range(10, 55, 6)} for y in range(10, 55, 6)}
        p("  leave e8", e8(g)["n"], "y28", leave[28], "y34", leave[34])
        # diffs
        diffs = []
        for y in range(10, 55, 6):
            for x in range(10, 55, 6):
                if hold[y][x] != leave[y][x]:
                    diffs.append(((x, y), hold[y][x], leave[y][x]))
        p("  hold vs leave diffs", diffs)
        out["trials"]["hold_vs_leave"] = {"hold_e8": 76, "leave_e8": e8(g)["n"], "diffs": diffs, "hold_y28": hold[28], "hold_y34": hold[34]}

    # D) latch persist then A5 exactly at (34,22) using TO_3422 from latch start
    if not cleared:
        p("## latch then exact 3422 A5")
        guid, g, prev, d = enter_l3()
        # latch
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        p("  latched e8", e8(g)["n"], "at", prev)
        guid, g, prev, d, log, ok = play(guid, g, prev, TO_3422 + [5, 5])
        p("  after", prev, "e8", e8(g)["n"], "c11", int(np.sum(g == 11)), "lv", d.get("levels_completed"))
        # where did we A5? find last pos before respawn
        path = [(r["actor"]["cx"], r["actor"]["cy"]) for r in log if r["actor"]]
        p("  path tail", path[-8:])
        out["trials"]["latch_3422_A5"] = {
            "path": path,
            "e8": e8(g)["n"],
            "c11": int(np.sum(g == 11)),
            "lv": d.get("levels_completed"),
            "cleared": ok,
        }
        if ok:
            cleared = True

    # E) after latch, stop 3422, try walk onto c11 east with single steps + check c11
    if not cleared:
        p("## latch pierce east along c11")
        guid, g, prev, d = enter_l3()
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_3422)
        p("  at", prev, "c11", int(np.sum(g == 11)), "under", g[20:25, 32:37] if prev else None)
        steps = []
        for i in range(8):
            b = (prev["cx"], prev["cy"])
            c0 = int(np.sum(g == 11))
            d = act(guid, 4)  # single R
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            a = (prev["cx"], prev["cy"]) if prev else None
            steps.append({"from": b, "to": a, "c11": [c0, int(np.sum(g == 11))], "e8": e8(g)["n"]})
            p(f"  R{i}", b, a, "c11", c0, int(np.sum(g == 11)))
            if a == b and i > 1:
                break
        out["trials"]["latch_c11_east"] = {"steps": steps, "final": prev}

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_PRELATCH_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
