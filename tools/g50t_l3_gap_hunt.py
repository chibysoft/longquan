"""g50t L3: after tip2-from-tip fail — crack right-col D block / c11 A5 / left gap.

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

OUT = ROOT / "tests/fixtures/g50t_l3_gap_hunt.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_5216 = [1] * 6 + [4] * 8 + [2, 2]  # from latch (34,34) → top → x52 → y16-ish


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

    def reset():
        return s.post(
            f"{BASE}/api/cmd/RESET",
            headers=H(key, True),
            json={"card_id": card, "game_id": gid},
            timeout=30,
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
            log.append({"a": a_, "actor": prev, "e8": e8(g)["n"], "c11": int(np.sum(g == 11)), "lv": d.get("levels_completed")})
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, log, True
        return guid, g, prev, d, log, False

    def latch(guid, g, prev):
        guid, g, prev, d, _, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if ok:
            return guid, g, prev, d, True
        guid, g, prev, d, _, ok = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        return guid, g, prev, d, ok

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

    # 1) right col: settle tricks then D
    p("## rightcol settle tricks")
    settle_plans = {
        "plain_D": [],
        "U_then_D": [1, 1],
        "L_then_D": [3, 3],
        "R_then_D": [4, 4],
        "LL_noop_D": [3, 3, 3, 3],
        "single_D_x8": None,  # special
    }
    for name, prep in settle_plans.items():
        if prep is None:
            continue
        guid, g, prev, d = enter_l3()
        guid, g, prev, d, _ = latch(guid, g, prev)
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_5216)
        # ensure near (52,16)
        for _ in range(4):
            if prev and prev["cx"] >= 50 and abs(prev["cy"] - 16) < 4:
                break
            guid, g, prev, d, _ = flush(guid, g, prev, 2 if prev and prev["cy"] < 16 else 4, 2)
        p(f"  {name} at", prev, "e8", e8(g)["n"])
        for a_ in prep:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        steps = []
        for i in range(8):
            b = (prev["cx"], prev["cy"]) if prev else None
            e0 = e8(g)["n"]
            guid, g, prev, d, ok = flush(guid, g, prev, 2, 2)
            a = (prev["cx"], prev["cy"]) if prev else None
            e1 = e8(g)["n"]
            steps.append({"i": i, "from": b, "to": a, "e8": [e0, e1], "lv": d.get("levels_completed")})
            p(f"  {name} D{i}", b, "->", a, "e8", e0, "->", e1)
            if ok or (d.get("levels_completed") or 0) > 2:
                cleared = True
                break
            if a == b:
                break
            if e1 < 76:
                p("  ** SHRINK", a, e1)
                break
        out["trials"][f"right_{name}"] = {"steps": steps, "final": prev, "e8": e8(g)["n"]}
        if cleared:
            break

    if not cleared:
        p("## rightcol single-step D")
        guid, g, prev, d = enter_l3()
        guid, g, prev, d, _ = latch(guid, g, prev)
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_5216)
        steps = []
        for i in range(12):
            b = (prev["cx"], prev["cy"]) if prev else None
            e0 = e8(g)["n"]
            d = act(guid, 2)  # single D
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            a = (prev["cx"], prev["cy"]) if prev else None
            e1 = e8(g)["n"]
            steps.append({"i": i, "from": b, "to": a, "e8": [e0, e1]})
            p(f"  sD{i}", b, "->", a, e0, e1)
            if a != b and a and a[1] > 18:
                p("  ** passed y16!")
            if a == b and i > 2:
                break
        out["trials"]["right_single_D"] = {"steps": steps, "final": prev}

    # 2) A5 at (34,22) after latch
    if not cleared:
        p("## A5 at 3422")
        guid, g, prev, d = enter_l3()
        guid, g, prev, d, _ = latch(guid, g, prev)
        guid, g, prev, d, log, ok = play(guid, g, prev, [1, 1, 1, 1, 1, 1])  # up toward 22
        p("  before A5", prev, "e8", e8(g)["n"], "c11", int(np.sum(g == 11)))
        # nudge to y22
        for _ in range(4):
            if prev and abs(prev["cy"] - 22) < 3:
                break
            aid = 1 if prev and prev["cy"] > 22 else 2
            guid, g, prev, d, _ = flush(guid, g, prev, aid, 2)
        p("  at", prev, "under", g[int(prev["cy"]) - 2 : int(prev["cy"]) + 3, int(prev["cx"]) - 2 : int(prev["cx"]) + 3] if prev else None)
        e0, c0 = e8(g)["n"], int(np.sum(g == 11))
        for a5 in (5, 5):
            d = act(guid, a5)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        p("  after A5", prev, "e8", e8(g)["n"], "c11", int(np.sum(g == 11)), "lv", d.get("levels_completed"))
        out["trials"]["a5_3422"] = {
            "e8": [e0, e8(g)["n"]],
            "c11": [c0, int(np.sum(g == 11))],
            "actor": prev,
            "lv": d.get("levels_completed"),
            "centers_y22": {x: int(g[22, x]) for x in range(10, 55, 6)},
            "centers_y28": {x: int(g[28, x]) for x in range(10, 55, 6)},
        }
        if (d.get("levels_completed") or 0) > 2:
            cleared = True

    # 3) from (34,28) try L / from (34,22) try L with singles
    if not cleared:
        p("## west probes from shaft")
        for start_seq, label in (
            ([1, 1], "from_3428"),
            ([1, 1, 1, 1], "from_3422"),
            ([1, 1, 1, 1, 3, 3, 3, 3], "from_3422_L"),
        ):
            guid, g, prev, d = enter_l3()
            guid, g, prev, d, _ = latch(guid, g, prev)
            guid, g, prev, d, _, _ = play(guid, g, prev, start_seq)
            p(f"  {label} at", prev, "e8", e8(g)["n"])
            path = [(prev["cx"], prev["cy"])] if prev else []
            for i in range(6):
                b = (prev["cx"], prev["cy"])
                e0 = e8(g)["n"]
                guid, g, prev, d, ok = flush(guid, g, prev, 3, 2)
                a = (prev["cx"], prev["cy"]) if prev else None
                p(f"  {label} L{i}", b, a, e0, e8(g)["n"])
                if a and a not in path:
                    path.append(a)
                if ok or (d.get("levels_completed") or 0) > 2:
                    cleared = True
                    break
                if a == b:
                    break
                if e8(g)["n"] < 76:
                    p("  ** shrink", a)
                    break
            out["trials"][label] = {"path": path, "e8": e8(g)["n"], "final": prev}

    # 4) left gap: from spawn after latch, D toward (10,28)
    if not cleared:
        p("## left gap from spawn")
        guid, g, prev, d = enter_l3()
        guid, g, prev, d, _ = latch(guid, g, prev)
        # back to spawn via top left
        guid, g, prev, d, _, _ = play(guid, g, prev, [1] * 6 + [3] * 10 + [2] * 4)
        p("  near spawn", prev)
        for aid, dn in ((2, "D"), (4, "R"), (3, "L")):
            guid2, g2, prev2 = guid, g, prev
            b = (prev2["cx"], prev2["cy"])
            guid2, g2, prev2, d2, ok = flush(guid2, g2, prev2, aid, 2)
            a = (prev2["cx"], prev2["cy"]) if prev2 else None
            p(f"  spawn-{dn}", b, a, "e8", e8(g2)["n"])
            if a != b and a and a[1] >= 28:
                p("  ** crossed y28!")
                guid, g, prev = guid2, g2, prev2
                # continue down / to (16,34)
                for i in range(8):
                    b = (prev["cx"], prev["cy"])
                    e0 = e8(g)["n"]
                    # prefer toward (16,34) or (22,34)
                    tx, ty = 16, 34
                    dx, dy = tx - prev["cx"], ty - prev["cy"]
                    aid2 = (4 if dx > 0 else 3) if abs(dx) >= abs(dy) else (2 if dy > 0 else 1)
                    guid, g, prev, d, ok = flush(guid, g, prev, aid2, 2)
                    a = (prev["cx"], prev["cy"]) if prev else None
                    p(f"  to1634", b, a, e8(g)["n"])
                    if e8(g)["n"] < 76:
                        p("  ** tip2?", a)
                        for a5 in (5, 5):
                            d = act(guid, a5)
                            guid = d["guid"]
                            g = plane(d)
                            prev = actor(g, prev)
                        p("  A5", prev, e8(g)["n"], d.get("levels_completed"))
                        if (d.get("levels_completed") or 0) > 2:
                            cleared = True
                        break
                    if a == b:
                        break
                break
        out["trials"]["left_gap"] = {"final": prev, "e8": e8(g)["n"]}

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_GAP_PARTIAL"
    if cleared:
        CLEAR.write_text(json.dumps({"cleared": True, "out": out}, indent=2, default=str), encoding="utf-8")
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
