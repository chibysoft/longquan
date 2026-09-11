"""g50t L3: dump tip2 frame; climb left from (10,52); tip2-A5 then re-latch tip1.

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

OUT = ROOT / "tests/fixtures/g50t_l3_tip2_dump.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
FRAME = ROOT / "tests/fixtures/g50t_l3_tip2_frame.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TO_LEFT10 = TO_BOTTOM + [3, 3, 3, 3, 3, 3, 3]  # toward x10


def p(*a, **k):
    print(*a, **k, flush=True)


def c11info(g):
    ys, xs = np.where(g == 11)
    if len(xs) == 0:
        return {"n": 0}
    return {"n": int(len(xs)), "xmin": int(xs.min()), "xmax": int(xs.max())}


def e8info(g):
    info = e8(g)
    ys, xs = np.where(g == 8)
    if len(xs) == 0:
        return info
    info = dict(info)
    info["xmin"] = int(xs.min())
    info["xmax"] = int(xs.max())
    info["ymin"] = int(ys.min())
    info["ymax"] = int(ys.max())
    return info


def show(tag, prev, g, d=None):
    p(
        f"  {tag}",
        (prev["cx"], prev["cy"]) if prev else None,
        "e8",
        e8info(g),
        "c11",
        c11info(g),
        "lv",
        None if d is None else d.get("levels_completed"),
    )


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
                    "pos": (prev["cx"], prev["cy"]) if prev else None,
                    "e8": e8(g)["n"],
                    "lv": d.get("levels_completed"),
                }
            )
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, log, True
        return guid, g, prev, d, log, False

    def latch_tip1(guid, g, prev):
        guid, g, prev, d, log, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if ok:
            return guid, g, prev, d, log, True
        return play(guid, g, prev, TO_3434 + [4, 4, 3, 3])

    out = {"cleared": False}
    cleared = False

    # --- dump tip2 hold frame ---
    p("## tip2 dump")
    guid, g, prev = enter_l3()
    guid, g, prev, d, _, ok = latch_tip1(guid, g, prev)
    if ok:
        cleared = True
    guid, g, prev, d, _, ok = play(guid, g, prev, TO_TIP2)
    show("tip2", prev, g, d)
    if ok:
        cleared = True
    FRAME.write_text(json.dumps({"frame": d.get("frame"), "levels": d.get("levels_completed"), "pos": (prev["cx"], prev["cy"]), "e8": e8info(g), "c11": c11info(g)}, default=str), encoding="utf-8")
    # neighbor cells center values
    cx, cy = int(round(prev["cx"])), int(round(prev["cy"]))
    neigh = {}
    for dx, dy, name in [(0, -6, "U"), (0, 6, "D"), (-6, 0, "L"), (6, 0, "R"), (0, -12, "U2"), (0, 0, "C")]:
        x, y = cx + dx, cy + dy
        if 2 <= x <= 61 and 2 <= y <= 61:
            sub = g[y - 2 : y + 3, x - 2 : x + 3]
            neigh[name] = {
                "to": (x, y),
                "center": int(g[y, x]),
                "hist": {int(k): int(v) for k, v in zip(*np.unique(sub, return_counts=True))},
            }
    out["tip2_neighbors"] = neigh
    p("  neighbors", json.dumps(neigh))
    # col x22 patch y28..52
    col = g[28:55, 20:25].tolist()
    out["col22_patch"] = col
    # star live
    for aid, label in [(1, "U"), (2, "D"), (3, "L"), (4, "R")]:
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, _ = latch_tip1(guid, g, prev)
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_TIP2)
        before = (prev["cx"], prev["cy"], e8(g)["n"])
        for _ in range(2):
            d = act(guid, aid)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        after = (prev["cx"], prev["cy"], e8(g)["n"]) if prev else None
        out[f"star_{label}"] = {"before": before, "after": after}
        p(f"  star {label}", before, "->", after)

    if cleared:
        CLEAR.write_text(json.dumps({"cleared": True}, indent=2), encoding="utf-8")
    else:
        # --- left climb from (10,52) with tip1 latch only ---
        p("## left climb 1052")
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, ok = latch_tip1(guid, g, prev)
        guid, g, prev, d, log, ok = play(guid, g, prev, TO_LEFT10)
        show("at_left", prev, g, d)
        path = []
        for a_ in [1] * 12 + [4] * 6 + [1] * 4 + [4] * 4:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            pos = (prev["cx"], prev["cy"]) if prev else None
            if pos and (not path or path[-1] != pos):
                path.append(pos)
            show(f"A{a_}", prev, g, d)
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                CLEAR.write_text(
                    json.dumps({"cleared": True, "method": "left_climb", "path": path}, indent=2, default=str),
                    encoding="utf-8",
                )
                break
        out["left_climb"] = {"path": path, "final_e8": e8(g)["n"]}
        p("  left path", path)

    if not cleared:
        # tip2 hold → does (22,28) or mid open? try from tip2 go R to 28 then U (with restore)
        # OR: A5 tip2 then FULL tip1 relatch and check e8
        p("## A5 tip2 then relatch tip1")
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, _ = latch_tip1(guid, g, prev)
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_TIP2)
        show("beforeA5", prev, g, d)
        for a_ in (5, 5):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            show("A5", prev, g, d)
        # now at spawn e8=92; re-latch tip1
        guid, g, prev, d, _, ok = latch_tip1(guid, g, prev)
        show("relatch", prev, g, d)
        out["relatch_after_tip2_A5"] = {"e8": e8info(g), "pos": (prev["cx"], prev["cy"]) if prev else None}
        # go to tip2 again — does it shrink further?
        guid, g, prev, d, _, ok = play(guid, g, prev, TO_TIP2)
        show("tip2_again", prev, g, d)
        out["tip2_again"] = {"e8": e8info(g), "pos": (prev["cx"], prev["cy"]) if prev else None}
        if (d.get("levels_completed") or 0) > 2:
            cleared = True

    if not cleared:
        # While holding tip2 e8=60, maybe need confirm at tip1 scar (40,34)?
        p("## tip2 then run to tip1 scar")
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, _ = latch_tip1(guid, g, prev)
        # from latch at 3434 go bottom tip2 — leaves tip2 restores. Instead:
        # hold tip2, can't reach tip1 without leaving.
        # Try: tip2 shrink, leave (restore 76), go tip1 scar A5? already latched.
        # Try standing tip2 and A5 with L2 buffer from (28,52):
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_BOTTOM + [3, 3, 3, 3])  # ~28,52 pend L?
        show("at28", prev, g, d)
        # want land tip2 with A5 pending: at 28 pend L, send A5
        for a_ in (5, 1, 5):  # variants
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            show(f"bufA{a_}", prev, g, d)
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                break
        out["buf_from28"] = {"pos": (prev["cx"], prev["cy"]) if prev else None, "e8": e8(g)["n"]}

        # clean buffer: at 28 after TO_BOTTOM+[3]*4
        # Trace pending: bottom ends pend D; L*4:
        # L drain D, L→46, L→40, L→34 — at 34 pend L. Need one more L to 28.
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, _ = latch_tip1(guid, g, prev)
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_BOTTOM + [3, 3, 3, 3, 3])
        show("at28b", prev, g, d)  # should be 28 pend L
        # A5: exec L → 22 tip2 e8=60, pend A5
        d = act(guid, 5)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        show("land_A5pend", prev, g, d)
        # fire A5
        d = act(guid, 5)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        show("fireA5", prev, g, d)
        out["land_with_A5"] = {
            "pos": (prev["cx"], prev["cy"]) if prev else None,
            "e8": e8info(g),
            "lv": d.get("levels_completed"),
        }
        if (d.get("levels_completed") or 0) > 2:
            cleared = True
            CLEAR.write_text(json.dumps({"cleared": True, "method": "land_with_A5"}, indent=2), encoding="utf-8")
        elif e8(g)["n"] <= 60:
            # try navigate / revisit
            for a_ in [4, 4, 3, 3, 3, 1, 1, 1, 4]:
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                show("post", prev, g, d)
                if (d.get("levels_completed") or 0) > 2:
                    cleared = True
                    break

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_TIP2_DUMP"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
