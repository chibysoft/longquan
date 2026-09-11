"""g50t L3: buffer-aware pierce-east — R at y16 so land y22 with pending R.

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

OUT = ROOT / "tests/fixtures/g50t_l3_pierce_rush.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]


def p(*a, **k):
    print(*a, **k, flush=True)


def c11info(g):
    ys, xs = np.where(g == 11)
    if len(xs) == 0:
        return {"n": 0, "xmax": None}
    return {"n": int(len(xs)), "xmax": int(xs.max()), "xmin": int(xs.min())}


def right_blk(g):
    return int(np.sum(g[20:25, 50:55] == 11))


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

    def latch2(guid, g, prev):
        guid, g, prev, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if ok:
            return guid, g, prev, True
        guid, g, prev, ok = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        return guid, g, prev, ok

    def show(tag, prev, g, d=None):
        p(
            f"  {tag}",
            (prev["cx"], prev["cy"]) if prev else None,
            "e8",
            e8(g)["n"],
            "c11",
            c11info(g),
            "blkN",
            right_blk(g),
            "lv",
            None if d is None else d.get("levels_completed"),
        )

    out = {}
    cleared = False

    # KEY SEQ: U*6 to top, D, D, then R*n
    # Lands (34,22) with pending R while pierce-cleared
    trials = {
        "bufR_pierce": [1, 1, 1, 1, 1, 1, 2, 2, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4],
        "bufR_pierce_Lgoal": [1, 1, 1, 1, 1, 1, 2, 2, 4, 4, 4, 4, 3, 3, 3, 3, 3, 3],
        "bufR_one_then_more": [1, 1, 1, 1, 1, 1, 2, 2, 4] + [4] * 12,
        # also try D*1 only then R (land 16 with R pending?)
        "D1_then_R": [1, 1, 1, 1, 1, 1, 2, 4, 4, 4, 4, 4, 4, 2, 2],
        # closed-loop version logged step by step
    }

    for name, seq in trials.items():
        p(f"## {name}")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch2(guid, g, prev)
        show("latch", prev, g)
        log = []
        for a_ in seq:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            log.append(
                {
                    "a": a_,
                    "pos": (prev["cx"], prev["cy"]) if prev else None,
                    "c11": c11info(g),
                    "blkN": right_blk(g),
                    "e8": e8(g)["n"],
                    "lv": d.get("levels_completed"),
                }
            )
            show(f"A{a_}", prev, g, d)
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                p("*** CLEAR")
                break
        path = []
        for r in log:
            if r["pos"] and (not path or path[-1] != r["pos"]):
                path.append(r["pos"])
        p("  path", path)
        out[name] = {"path": path, "final": log[-1] if log else None}
        if cleared:
            CLEAR.write_text(
                json.dumps({"cleared": True, "method": name, "log": log}, indent=2, default=str),
                encoding="utf-8",
            )
            break
        # if east of 34 at y22, hunt
        if prev and prev["cx"] >= 40 and 20 <= prev["cy"] <= 24:
            p("  EAST ON BAND — hunt")
            for _ in range(24):
                cx, cy = prev["cx"], prev["cy"]
                dx, dy = 22 - cx, 22 - cy
                aid = (4 if dx > 0 else 3) if abs(dx) >= abs(dy) else (2 if dy > 0 else 1)
                b = (cx, cy)
                for a_ in (aid, aid):
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                show("h", prev, g, d)
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

    # Explicit step log of THE critical 4 actions after top
    if not cleared:
        p("## micro critical")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch2(guid, g, prev)
        for a_ in (1, 1, 1, 1, 1, 1):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        show("top", prev, g)
        for a_ in (2, 2, 4, 4, 4, 4, 4, 4):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            show(f"critA{a_}", prev, g, d)
            if prev and prev["cx"] > 34:
                # dump cells east
                cx, cy = int(round(prev["cx"])), int(round(prev["cy"]))
                p("  row", g[cy, cx - 2 : cx + 10].tolist())
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                break
        out["micro"] = {"final": prev, "c11": c11info(g), "blkN": right_blk(g)}

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_RUSH_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
