"""g50t L3: track c11 bbox while walking latch→gate; hunt freeze-clear.

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

OUT = ROOT / "tests/fixtures/g50t_l3_c11_track.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]


def p(*a, **k):
    print(*a, **k, flush=True)


def c11info(g):
    ys, xs = np.where(g == 11)
    if len(xs) == 0:
        return {"n": 0, "bbox": None, "xmax": None}
    return {
        "n": int(len(xs)),
        "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
        "xmax": int(xs.max()),
        "xmin": int(xs.min()),
    }


def rightcol_blocked(g):
    """True if (52,22) 5x5 has any 11."""
    patch = g[20:25, 50:55]
    return int(np.sum(patch == 11)) > 0, int(np.sum(patch == 11))


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
        for a_ in seq:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, True
        return guid, g, prev, False

    def latch(guid, g, prev):
        guid, g, prev, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if ok:
            return guid, g, prev, True
        guid, g, prev, ok = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        return guid, g, prev, ok

    out = {}
    cleared = False

    # Track c11 while moving latch → top → east → down
    p("## track c11 latch to gate")
    guid, g, prev = enter_l3()
    # before latch
    info0 = c11info(g)
    blk0, n11_0 = rightcol_blocked(g)
    p("  spawn L3", prev, "c11", info0, "right_blk", blk0, n11_0)
    guid, g, prev, _ = latch(guid, g, prev)
    info1 = c11info(g)
    blk1, n11_1 = rightcol_blocked(g)
    p("  latched", prev, "c11", info1, "right_blk", blk1, n11_1, "e8", e8(g)["n"])

    track = [
        {
            "where": "latched",
            "actor": prev,
            "c11": info1,
            "right_blk": blk1,
            "n11_patch": n11_1,
            "e8": e8(g)["n"],
        }
    ]
    seq = [1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2, 2, 2]
    for a_ in seq:
        d = act(guid, a_)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        info = c11info(g)
        blk, n11p = rightcol_blocked(g)
        row = {
            "a": a_,
            "actor": (prev["cx"], prev["cy"]) if prev else None,
            "c11": info,
            "right_blk": blk,
            "n11_patch": n11p,
            "e8": e8(g)["n"],
            "lv": d.get("levels_completed"),
        }
        track.append(row)
        if blk != track[-2].get("right_blk") or info.get("xmax") != track[-2]["c11"].get("xmax"):
            p(
                "  CHANGE",
                row["actor"],
                "A",
                a_,
                "c11",
                info,
                "right_blk",
                blk,
                n11p,
            )
        if (d.get("levels_completed") or 0) > 2:
            cleared = True
            break
    out["track"] = track
    p("  final", prev, c11info(g), "right_blk", rightcol_blocked(g))

    # Try: after latch, stay near tip (c11 clear on right), A5 remote? already failed.
    # Try: latch, go ONLY up to (34,10) without going east past tip x — check right_blk
    if not cleared:
        p("## how far east until right_blk flips")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch(guid, g, prev)
        # to top at x34
        for a_ in (1, 1, 1, 1, 1, 1):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        p("  at", prev, "c11", c11info(g), "blk", rightcol_blocked(g))
        # step east one cell at a time (flush R)
        flips = []
        for i in range(10):
            before = (prev["cx"], prev["cy"])
            info_b = c11info(g)
            blk_b, n_b = rightcol_blocked(g)
            for a_ in (4, 4):
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
            after = (prev["cx"], prev["cy"]) if prev else None
            info_a = c11info(g)
            blk_a, n_a = rightcol_blocked(g)
            p(
                f"  E{i}",
                before,
                "->",
                after,
                "blk",
                blk_b,
                "->",
                blk_a,
                "c11xmax",
                info_b.get("xmax"),
                "->",
                info_a.get("xmax"),
                "n",
                info_b.get("n"),
                "->",
                info_a.get("n"),
            )
            flips.append(
                {
                    "i": i,
                    "from": before,
                    "to": after,
                    "blk": [blk_b, blk_a],
                    "c11": [info_b, info_a],
                    "n11_patch": [n_b, n_a],
                }
            )
            if blk_a and not blk_b:
                p("  ** FLIP to blocked at", after)
            if after == before:
                break
        out["east_flip"] = flips

        # If we find x where still clear, try D from that column toward y22
        if not cleared:
            p("## drop from columns while right still clear")
            for tx in (34, 40, 46):
                guid, g, prev = enter_l3()
                guid, g, prev, _ = latch(guid, g, prev)
                # top
                for a_ in (1, 1, 1, 1, 1, 1):
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                # east toward tx
                while prev and prev["cx"] < tx - 2:
                    for a_ in (4, 4):
                        d = act(guid, a_)
                        guid = d["guid"]
                        g = plane(d)
                        prev = actor(g, prev)
                blk, n11p = rightcol_blocked(g)
                p("  col", prev, "c11", c11info(g), "right_blk", blk, n11p)
                # try D
                path = []
                for i in range(8):
                    b = (prev["cx"], prev["cy"])
                    d = act(guid, 2)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                    a = (prev["cx"], prev["cy"]) if prev else None
                    path.append(a)
                    p(
                        f"    D{i}",
                        b,
                        "->",
                        a,
                        "blk",
                        rightcol_blocked(g),
                        "e8",
                        e8(g)["n"],
                        "lv",
                        d.get("levels_completed"),
                    )
                    if (d.get("levels_completed") or 0) > 2:
                        cleared = True
                        break
                    if a == b and i >= 1:
                        break
                out[f"drop_x{tx}"] = {
                    "path": path,
                    "c11": c11info(g),
                    "final": prev,
                    "lv": d.get("levels_completed"),
                }
                if cleared:
                    CLEAR.write_text(
                        json.dumps({"cleared": True, "method": f"drop_x{tx}"}, indent=2, default=str),
                        encoding="utf-8",
                    )
                    break

    # Try: latch, go to (34,22) where we pierce c11, grind east while watching blk
    if not cleared:
        p("## from 3422 push into c11 watching xmax")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch(guid, g, prev)
        for a_ in (1, 1, 3, 3):  # settle 3422
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        p("  at", prev, "c11", c11info(g), "blk", rightcol_blocked(g))
        for i in range(8):
            b = (prev["cx"], prev["cy"])
            info_b = c11info(g)
            for a_ in (4, 4):
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
            a = (prev["cx"], prev["cy"]) if prev else None
            p(
                f"  R{i}",
                b,
                "->",
                a,
                "c11",
                c11info(g),
                "blk",
                rightcol_blocked(g),
                "n",
                int(np.sum(g == 11)),
            )
            if a == b and i >= 1:
                break

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_C11TRACK_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
