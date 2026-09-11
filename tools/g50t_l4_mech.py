"""g50t L4: map c15, dir smoke from spawn, tip shrink hunt, goal approach.

tags=["g50t_recon"]
Budget: L3 clear ~208; keep L4 probes short.
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

OUT = ROOT / "tests/fixtures/g50t_l4_mech.json"
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


def c15info(g):
    ys, xs = np.where(g == 15)
    if len(xs) == 0:
        return {"n": 0}
    return {
        "n": int(len(xs)),
        "xmin": int(xs.min()),
        "xmax": int(xs.max()),
        "ymin": int(ys.min()),
        "ymax": int(ys.max()),
    }


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
    out = {}

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
        # transition
        d = act(guid, 4)
        if "guid" not in d:
            return None, None, None, d, False
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, None)
        p("L4", (prev["cx"], prev["cy"]) if prev else None, "e8", einfo(g), "c15", c15info(g), "nact", nact[0])
        return guid, g, prev, d, True

    def show(tag, prev, g, d=None):
        p(
            f"  {tag}",
            (prev["cx"], prev["cy"]) if prev else None,
            "e8",
            e8(g)["n"],
            "c15",
            c15info(g),
            "lv",
            None if d is None else d.get("levels_completed"),
            "n",
            nact[0],
        )

    # --- trial A: settle dirs from spawn ---
    p("## dirs")
    guid, g, prev, d, ok = enter_l4()
    if not ok:
        out["reading"] = "ENTER_FAIL"
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        return
    # drain unknown pending with harmless: double each dir from fresh enters would be costly.
    # At spawn (28,10): try D*2, record path
    path = [(prev["cx"], prev["cy"])]
    for a_ in [2, 2, 2, 2, 2, 2, 3, 3, 3, 4, 4, 4, 1, 1]:
        before_e = e8(g)["n"]
        d = act(guid, a_)
        if "guid" not in d:
            out["dirs_fail"] = {k: d.get(k) for k in d if k != "frame"}
            break
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        pos = (prev["cx"], prev["cy"]) if prev else None
        if pos and (not path or path[-1] != pos):
            path.append(pos)
        de = e8(g)["n"] - before_e
        if de:
            p("  *** e8", before_e, "->", e8(g)["n"], "at", pos, "A", a_)
        show(f"A{a_}", prev, g, d)
        if (d.get("levels_completed") or 0) > 3:
            CLEAR.write_text(json.dumps({"cleared": True, "method": "dirs"}, indent=2), encoding="utf-8")
            out["cleared"] = True
            break
    out["dirs_path"] = path
    out["dirs_final_e8"] = einfo(g) if prev else None
    p("  path", path)

    if out.get("cleared"):
        out["reading"] = "L4_CLEAR"
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        p("READING L4_CLEAR")
        s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)
        return

    # --- trial B: go to snake band y28, walk along, watch e8 ---
    p("## snake band")
    guid, g, prev, d, ok = enter_l4()
    if not ok:
        return
    # from (28,10) down to y28: need ~3 downs (10→16→22→28)
    seq = [2, 2, 2, 2]
    for a_ in seq:
        d = act(guid, a_)
        if "guid" not in d:
            break
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        show(f"D", prev, g, d)
    # walk L along snake then R, note shrinks
    band = []
    for a_ in [3] * 6 + [4] * 10 + [5, 5]:
        before_e = e8(g)["n"]
        before = (prev["cx"], prev["cy"]) if prev else None
        d = act(guid, a_)
        if "guid" not in d:
            band.append({"a": a_, "err": {k: d.get(k) for k in d if k != "frame"}})
            break
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        rec = {
            "a": a_,
            "pos": (prev["cx"], prev["cy"]) if prev else None,
            "e8": e8(g)["n"],
            "de8": e8(g)["n"] - before_e,
            "c15": c15info(g),
            "lv": d.get("levels_completed"),
        }
        band.append(rec)
        if rec["de8"] or before != rec["pos"]:
            show(f"A{a_}", prev, g, d)
        if (d.get("levels_completed") or 0) > 3:
            CLEAR.write_text(json.dumps({"cleared": True, "method": "band"}, indent=2), encoding="utf-8")
            out["cleared"] = True
            break
    out["band"] = band

    # --- trial C: left then down toward goal (10,52) ---
    if not out.get("cleared"):
        p("## goal hunt left-down")
        guid, g, prev, d, ok = enter_l4()
        if ok:
            # top west then down left col
            for a_ in [3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 3, 2, 2]:
                d = act(guid, a_)
                if "guid" not in d:
                    p("  fail", nact[0])
                    break
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                show(f"A{a_}", prev, g, d)
                if e8(g)["n"] != 52:
                    p("  e8chg", e8(g)["n"])
                if (d.get("levels_completed") or 0) > 3:
                    CLEAR.write_text(
                        json.dumps({"cleared": True, "method": "goal_hunt", "nact": nact[0]}, indent=2),
                        encoding="utf-8",
                    )
                    out["cleared"] = True
                    break
            out["goal_pos"] = (prev["cx"], prev["cy"]) if prev else None
            out["goal_e8"] = einfo(g) if prev else None

    out["nact"] = nact[0]
    out["reading"] = "L4_CLEAR" if out.get("cleared") else "L4_MECH"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
