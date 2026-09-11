"""g50t L3: descend-pierce (34,22) clears c11 east — then rush east on y22.

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

OUT = ROOT / "tests/fixtures/g50t_l3_pierce_east.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]


def p(*a, **k):
    print(*a, **k, flush=True)


def c11info(g):
    ys, xs = np.where(g == 11)
    if len(xs) == 0:
        return {"n": 0, "xmax": None, "bbox": None}
    return {
        "n": int(len(xs)),
        "xmax": int(xs.max()),
        "xmin": int(xs.min()),
        "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
    }


def right_blk(g):
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

    def status(label, prev, g, d=None):
        blk, n = right_blk(g)
        p(
            f"  {label}",
            (prev["cx"], prev["cy"]) if prev else None,
            "e8",
            e8(g)["n"],
            "c11",
            c11info(g),
            "blk",
            blk,
            n,
            "lv",
            None if d is None else d.get("levels_completed"),
        )

    out = {}
    cleared = False

    # Primary: latch → top → descend to y22 → IMMEDIATELY east
    variants = {
        # after latch at 3434: U to top, D D to land 22 with pierce, R's
        # Buffer: from 3434 pending L; U*6 → top; D: flush, D: to 16, D: to 22
        "descend_then_R": [1, 1, 1, 1, 1, 1, 2, 2, 2, 4, 4, 4, 4, 4, 4, 4, 4],
        # more D settle then R
        "descend_settle_R": [1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 4, 4, 4, 4, 4, 4],
        # descend to 22, R, if move then continue to goal
        "descend_R_hunt": [1, 1, 1, 1, 1, 1, 2, 2, 2] + [4] * 10 + [2, 2, 3, 3, 3, 3, 1, 1],
        # descend only to 16 then R? (maybe walk above bar)
        "at16_R": [1, 1, 1, 1, 1, 1, 2, 2, 4, 4, 4, 4, 4, 4, 2, 2, 2],
        # from latch stay low: U once to 28, U to 22 (ascend — expect expand) control
        "ascend_control_R": [1, 1, 3, 3, 4, 4, 4, 4],
    }

    for name, seq in variants.items():
        p(f"## {name}")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch(guid, g, prev)
        status("latched", prev, g)
        log = []
        for a_ in seq:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            blk, n = right_blk(g)
            log.append(
                {
                    "a": a_,
                    "actor": (prev["cx"], prev["cy"]) if prev else None,
                    "e8": e8(g)["n"],
                    "c11": c11info(g),
                    "blk": blk,
                    "n11p": n,
                    "lv": d.get("levels_completed"),
                }
            )
            if prev and (abs(prev["cy"] - 22) < 3 or a_ in (4, 2)):
                status(f"A{a_}", prev, g, d)
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                p("*** L3 CLEAR", name)
                break
        # unique path
        path = []
        for r in log:
            if r["actor"] and (not path or path[-1] != r["actor"]):
                path.append(r["actor"])
        p("  path", path)
        out[name] = {"path": path, "log": log[-8:], "final": log[-1] if log else None}
        if cleared:
            CLEAR.write_text(
                json.dumps({"cleared": True, "method": name, "log": log}, indent=2, default=str),
                encoding="utf-8",
            )
            break
        # if we moved east of x34 at y22, keep hunting
        if prev and prev["cx"] > 36 and abs(prev["cy"] - 22) < 4:
            p("  ** EAST OF PIERCE — hunt goal")
            for _ in range(20):
                cx, cy = prev["cx"], prev["cy"]
                dx, dy = 22 - cx, 22 - cy
                if abs(dx) < 3 and abs(dy) < 3:
                    p("  ON GOAL", prev)
                aid = (4 if dx > 0 else 3) if abs(dx) >= abs(dy) else (2 if dy > 0 else 1)
                b = (cx, cy)
                for a_ in (aid, aid):
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                status("hunt", prev, g, d)
                if (d.get("levels_completed") or 0) > 2:
                    cleared = True
                    CLEAR.write_text(
                        json.dumps({"cleared": True, "method": name + "+hunt"}, indent=2, default=str),
                        encoding="utf-8",
                    )
                    break
                if prev and (prev["cx"], prev["cy"]) == b:
                    break
            if cleared:
                break

    # Closed-loop: latch, top, descend until y~22 and blk False, then only R
    if not cleared:
        p("## closed pierce-east")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch(guid, g, prev)
        # to top
        for a_ in (1, 1, 1, 1, 1, 1):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        status("top", prev, g)
        # descend until cy>=22 or blk clears at y22
        for i in range(10):
            d = act(guid, 2)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            status(f"D{i}", prev, g, d)
            if prev and prev["cy"] >= 21:
                blk, _ = right_blk(g)
                if not blk:
                    p("  pierce clear — RUSH EAST")
                    break
        # rush R
        moved_east = False
        for i in range(12):
            b = (prev["cx"], prev["cy"]) if prev else None
            d = act(guid, 4)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            a = (prev["cx"], prev["cy"]) if prev else None
            status(f"R{i}", prev, g, d)
            if a and b and a[0] > b[0] + 2:
                moved_east = True
                p("  ** MOVED EAST", b, "->", a)
            if a == b and i >= 2:
                break
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                break
        out["closed"] = {"moved_east": moved_east, "final": prev, "c11": c11info(g), "blk": right_blk(g)}

        # if east worked, dump patch ahead
        if moved_east and prev:
            cx, cy = int(round(prev["cx"])), int(round(prev["cy"]))
            p("  ahead patch\n", g[cy - 2 : cy + 3, cx : cx + 8])

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_PIERCE_EAST_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
