"""g50t L3 clear hunt: tip2 (22,52) shrink 76→60; A5 latch; route to (22,22).

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

OUT = ROOT / "tests/fixtures/g50t_l3_tip2_clear.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2, 2]
# from bottom pending D: L*5 then U lands (22,52) pend U, e8→60
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]


def p(*a, **k):
    print(*a, **k, flush=True)


def c11info(g):
    ys, xs = np.where(g == 11)
    if len(xs) == 0:
        return {"n": 0}
    return {"n": int(len(xs)), "xmin": int(xs.min()), "xmax": int(xs.max())}


def show(tag, prev, g, d=None):
    p(
        f"  {tag}",
        (prev["cx"], prev["cy"]) if prev else None,
        "e8",
        e8(g)["n"],
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
                    "c11": c11info(g),
                    "lv": d.get("levels_completed"),
                }
            )
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, log, True
        return guid, g, prev, d, log, False

    def setup_tip2(guid, g, prev):
        guid, g, prev, d, log, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if ok:
            return guid, g, prev, d, log, True
        guid, g, prev, d, log, ok = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        if ok:
            return guid, g, prev, d, log, True
        return play(guid, g, prev, TO_TIP2)

    def path_of(log):
        path = []
        for r in log:
            if r["pos"] and (not path or path[-1] != r["pos"]):
                path.append(r["pos"])
        return path

    def hunt(guid, g, prev, steps=60):
        log = []
        for _ in range(steps):
            if not prev:
                break
            cx, cy = prev["cx"], prev["cy"]
            dx, dy = 22 - cx, 22 - cy
            if abs(dx) < 0.1 and abs(dy) < 0.1:
                # on goal — wait / any move
                aid = 4
            else:
                aid = (4 if dx > 0 else 3) if abs(dx) >= abs(dy) else (2 if dy > 0 else 1)
            b = (cx, cy)
            d = act(guid, aid)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            log.append({"a": aid, "pos": (prev["cx"], prev["cy"]) if prev else None, "e8": e8(g)["n"], "lv": d.get("levels_completed")})
            show("h", prev, g, d)
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, log, True
            if prev and (prev["cx"], prev["cy"]) == b:
                aid2 = (2 if dy > 0 else 1) if abs(dx) >= abs(dy) else (4 if dx > 0 else 3)
                for a2 in (aid2, 4, 3, 1, 2):
                    d = act(guid, a2)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                    log.append({"a": a2, "pos": (prev["cx"], prev["cy"]) if prev else None, "e8": e8(g)["n"], "lv": d.get("levels_completed")})
                    show(f"alt{a2}", prev, g, d)
                    if (d.get("levels_completed") or 0) > 2:
                        return guid, g, prev, d, log, True
                    if prev and (prev["cx"], prev["cy"]) != b:
                        break
                else:
                    break
        return guid, g, prev, d, log, False

    out = {}
    cleared = False

    trials = {
        # at tip2 pend U: A5 exec U(noop?), queue A5; next A5 fires on tip
        "A5_on_tip2": [5, 5],
        # leave tip east/west then revisit for persist (L2 style)
        "leave_R_revisit": [4, 4, 3, 3],
        "leave_L_revisit": [3, 3, 4, 4],
        # A5 then leave
        "A5_leave_R": [5, 5, 4, 4, 3, 3],
        "A5_leave_L": [5, 4, 3, 3, 4],
        # drain U with R/L then A5 while standing
        "drain_R_A5": [4, 5, 5],
        "drain_L_A5": [3, 5, 5],
        "drain_D_A5": [2, 5, 5],
        # star dirs from tip2
        "star_U": [1, 1, 1, 1],
        "star_D": [2, 2],
        "star_L": [3, 3, 3, 3],
        "star_R": [4, 4, 4, 4],
        # after shrink without A5, go bottom east then up right then top west to goal (L2-like with e8=60)
        "e60_right_top_loop": [4, 4, 4, 4, 4, 1, 1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 4],
        # west on bottom then up left col
        "e60_left_up": [3, 3, 1, 1, 1, 1, 1, 4, 4],
    }

    for name, after in trials.items():
        p(f"## {name}")
        try:
            guid, g, prev = enter_l3()
            guid, g, prev, d, log, ok = setup_tip2(guid, g, prev)
            show("tip2", prev, g, d)
            if ok:
                cleared = True
                CLEAR.write_text(
                    json.dumps({"cleared": True, "method": "setup_tip2"}, indent=2, default=str),
                    encoding="utf-8",
                )
                break
            e0 = e8(g)["n"]
            for a_ in after:
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                log.append(
                    {
                        "a": a_,
                        "pos": (prev["cx"], prev["cy"]) if prev else None,
                        "e8": e8(g)["n"],
                        "c11": c11info(g),
                        "lv": d.get("levels_completed"),
                    }
                )
                show(f"A{a_}", prev, g, d)
                if (d.get("levels_completed") or 0) > 2:
                    cleared = True
                    break
            out[name] = {
                "path": path_of(log),
                "e8_start": e0,
                "e8_end": e8(g)["n"],
                "final": log[-1] if log else None,
            }
            p("  e8", e0, "->", e8(g)["n"], "path_tail", path_of(log)[-8:])
            if cleared:
                CLEAR.write_text(
                    json.dumps({"cleared": True, "method": name, "log": log}, indent=2, default=str),
                    encoding="utf-8",
                )
                break
            # hunt if e8<=60 or moved off tip
            if e8(g)["n"] <= 60:
                guid, g, prev, d, hlog, ok = hunt(guid, g, prev)
                out[name]["hunt"] = path_of(hlog)
                if ok:
                    cleared = True
                    CLEAR.write_text(
                        json.dumps({"cleared": True, "method": name + "+hunt", "log": log + hlog}, indent=2, default=str),
                        encoding="utf-8",
                    )
                    break
        except Exception as e:
            p("  ERR", e)
            out[name] = {"error": str(e)}

    # Persist check: step on tip2, leave, check e8
    if not cleared:
        p("## persist60")
        guid, g, prev = enter_l3()
        guid, g, prev, d, log, _ = setup_tip2(guid, g, prev)
        show("on", prev, g, d)
        e_on = e8(g)["n"]
        # leave to (28,52): pending U — R exec U noop? use R: exec U (noop at tip), pend R; R→(28,52)
        for a_ in (4, 4):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            show("leave", prev, g, d)
        e_leave = e8(g)["n"]
        # revisit
        for a_ in (3, 3):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            show("back", prev, g, d)
        e_back = e8(g)["n"]
        out["persist60"] = {"on": e_on, "leave": e_leave, "back": e_back, "pos": (prev["cx"], prev["cy"]) if prev else None}
        p("  persist", out["persist60"])

        # A5 latch attempt with correct buffer: at (28,52) pend L toward tip, send A5
        # Re-setup
        guid, g, prev = enter_l3()
        guid, g, prev, d, log, _ = setup_tip2(guid, g, prev)
        # at (22,52) pend U. Move to (28,52) with pend L toward tip:
        # R: exec U noop, pend R → stay; R: exec R → (28,52) pend R. Bad pending.
        # From tip pend U: L? west. 
        # Better: TO_TIP2 ends pend U on tip. Send R (U noop, pend R), R (→28 pend R).
        # From 28 pend R: send L (→22 pend L)? Then A5 from adjacent:
        # At 28: want pend L, send A5: exec L→22, pend A5; next fires A5.
        for a_ in (4, 4, 3, 5, 5):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            show("latchbuf", prev, g, d)
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                break
        out["latchbuf"] = {
            "pos": (prev["cx"], prev["cy"]) if prev else None,
            "e8": e8(g)["n"],
            "lv": d.get("levels_completed"),
        }
        if e8(g)["n"] <= 60 and not cleared:
            guid, g, prev, d, hlog, ok = hunt(guid, g, prev)
            if ok:
                cleared = True
                CLEAR.write_text(
                    json.dumps({"cleared": True, "method": "latchbuf+hunt"}, indent=2, default=str),
                    encoding="utf-8",
                )

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_TIP2_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
