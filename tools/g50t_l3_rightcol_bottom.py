"""g50t L3: after latch, step down right column x52; then bottom to (16,34) 2nd tip.

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

OUT = ROOT / "tests/fixtures/g50t_l3_rightcol_bottom.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]


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
        return guid, g, prev

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
                return guid, g, prev, log, True
        return guid, g, prev, log, False

    def latch(guid, g, prev):
        guid, g, prev, _, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if ok:
            return guid, g, prev, True
        guid, g, prev, _, ok = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        return guid, g, prev, ok

    def flush(guid, g, prev, aid, n=2):
        log = []
        for _ in range(n):
            d = act(guid, aid)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            log.append(prev)
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, log, True, d
        return guid, g, prev, log, False, d

    out = {}
    cleared = False

    p("## right column step-down")
    guid, g, prev = enter_l3()
    guid, g, prev, _ = latch(guid, g, prev)
    # to top then to x52: U*6 + R*8 from (34,34)
    guid, g, prev, _, ok = play(guid, g, prev, [1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4])
    p("  at", prev, "e8", e8(g)["n"])
    # settle R
    guid, g, prev, _, ok, d = flush(guid, g, prev, 4, 2)
    p("  settle", prev)

    steps = []
    for i in range(12):
        before = (prev["cx"], prev["cy"]) if prev else None
        e0 = e8(g)["n"]
        guid, g, prev, _, ok, d = flush(guid, g, prev, 2, 2)
        after = (prev["cx"], prev["cy"]) if prev else None
        e1 = e8(g)["n"]
        p(f"  D{i}", before, "->", after, "e8", e0, "->", e1, "lv", d.get("levels_completed"))
        steps.append({"i": i, "from": before, "to": after, "e8": [e0, e1], "lv": d.get("levels_completed")})
        if ok or (d.get("levels_completed") or 0) > 2:
            cleared = True
            break
        if after == before:
            p("  stuck down")
            break
        if e1 < 76:
            p("  ** second shrink!", after, e1)

    out["right_down"] = {"steps": steps, "final": prev, "e8": e8(g)["n"]}

    # If stuck at y16, try L then D (detour)
    if not cleared and prev and prev["cy"] <= 18:
        p("## detour L from stuck")
        for aid, name in ((3, "L"), (4, "R"), (1, "U")):
            guid2, g2, prev2 = guid, g, prev
            b = (prev2["cx"], prev2["cy"])
            guid2, g2, prev2, _, _, d = flush(guid2, g2, prev2, aid, 2)
            a = (prev2["cx"], prev2["cy"]) if prev2 else None
            p(f"  {name}", b, "->", a, "e8", e8(g2)["n"])
            if a != b:
                guid, g, prev = guid2, g2, prev2
                # try D again
                for i in range(8):
                    b = (prev["cx"], prev["cy"])
                    guid, g, prev, _, ok, d = flush(guid, g, prev, 2, 2)
                    a = (prev["cx"], prev["cy"]) if prev else None
                    p(f"  Dafter{name}{i}", b, "->", a, "e8", e8(g)["n"])
                    if a == b or ok:
                        break
                break

    # Fresh: try reach bottom via left after somehow
    # Path idea: latch -> tip (40,34) which is floor -> is D/R open to new cells?
    if not cleared:
        p("## from tip perimeter after latch")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch(guid, g, prev)
        guid, g, prev, _, _ = play(guid, g, prev, [4, 4])  # to tip
        p("  tip", prev, "e8", e8(g)["n"])
        # dump 5x5 neighborhood colors
        cx, cy = int(prev["cx"]), int(prev["cy"])
        patch = g[cy - 4 : cy + 5, cx - 4 : cx + 5]
        p("  patch\n", patch)
        for aid, name in ((1, "U"), (2, "D"), (3, "L"), (4, "R")):
            guid, g, prev = enter_l3()
            guid, g, prev, _ = latch(guid, g, prev)
            guid, g, prev, _, _ = play(guid, g, prev, [4, 4])
            b = (prev["cx"], prev["cy"], e8(g)["n"])
            guid, g, prev, _, _, d = flush(guid, g, prev, aid, 2)
            a = (prev["cx"], prev["cy"], e8(g)["n"]) if prev else None
            p(f"  tip-{name}", b, "->", a)
            if a and a[2] < 76:
                p("  ** SHRINK")
                # A5 latch second
                for a5 in (5, 5):
                    d = act(guid, a5)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                p("  A5", prev, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
                if (d.get("levels_completed") or 0) > 2:
                    cleared = True

    # Try (16,34) via: latch, top, left to x10, ... can't down past 22.
    # Alternative: from (40,34) after latch, R is blocked; what about going to (52,34)?
    # y34 has 52:5. From tip (40,34) R twice?
    if not cleared:
        p("## tip toward x52 along y34")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch(guid, g, prev)
        guid, g, prev, _, _ = play(guid, g, prev, [4, 4])  # tip
        for i in range(6):
            b = (prev["cx"], prev["cy"])
            e0 = e8(g)["n"]
            guid, g, prev, _, ok, d = flush(guid, g, prev, 4, 2)
            a = (prev["cx"], prev["cy"]) if prev else None
            p(f"  R{i}", b, "->", a, "e8", e0, "->", e8(g)["n"])
            if a == b:
                break
            if e8(g)["n"] < 76:
                p("  ** shrink at", a)
                break
        # if at x52 y34, go D to bottom and west to x16 then up/A5
        if prev and prev["cx"] >= 50:
            p("  on right col mid — descend")
            for i in range(8):
                b = (prev["cx"], prev["cy"])
                guid, g, prev, _, ok, d = flush(guid, g, prev, 2, 2)
                a = (prev["cx"], prev["cy"]) if prev else None
                p(f"  D{i}", b, "->", a, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
                if a == b or ok:
                    if ok:
                        cleared = True
                    break
            if prev and prev["cy"] >= 50:
                # west to x16
                for i in range(10):
                    b = (prev["cx"], prev["cy"])
                    guid, g, prev, _, ok, d = flush(guid, g, prev, 3, 2)
                    a = (prev["cx"], prev["cy"]) if prev else None
                    p(f"  L{i}", b, "->", a, "e8", e8(g)["n"])
                    if ok:
                        cleared = True
                        break
                    if a == b:
                        break
                    if e8(g)["n"] < 76:
                        p("  ** bottom shrink", a)
                        for a5 in (5, 5):
                            d = act(guid, a5)
                            guid = d["guid"]
                            g = plane(d)
                            prev = actor(g, prev)
                        p("  A5", prev, e8(g)["n"], d.get("levels_completed"))

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_RIGHTCOL_PARTIAL"
    if cleared:
        CLEAR.write_text(json.dumps({"cleared": True, "out": out}, indent=2, default=str), encoding="utf-8")
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
