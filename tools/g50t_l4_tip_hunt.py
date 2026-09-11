"""g50t L4: tip hunt near snake ends; try (40,22)↓ and left-of-snake.

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

OUT = ROOT / "tests/fixtures/g50t_l4_tip_hunt.json"
CLEAR = ROOT / "tests/fixtures/g50t_l4_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]


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
    gid = s.get(f"{BASE}/api/games/g50t", headers=H(key), timeout=20).json()["game_id"]
    p("opened", gid)
    nact = [0]
    out = {"cleared": False}

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

    def play(guid, g, prev, seq, stop_lv=None):
        for a_ in seq:
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, False, True
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            lv = d.get("levels_completed") or 0
            if stop_lv is not None and lv >= stop_lv:
                return guid, g, prev, d, True, False
            if lv > 3:
                return guid, g, prev, d, True, False
        return guid, g, prev, d, False, False

    def enter_l4():
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
        if not ok and not dead:
            guid, g, prev, d, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        guid, g, prev, d, ok, dead = play(guid, g, prev, TO_TIP2 + [5, 5])
        if (d.get("levels_completed") or 0) < 3 and not dead:
            guid, g, prev, d, ok, dead = play(guid, g, prev, TIP1_LEAVE)
            guid, g, prev, d, ok, dead = play(guid, g, prev, L3_WEST_CLEAR, stop_lv=3)
        if (d.get("levels_completed") or 0) < 3 or "guid" not in d:
            return None, None, None, d, False
        d = act(guid, 4)
        if "guid" not in d:
            return None, None, None, d, False
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, None)
        p("L4", (prev["cx"], prev["cy"]), "e8", e8(g)["n"], "nact", nact[0])
        return guid, g, prev, d, True

    def show(tag, prev, g, d):
        p(f"  {tag}", (prev["cx"], prev["cy"]) if prev else None, "e8", einfo(g), "lv", d.get("levels_completed"), "n", nact[0])

    trials = {
        # to (40,22) then D toward snake right tip
        "D_from_4022": [2, 2, 2, 4, 4, 2, 2, 5, 5, 2, 3, 3],
        # to (34,22) D
        "D_from_3422": [2, 2, 2, 4, 2, 2, 5, 5],
        # top to (46,10)/(52,10) then down right col past c15?
        "rightcol": [4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 3, 3],
        # hold on snake: approach (28,22) and keep D+A5 buffer
        "A5_queue_2822": [2, 2, 2, 5, 2, 5],
        # west top, down to snake left tip area — can't pass y28; try A5 at (10,22)
        "A5_at_1022": [3, 3, 3, 2, 2, 5, 5, 2, 2],
        # walk onto known floor south of snake if any open after shrink attempt
        "east_then_south": [2, 2, 4, 4, 4, 2, 2, 2, 3, 2, 2, 3, 3, 3],
    }

    for name, seq in trials.items():
        p(f"## {name}")
        guid, g, prev, d, ok = enter_l4()
        if not ok:
            out[name] = {"enter_fail": True}
            continue
        log = []
        for a_ in seq:
            before_e = e8(g)["n"]
            d = act(guid, a_)
            if "guid" not in d:
                log.append({"a": a_, "err": {k: d.get(k) for k in d if k != "frame"}})
                break
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            rec = {
                "a": a_,
                "pos": (prev["cx"], prev["cy"]) if prev else None,
                "e8": e8(g)["n"],
                "de8": e8(g)["n"] - before_e,
                "lv": d.get("levels_completed"),
            }
            log.append(rec)
            if rec["de8"] or True:
                show(f"A{a_}", prev, g, d)
            if (d.get("levels_completed") or 0) > 3:
                out["cleared"] = True
                CLEAR.write_text(
                    json.dumps({"cleared": True, "method": name, "log": log, "nact": nact[0]}, indent=2, default=str),
                    encoding="utf-8",
                )
                break
        path = []
        for r in log:
            if r.get("pos") and (not path or path[-1] != r["pos"]):
                path.append(r["pos"])
        shrinks = [r for r in log if r.get("de8")]
        p("  path", path, "shrinks", shrinks)
        out[name] = {"path": path, "shrinks": shrinks, "final_e8": einfo(g) if prev else None, "nact": nact[0]}
        if out["cleared"]:
            break

    out["reading"] = "L4_CLEAR" if out["cleared"] else "L4_TIP_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
