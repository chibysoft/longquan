"""g50t L3: A5 at gate (52,16) / (34,22) after latch; try open rightcol.

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

OUT = ROOT / "tests/fixtures/g50t_l3_gate_a5.json"
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

    def to_5216(guid, g, prev):
        guid, g, prev, ok = play(
            guid, g, prev, [1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4]
        )
        # settle R then one D (first D flushes R)
        for a_ in (4, 4, 2, 2):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        return guid, g, prev

    def to_3422(guid, g, prev):
        # from (34,34) pending L: U U L L → (34,22) settled
        for a_ in (1, 1, 3, 3):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        return guid, g, prev

    out = {}
    cleared = False

    trials = {
        "a5_at_5216": "gate",
        "a5_at_3422_latched": "pierce",
        "a5_at_5210": "top_right",
        "a5_at_1010": "top_left",
    }

    for name in trials:
        p(f"## {name}")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch(guid, g, prev)
        p("  latched", prev, "e8", e8(g)["n"])
        if name == "a5_at_5216":
            guid, g, prev = to_5216(guid, g, prev)
        elif name == "a5_at_3422_latched":
            guid, g, prev = to_3422(guid, g, prev)
        elif name == "a5_at_5210":
            guid, g, prev, _ = play(
                guid, g, prev, [1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4]
            )
        elif name == "a5_at_1010":
            guid, g, prev, _ = play(
                guid, g, prev, [1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 3]
            )
        p("  before A5", prev, "e8", e8(g)["n"], "c11", int(np.sum(g == 11)))
        e0 = e8(g)["n"]
        # settle same-dir noop then A5
        for a_ in (5, 5):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            p(
                f"  A5",
                prev,
                "e8",
                e8(g)["n"],
                "c11",
                int(np.sum(g == 11)),
                "lv",
                d.get("levels_completed"),
            )
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                break
        out[name] = {
            "e8": [e0, e8(g)["n"]],
            "actor": prev,
            "c11": int(np.sum(g == 11)),
            "lv": d.get("levels_completed"),
        }
        if cleared:
            CLEAR.write_text(
                json.dumps({"cleared": True, "method": name}, indent=2, default=str),
                encoding="utf-8",
            )
            break
        # if still alive at gate with e8=76, try D again
        if prev and e8(g)["n"] == 76 and name == "a5_at_5216":
            p("  still alive — retry D")
            for i in range(6):
                b = (prev["cx"], prev["cy"])
                d = act(guid, 2)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                a = (prev["cx"], prev["cy"]) if prev else None
                p(f"  D{i}", b, "->", a, "e8", e8(g)["n"])
                if a != b:
                    p("  ** GATE OPENED")
                    # continue to bottom and toward goal
                    for j in range(20):
                        if not prev:
                            break
                        cx, cy = prev["cx"], prev["cy"]
                        # aim (22,28) then (22,22)
                        tx, ty = (22, 22) if cy >= 26 and cx <= 28 else (22, 28) if cy >= 20 else (52, 52)
                        dx, dy = tx - cx, ty - cy
                        aid = (4 if dx > 0 else 3) if abs(dx) >= abs(dy) else (2 if dy > 0 else 1)
                        b2 = (cx, cy)
                        for a_ in (aid, aid):
                            d = act(guid, a_)
                            guid = d["guid"]
                            g = plane(d)
                            prev = actor(g, prev)
                        p(f"  hunt", b2, "->", (prev["cx"], prev["cy"]) if prev else None, "lv", d.get("levels_completed"))
                        if (d.get("levels_completed") or 0) > 2:
                            cleared = True
                            CLEAR.write_text(
                                json.dumps({"cleared": True, "method": "gate_open_hunt"}, indent=2, default=str),
                                encoding="utf-8",
                            )
                            break
                    break
                if i >= 2:
                    break

    # Special: A5-queue at gate — while at (52,10), send A5 then D so A5 executes at (52,16)
    if not cleared:
        p("## queue A5 into 5216")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch(guid, g, prev)
        guid, g, prev, _ = play(
            guid, g, prev, [1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4]
        )
        # at (52,10) pending R; D flushes R; send A5 so next lands
        # Want: at (52,16) when A5 executes
        # settle: R noop, D -> 16 pending D, A5 -> exec D noop?, pending A5, A5 -> fire
        for a_ in (4, 2, 5, 5):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            p("  q", a_, prev, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                break
        out["queue_5216"] = {"actor": prev, "e8": e8(g)["n"], "lv": d.get("levels_completed")}
        # if dead+unlatch, note; if alive try D
        if prev and e8(g)["n"] <= 76:
            for i in range(8):
                b = (prev["cx"], prev["cy"])
                d = act(guid, 2)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                a = (prev["cx"], prev["cy"]) if prev else None
                p(f"  qD{i}", b, "->", a, "e8", e8(g)["n"])
                if a != b and a and a[1] > 16:
                    p("  ** opened after queue A5")
                if a == b and i >= 2:
                    break

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_GATE_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
