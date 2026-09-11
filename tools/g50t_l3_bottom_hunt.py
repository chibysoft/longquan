"""g50t L3: bottom corridor after right-open — tip2 / (22,52) / up to goal.

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

OUT = ROOT / "tests/fixtures/g50t_l3_bottom_hunt.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
# latch @3434 → pierce → top east → right col to (52,52)
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2, 2]


def p(*a, **k):
    print(*a, **k, flush=True)


def c11info(g):
    ys, xs = np.where(g == 11)
    if len(xs) == 0:
        return {"n": 0}
    return {
        "n": int(len(xs)),
        "xmin": int(xs.min()),
        "xmax": int(xs.max()),
    }


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

    def play(guid, g, prev, seq, tag=""):
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
            if tag:
                show(f"{tag}A{a_}", prev, g, d)
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, log, True
        return guid, g, prev, d, log, False

    def latch(guid, g, prev):
        guid, g, prev, d, log, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if ok:
            return guid, g, prev, d, log, True
        return play(guid, g, prev, TO_3434 + [4, 4, 3, 3])

    def to_bottom(guid, g, prev):
        return play(guid, g, prev, TO_BOTTOM)

    def settle_move(guid, g, prev, aid):
        """Issue aid twice so buffer executes exactly one intended step from unknown pending.
        Returns after second tap; caller should check pos.
        Better: drain by repeating until move or 3 taps, then one more opposite? 
        Simple: aid, aid and report.
        """
        before = (prev["cx"], prev["cy"]) if prev else None
        d = None
        for _ in range(2):
            d = act(guid, aid)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, True
        return guid, g, prev, d, False

    def step_until(guid, g, prev, aid, target, max_taps=8):
        """Keep tapping aid until pos==target or stuck."""
        for i in range(max_taps):
            before = (prev["cx"], prev["cy"])
            d = act(guid, aid)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            show(f"tap{aid}", prev, g, d)
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, True
            if prev and (int(round(prev["cx"])), int(round(prev["cy"]))) == target:
                # one more same to drain pending into wall/hold? NO — leave pending.
                return guid, g, prev, d, False
            if prev and (prev["cx"], prev["cy"]) == before and i > 0:
                return guid, g, prev, d, False
        return guid, g, prev, d, False

    def path_of(log):
        path = []
        for r in log:
            if r["pos"] and (not path or path[-1] != r["pos"]):
                path.append(r["pos"])
        return path

    out = {"cleared": False}
    cleared = False

    trials = {
        # west along bottom to x40, then up (tip2 40,46 / 40,40)
        "bot_W40_U": {
            "after": [3, 3, 3, 1, 1, 1, 1, 1, 5, 5],
            "note": "to ~40,52 then up + A5",
        },
        "bot_W40_U_hold": {
            "after": [3, 3, 1, 1, 1, 1, 1, 1, 1],
            "note": "up column x40",
        },
        # carefully to (22,52)
        "bot_to_2252": {
            "after": [3, 3, 3, 3, 3, 4],  # overshoot then correct?
            "note": "west bottom",
        },
        "bot_W_U22": {
            "after": [3, 3, 3, 3, 3, 1, 1, 1, 1, 1, 1],
            "note": "west then up leftish",
        },
        # tip2 A5 at 40,46
        "tip_4046_A5": {
            "after": [3, 3, 1, 1, 5, 5],
            "note": "(40,52)->(40,46) A5",
        },
        "tip_4040_A5": {
            "after": [3, 3, 1, 1, 1, 1, 5, 5],
            "note": "(40,52)->(40,40) A5",
        },
        # L2-like confirm after tip?
        "tip_4046_then_goal": {
            "after": [3, 3, 1, 1, 5, 5, 2, 2, 3, 3, 3, 1, 1, 1, 1, 4],
            "note": "A5 then navigate",
        },
    }

    # First: precise navigate script with settle
    p("## precise bottom west + up")
    guid, g, prev = enter_l3()
    guid, g, prev, d, _, ok = latch(guid, g, prev)
    if ok:
        cleared = True
    else:
        guid, g, prev, d, log, ok = to_bottom(guid, g, prev)
        show("bottom", prev, g, d)
        out["to_bottom_path"] = path_of(log)
        if ok:
            cleared = True
        else:
            # pending is D after last downs — drain with L intent:
            # want (40,52): from (52,52) need L twice (52→46→40)
            # Sequence: L (exec pending D noop at bottom?), ...
            for label, seq in [
                ("to4052", [3, 3, 3]),
                ("up4046", [1, 1]),
                ("up4040", [1, 1]),
                ("up4034", [1, 1]),
            ]:
                before = (prev["cx"], prev["cy"])
                for a_ in seq:
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                    show(label, prev, g, d)
                    if (d.get("levels_completed") or 0) > 2:
                        cleared = True
                        break
                if cleared:
                    break
                out[label] = {
                    "from": before,
                    "to": (prev["cx"], prev["cy"]) if prev else None,
                    "e8": e8(g)["n"],
                    "c11": c11info(g),
                }
            if not cleared and prev:
                # try A5 here (maybe on tip)
                cx, cy = int(round(prev["cx"])), int(round(prev["cy"]))
                p(f"  try A5 at {(cx, cy)}")
                for a_ in (5, 5):
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                    show("A5", prev, g, d)
                    if (d.get("levels_completed") or 0) > 2:
                        cleared = True
                        break
                out["A5_at"] = {"pos": (cx, cy), "after": (prev["cx"], prev["cy"]) if prev else None, "e8": e8(g)["n"]}

    if cleared:
        CLEAR.write_text(
            json.dumps({"cleared": True, "method": "precise_bottom"}, indent=2, default=str),
            encoding="utf-8",
        )
    else:
        # scripted trials
        for name, spec in trials.items():
            p(f"## {name}")
            try:
                guid, g, prev = enter_l3()
                guid, g, prev, d, _, ok = latch(guid, g, prev)
                if ok:
                    cleared = True
                    break
                seq = TO_BOTTOM + spec["after"]
                guid, g, prev, d, log, ok = play(guid, g, prev, seq)
                path = path_of(log)
                p("  path", path)
                show("final", prev, g, d)
                out[name] = {"path": path, "final": log[-1] if log else None, "note": spec["note"]}
                if ok:
                    cleared = True
                    CLEAR.write_text(
                        json.dumps({"cleared": True, "method": name, "path": path, "log": log}, indent=2, default=str),
                        encoding="utf-8",
                    )
                    break
                # if e8 dropped, hunt goal
                if e8(g)["n"] < 76:
                    p("  e8 dropped — hunt goal")
                    for _ in range(40):
                        cx, cy = prev["cx"], prev["cy"]
                        dx, dy = 22 - cx, 22 - cy
                        aid = (4 if dx > 0 else 3) if abs(dx) >= abs(dy) else (2 if dy > 0 else 1)
                        b = (cx, cy)
                        d = act(guid, aid)
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
                            # try other axis once
                            aid2 = (2 if dy > 0 else 1) if abs(dx) >= abs(dy) else (4 if dx > 0 else 3)
                            d = act(guid, aid2)
                            guid = d["guid"]
                            g = plane(d)
                            prev = actor(g, prev)
                            if prev and (prev["cx"], prev["cy"]) == b:
                                break
                    if cleared:
                        break
            except Exception as e:
                p("  ERR", e)
                out[name] = {"error": str(e)}
                # re-open game context via next trial's enter_l3
                continue

    # Dedicated: land exactly (22,52) then climb
    if not cleared:
        p("## land2252_climb")
        try:
            guid, g, prev = enter_l3()
            guid, g, prev, d, _, _ = latch(guid, g, prev)
            guid, g, prev, d, log, ok = to_bottom(guid, g, prev)
            if ok:
                cleared = True
            else:
                # From (52,52) with pending D: L taps
                # Target x=22: need (52-22)/6 = 5 lefts of movement
                # Buffer: first L may exec pending D (noop), then L*5
                for a_ in [3] * 8:
                    before = (prev["cx"], prev["cy"])
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                    show("W", prev, g, d)
                    if (d.get("levels_completed") or 0) > 2:
                        cleared = True
                        break
                    if prev and int(round(prev["cx"])) == 22 and int(round(prev["cy"])) == 52:
                        p("  HIT 2252")
                        break
                out["land2252"] = {"pos": (prev["cx"], prev["cy"]) if prev else None, "e8": e8(g)["n"]}
                if not cleared and prev and int(round(prev["cx"])) == 22:
                    # climb toward (22,22)/(22,28)
                    for a_ in [1] * 10:
                        d = act(guid, a_)
                        guid = d["guid"]
                        g = plane(d)
                        prev = actor(g, prev)
                        show("U22", prev, g, d)
                        if (d.get("levels_completed") or 0) > 2:
                            cleared = True
                            CLEAR.write_text(
                                json.dumps({"cleared": True, "method": "land2252_climb"}, indent=2, default=str),
                                encoding="utf-8",
                            )
                            break
                    # A5 if on snake
                    if not cleared:
                        for a_ in (5, 5):
                            d = act(guid, a_)
                            guid = d["guid"]
                            g = plane(d)
                            prev = actor(g, prev)
                            show("A5col22", prev, g, d)
                            if (d.get("levels_completed") or 0) > 2:
                                cleared = True
                                break
                elif not cleared and prev:
                    # try (28,52) U and (16,52) U / R to 22
                    cx = int(round(prev["cx"]))
                    if cx in (16, 28, 34, 40):
                        for a_ in [1] * 8 + [4, 4, 3, 3, 1, 1]:
                            d = act(guid, a_)
                            guid = d["guid"]
                            g = plane(d)
                            prev = actor(g, prev)
                            show("alt", prev, g, d)
                            if (d.get("levels_completed") or 0) > 2:
                                cleared = True
                                CLEAR.write_text(
                                    json.dumps({"cleared": True, "method": "alt_climb"}, indent=2, default=str),
                                    encoding="utf-8",
                                )
                                break
        except Exception as e:
            p("  ERR", e)
            out["land2252_err"] = str(e)

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_BOTTOM_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    try:
        s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)
    except Exception:
        pass


if __name__ == "__main__":
    main()
