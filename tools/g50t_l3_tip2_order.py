"""g50t L3: tip2 order / persist / snake-touch after shrink.

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

OUT = ROOT / "tests/fixtures/g50t_l3_tip2_order.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
# pierce+top+right to bottom (no tip1)
TO_BOTTOM_ONLY = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2, 2]
# but without tip1, is pierce+right open? c11 gate needs latch shrink!
# Without tip1 e8=92, right col may stay blocked. Test both.


def p(*a, **k):
    print(*a, **k, flush=True)


def c11info(g):
    ys, xs = np.where(g == 11)
    if len(xs) == 0:
        return {"n": 0}
    return {"n": int(len(xs)), "xmin": int(xs.min()), "xmax": int(xs.max())}


def einfo(g):
    e = e8(g)
    ys, xs = np.where(g == 8)
    if len(xs):
        e = dict(e)
        e.update(xmin=int(xs.min()), xmax=int(xs.max()), ymin=int(ys.min()), ymax=int(ys.max()))
    return e


def show(tag, prev, g, d=None):
    p(
        f"  {tag}",
        (prev["cx"], prev["cy"]) if prev else None,
        "e8",
        einfo(g),
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
            log.append({"a": a_, "pos": (prev["cx"], prev["cy"]) if prev else None, "e8": e8(g)["n"], "lv": d.get("levels_completed")})
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, log, True
        return guid, g, prev, d, log, False

    def tip1_latch(guid, g, prev):
        guid, g, prev, d, log, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if ok:
            return guid, g, prev, d, log, True
        return play(guid, g, prev, TO_3434 + [4, 4, 3, 3])

    def to_bottom(guid, g, prev):
        return play(guid, g, prev, TO_BOTTOM_ONLY)

    def to_tip2(guid, g, prev):
        return play(guid, g, prev, TO_BOTTOM_ONLY + [3, 3, 3, 3, 3, 1])

    out = {"cleared": False}
    cleared = False

    # A) tip1 latch → tip2 → A5 → respawn → tip1 latch carefully → tip2 leave persist?
    p("## persist chain")
    guid, g, prev = enter_l3()
    guid, g, prev, d, _, ok = tip1_latch(guid, g, prev)
    show("tip1", prev, g, d)
    p("  tip1 e8", e8(g)["n"])
    guid, g, prev, d, _, ok = to_tip2(guid, g, prev)
    show("tip2", prev, g, d)
    # A5 fire
    for a_ in (5, 5):
        d = act(guid, a_)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        show("A5", prev, g, d)
    # RESET-less: from spawn re-latch tip1
    guid, g, prev, d, _, ok = tip1_latch(guid, g, prev)
    show("tip1b", prev, g, d)
    out["after_relatch_e8"] = e8(g)["n"]
    # if tip1 latch failed (92), force tip1 again from fresh enter
    if e8(g)["n"] != 76:
        p("  tip1 relatch failed — fresh enter")
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, ok = tip1_latch(guid, g, prev)
        show("tip1fresh", prev, g, d)
    # tip2 again + leave, watch e8
    guid, g, prev, d, _, ok = to_tip2(guid, g, prev)
    show("tip2b", prev, g, d)
    e_on = e8(g)["n"]
    for a_ in (4, 4):
        d = act(guid, a_)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        show("leave", prev, g, d)
    out["persist_after_A5_chain"] = {"on": e_on, "leave": e8(g)["n"], "pos": (prev["cx"], prev["cy"]) if prev else None}
    p("  persist", out["persist_after_A5_chain"])

    # B) tip1 → tip2 hold → try reach snake edge via long way WITHOUT leaving pad?
    # impossible. Instead: tip2 hold, note snake; leave restores; go to snake head cells that were exposed at e60
    # Exposed at e60: ymin=37 — cells (22,34)? still snake at 40. Try approach (28,40)/(16,40)/(22,34) after leave
    p("## post-shrink snake touch (restored map)")
    guid, g, prev = enter_l3()
    guid, g, prev, d, _, _ = tip1_latch(guid, g, prev)
    guid, g, prev, d, _, _ = to_tip2(guid, g, prev)
    show("held", prev, g, d)
    # leave to 28 and try U toward snake
    for a_ in (4, 4, 1, 1, 1, 1, 3, 1, 5, 5):
        d = act(guid, a_)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        show(f"A{a_}", prev, g, d)
        if (d.get("levels_completed") or 0) > 2:
            cleared = True
            break
        if e8(g)["n"] not in (76, 60, 92) and e8(g)["n"] < 76:
            p("  *** new shrink", e8(g)["n"])
    out["snake_touch"] = {"pos": (prev["cx"], prev["cy"]) if prev else None, "e8": einfo(g)}

    # C) Without tip1: can we open right? 
    p("## no tip1 pierce right?")
    guid, g, prev = enter_l3()
    show("spawn", prev, g, d if 'd' in dir() else None)
    guid, g, prev, d, log, ok = play(guid, g, prev, TO_BOTTOM_ONLY)
    path = []
    for r in log:
        if r["pos"] and (not path or path[-1] != r["pos"]):
            path.append(r["pos"])
    show("end", prev, g, d)
    out["no_tip1_bottom"] = {"path": path, "e8": e8(g)["n"], "c11": c11info(g)}
    p("  path", path)

    # D) KEY: buffer land tip2 with A5 pending (from 28)
    p("## land tip2 with A5 armed")
    guid, g, prev = enter_l3()
    guid, g, prev, d, _, _ = tip1_latch(guid, g, prev)
    guid, g, prev, d, _, _ = play(guid, g, prev, TO_BOTTOM_ONLY + [3, 3, 3, 3, 3])
    show("at28", prev, g, d)  # expect ~28,52
    d = act(guid, 5)
    guid = d["guid"]
    g = plane(d)
    prev = actor(g, prev)
    show("armed_land", prev, g, d)
    d = act(guid, 4)  # fire A5 with harmless next?
    guid = d["guid"]
    g = plane(d)
    prev = actor(g, prev)
    show("fire", prev, g, d)
    out["armed_A5"] = {"pos": (prev["cx"], prev["cy"]) if prev else None, "e8": einfo(g), "lv": d.get("levels_completed")}
    if (d.get("levels_completed") or 0) > 2:
        cleared = True
        CLEAR.write_text(json.dumps({"cleared": True, "method": "armed_A5"}, indent=2), encoding="utf-8")

    # E) While e8=60 on tip2: A5 is unlock. What about stepping off onto (22,46) if we first A5-shrink differently?
    # Try visit tip2, then tip1 scar (40,34) via bottom-right-up — e8 will be 76; A5 tip1 again?
    p("## tip2 then re-A5 tip1 scar")
    guid, g, prev = enter_l3()
    guid, g, prev, d, _, _ = tip1_latch(guid, g, prev)
    guid, g, prev, d, _, _ = to_tip2(guid, g, prev)
    show("t2", prev, g, d)
    # to tip1 via bottom: R to 40, U — but U blocked on x40 earlier!
    # via right col: R to 52, U to 34, L to 40
    for a_ in [4] * 6 + [1] * 4 + [3] * 3 + [5, 5]:
        d = act(guid, a_)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        show(f"A{a_}", prev, g, d)
        if (d.get("levels_completed") or 0) > 2:
            cleared = True
            break
    out["re_A5_tip1"] = {"pos": (prev["cx"], prev["cy"]) if prev else None, "e8": einfo(g)}

    # F) climb x16 from tip2 side after leave — snake ymin=32 at e76, (16,34) was reachable; try (16,28)?
    p("## climb x16 deep")
    guid, g, prev = enter_l3()
    guid, g, prev, d, _, _ = tip1_latch(guid, g, prev)
    guid, g, prev, d, _, _ = play(guid, g, prev, TO_BOTTOM_ONLY + [3, 3, 3, 3, 3, 3])  # ~16
    show("x16", prev, g, d)
    for a_ in [1] * 10 + [4] * 4 + [1] * 4 + [4, 3, 1, 1]:
        before = (prev["cx"], prev["cy"])
        d = act(guid, a_)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        if prev and (prev["cx"], prev["cy"]) != before:
            show(f"A{a_}", prev, g, d)
        if (d.get("levels_completed") or 0) > 2:
            cleared = True
            CLEAR.write_text(json.dumps({"cleared": True, "method": "x16"}, indent=2), encoding="utf-8")
            break
    out["x16"] = {"pos": (prev["cx"], prev["cy"]) if prev else None, "e8": einfo(g)}

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_TIP2_ORDER"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
