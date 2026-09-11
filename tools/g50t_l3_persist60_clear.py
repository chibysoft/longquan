"""g50t L3: tip2 A5 arms tip2; tip1 re-leave reasserts tip1; tip2 leave may persist 60; then clear.

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

OUT = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
# tip1 re-leave without A5
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
# left climb clear from bottom after persist60
CLEAR_SEQ = TO_BOTTOM + [3, 3, 3, 3, 3, 3, 3, 1, 1, 1, 1, 4, 4, 1, 1, 1]


def p(*a, **k):
    print(*a, **k, flush=True)


def einfo(g):
    e = dict(e8(g))
    ys, xs = np.where(g == 8)
    if len(xs):
        e.update(xmin=int(xs.min()), xmax=int(xs.max()), ymin=int(ys.min()), ymax=int(ys.max()))
    return e


def show(tag, prev, g, d=None):
    p(
        f"  {tag}",
        (prev["cx"], prev["cy"]) if prev else None,
        "e8",
        einfo(g),
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

    def tip1_latch(guid, g, prev):
        guid, g, prev, d, log, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if ok:
            return guid, g, prev, d, log, True
        return play(guid, g, prev, TO_3434 + [4, 4, 3, 3])

    def path_of(log):
        path = []
        for r in log:
            if r["pos"] and (not path or path[-1] != r["pos"]):
                path.append(r["pos"])
        return path

    out = {"cleared": False}

    p("## chain: tip1 latch -> tip2 A5 -> tip1 leave -> tip2 leave")
    guid, g, prev = enter_l3()
    guid, g, prev, d, log, ok = tip1_latch(guid, g, prev)
    show("tip1", prev, g, d)
    assert e8(g)["n"] == 76

    guid, g, prev, d, log, ok = play(guid, g, prev, TO_TIP2)
    show("tip2", prev, g, d)
    assert e8(g)["n"] == 60
    for a_ in (5, 5):
        d = act(guid, a_)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        show("A5", prev, g, d)

    guid, g, prev, d, log, ok = play(guid, g, prev, TIP1_LEAVE)
    show("tip1_releave", prev, g, d)
    e_mid = e8(g)["n"]
    p("  after tip1 releave e8", e_mid)

    guid, g, prev, d, log, ok = play(guid, g, prev, TO_TIP2)
    show("tip2_again", prev, g, d)
    e_on = e8(g)["n"]
    # leave tip2
    for a_ in (4, 4):
        d = act(guid, a_)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        show("leave2", prev, g, d)
    e_leave = e8(g)["n"]
    p("  tip2 on", e_on, "leave", e_leave)
    out["chain"] = {"tip1_releave": e_mid, "tip2_on": e_on, "tip2_leave": e_leave}

    cleared = False
    if e_leave == 60 or e_on == 60 and e_leave == 60:
        p("  *** PERSIST 60")
    if e_leave <= 60:
        p("## clear climb")
        # from ~28,52 go left up to goal
        # careful buffer to (16,34) then R to (22,34) then U
        for a_ in [3, 3, 3, 1, 1, 1, 1, 4, 1, 1, 1, 4, 4]:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            show(f"cA{a_}", prev, g, d)
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                break
        out["climb_pos"] = (prev["cx"], prev["cy"]) if prev else None
        out["climb_e8"] = einfo(g)
        out["lv"] = d.get("levels_completed")

    # Variant: tip2 A5 -> tip1 leave -> tip2 leave with L toward clear path
    if not cleared:
        p("## chain2: after persist check, full clear seq from scratch")
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, _ = tip1_latch(guid, g, prev)
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_TIP2 + [5, 5])
        show("afterA5", prev, g, d)
        guid, g, prev, d, _, _ = play(guid, g, prev, TIP1_LEAVE)
        show("re76", prev, g, d)
        guid, g, prev, d, log, ok = play(guid, g, prev, TO_TIP2 + [4, 4])
        show("after_tip2_leave", prev, g, d)
        e_leave = e8(g)["n"]
        out["chain2_leave"] = e_leave
        p("  leave e8", e_leave)
        if e_leave == 60:
            # clear: west to x10/16, up to y34, east to 22, up to 22
            guid, g, prev, d, log, ok = play(
                guid,
                g,
                prev,
                [3, 3, 3, 3, 1, 1, 1, 1, 4, 4, 1, 1, 1],
            )
            path = path_of(log)
            show("clear_end", prev, g, d)
            out["clear_path"] = path
            p("  clear path", path)
            if ok or (d.get("levels_completed") or 0) > 2:
                cleared = True
            # if at (22,34) or (22,28) continue
            if not cleared and prev:
                for a_ in [1, 1, 1, 4, 3, 1, 1]:
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                    show("fin", prev, g, d)
                    if (d.get("levels_completed") or 0) > 2:
                        cleared = True
                        break

    # Variant3: tip2 A5 -> tip1 leave -> go LEFT climb WITHOUT second tip2
    # (maybe tip2 A5 alone + tip1 confirm persists 60 even without re-touch tip2)
    if not cleared:
        p("## chain3: tip2 A5 + tip1 leave, check e8 then left without re-tip2")
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, _ = tip1_latch(guid, g, prev)
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_TIP2 + [5, 5])
        guid, g, prev, d, _, _ = play(guid, g, prev, TIP1_LEAVE)
        show("mid", prev, g, d)
        e_mid = e8(g)["n"]
        # open bottom and left climb — if e8 somehow allows (22,34)
        guid, g, prev, d, log, ok = play(guid, g, prev, CLEAR_SEQ)
        path = path_of(log)
        show("end", prev, g, d)
        out["chain3"] = {"e_mid": e_mid, "e_end": e8(g)["n"], "path": path, "ymin": einfo(g).get("ymin")}
        p("  path", path, "e8", e8(g)["n"], "ymin", einfo(g).get("ymin"))
        if ok or (d.get("levels_completed") or 0) > 2:
            cleared = True
        # try R into (22,34) from wherever
        if not cleared and prev and prev["cy"] <= 34:
            for a_ in [4, 4, 1, 1, 1]:
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                show("push", prev, g, d)
                if (d.get("levels_completed") or 0) > 2:
                    cleared = True
                    break

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_PERSIST_CHAIN"
    if cleared:
        out["levels"] = 3
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
