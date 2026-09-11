"""g50t L4: NO tip1 latch — rightcol explore at e8=52; hunt tip2 / bottom / c15 pierce.

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

OUT = ROOT / "tests/fixtures/g50t_l4_prelatch_right.json"
FRAME = ROOT / "tests/fixtures/g50t_l4_prelatch_frame.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]
# from L4 spawn (28,10): to right col — R blocked at 34 hole on y10; via (28,22)(34,22)(40,22)(40,10)(52,10)
TO_RIGHT = [2, 2, 4, 1, 1, 4, 4, 2, 2, 2, 2, 2, 2, 2]


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
                p(" ", a_, (prev["cx"], prev["cy"]) if prev else None, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
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
        if (d.get("levels_completed") or 0) < 3 and not dead:
            guid, g, prev, d, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        guid, g, prev, d, ok, dead = play(guid, g, prev, TO_TIP2 + [5, 5])
        if (d.get("levels_completed") or 0) < 3 and not dead:
            guid, g, prev, d, ok, dead = play(guid, g, prev, TIP1_LEAVE)
            guid, g, prev, d, ok, dead = play(guid, g, prev, L3_WEST_CLEAR, stop_lv=3)
        d = act(guid, 4)
        guid, g, prev = d["guid"], plane(d), actor(plane(d), None)
        p("L4", (prev["cx"], prev["cy"]), einfo(g), "nact", nact[0])
        return guid, g, prev, d

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
            log.append({"label": label, "a": a_, "from": before, "to": pos, "e8": e8(g)["n"], "de": de, "lv": d.get("levels_completed")})
            p(f"  {label}", a_, before, "->", pos, "e8", e8(g)["n"], "de", de, "lv", d.get("levels_completed"))
            if de < 0:
                p("  *** SHRINK", einfo(g))
                FRAME.write_text(
                    json.dumps({"frame": d.get("frame"), "pos": pos, "e8": einfo(g)}, default=str),
                    encoding="utf-8",
                )
            if (d.get("levels_completed") or 0) > 3:
                p("  *** CLEAR")
                return guid, g, prev, d, False
        return guid, g, prev, d, False

    guid, g, prev, d = enter_l4()
    # no tip — go right
    p("## rightcol e8=52")
    guid, g, prev, d, dead = slog("R", guid, g, prev, TO_RIGHT + [3, 3, 3, 2, 2, 3, 3, 2, 3, 5, 5, 2, 3, 3, 3, 3])

    # Phase2: tip HOLD then immediately rightcol while... can't. 
    # Phase2: tip step only, leave recover, then right — baseline
    # Phase3: tip A5 death respawn, WITHOUT leave-persist path — just A5 once then right from spawn
    if (d.get("levels_completed") or 0) <= 3:
        p("## tip A5 only then right (no leave persist)")
        guid, g, prev, d = enter_l4()
        guid, g, prev, d, dead = slog("A5only", guid, g, prev, [2, 2, 2, 4, 2, 5, 5])
        # respawn ~ (28,10); try right again; e8 may be latched weird
        p("after A5", (prev["cx"], prev["cy"]), einfo(g))
        guid, g, prev, d, dead = slog("R2", guid, g, prev, TO_RIGHT + [3, 2, 2, 3, 3, 3, 3, 2])

    result = {
        "cleared": (d.get("levels_completed") or 0) > 3 if d else False,
        "final_pos": (prev["cx"], prev["cy"]) if prev else None,
        "final_e8": einfo(g) if g is not None else None,
        "lv": d.get("levels_completed") if d else None,
        "nact": nact[0],
        "shrinks": [r for r in log if r.get("de", 0) < 0],
        "log": log,
    }
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    p("READING", {k: result[k] for k in result if k != "log"})
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
