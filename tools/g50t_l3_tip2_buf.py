"""g50t L3: buffer-precise tip2 on x40 / climb x22 after right-open bottom.

Arrive (40,52) with pending UP via: ... L to (46,52) pending L, then U.
Arrive tip (40,46) with pending A5 via: at (40,52) pending U, send A5.

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

OUT = ROOT / "tests/fixtures/g50t_l3_tip2_buf.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2, 2]


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

    def latch_bottom(guid, g, prev):
        guid, g, prev, d, log, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if ok:
            return guid, g, prev, d, log, True
        guid, g, prev, d, log, ok = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        if ok:
            return guid, g, prev, d, log, True
        return play(guid, g, prev, TO_BOTTOM)

    def path_of(log):
        path = []
        for r in log:
            if r["pos"] and (not path or path[-1] != r["pos"]):
                path.append(r["pos"])
        return path

    def run_seq(name, after, hunt=True):
        nonlocal_cleared = False
        p(f"## {name}")
        guid, g, prev = enter_l3()
        guid, g, prev, d, log1, ok = latch_bottom(guid, g, prev)
        if ok:
            return True, path_of(log1), log1
        show("bottom", prev, g, d)
        log = list(log1)
        for a_ in after:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            rec = {
                "a": a_,
                "pos": (prev["cx"], prev["cy"]) if prev else None,
                "e8": e8(g)["n"],
                "c11": c11info(g),
                "lv": d.get("levels_completed"),
            }
            log.append(rec)
            show(f"A{a_}", prev, g, d)
            if (d.get("levels_completed") or 0) > 2:
                CLEAR.write_text(
                    json.dumps({"cleared": True, "method": name, "log": log}, indent=2, default=str),
                    encoding="utf-8",
                )
                return True, path_of(log), log
        # if shrunk, hunt
        if hunt and prev and e8(g)["n"] <= 70:
            p("  SHRINK — hunt (22,22)")
            for _ in range(48):
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
                    CLEAR.write_text(
                        json.dumps({"cleared": True, "method": name + "+hunt"}, indent=2, default=str),
                        encoding="utf-8",
                    )
                    return True, path_of(log), log
                if prev and (prev["cx"], prev["cy"]) == b:
                    aid2 = (2 if dy > 0 else 1) if abs(dx) >= abs(dy) else (4 if dx > 0 else 3)
                    d = act(guid, aid2)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                    if prev and (prev["cx"], prev["cy"]) == b:
                        break
        return False, path_of(log), log

    out = {}
    cleared = False

    # KEY BUFFER SEQS from (52,52) pending D:
    # L, L, U  → (40,52) pending U
    trials = {
        "tip4046_A5": [3, 3, 1, 5, 5],
        # L,L,U,U → (40,46) pend U; A5 exec U→(40,40) — maybe tip is 40,40
        "tip4040_via_U_A5": [3, 3, 1, 1, 5, 5],
        # L,L,U,U,U → (40,40); A5
        "tip4040_A5": [3, 3, 1, 1, 1, 5, 5],
        # climb x40 fully watching e8
        "climb_x40": [3, 3, 1, 1, 1, 1, 1, 1, 1],
        # to (22,52) pend U: L*5 to (28,52)pend L, then U
        # From 52: L(drain), L→46, L→40, L→34, L→28, U→22 pend U
        "land2252_U": [3, 3, 3, 3, 3, 1],
        "land2252_climb": [3, 3, 3, 3, 3, 1, 1, 1, 1, 1, 1],
        "land2252_A5": [3, 3, 3, 3, 3, 1, 5, 5],
        # (22,46)/(22,40) A5
        "col22_tip_A5": [3, 3, 3, 3, 3, 1, 1, 1, 5, 5],
        # after tip4046 latch attempt, go to goal like L2
        "tip4046_then_up": [3, 3, 1, 5, 5, 1, 1, 1, 3, 3, 1, 1, 4],
    }

    for name, after in trials.items():
        ok, path, log = run_seq(name, after)
        out[name] = {
            "path": path,
            "final": log[-1] if log else None,
            "e8_min": min((r["e8"] for r in log), default=None),
        }
        p("  path", path, "e8_min", out[name]["e8_min"])
        if ok:
            cleared = True
            break

    # Micro: verify land (40,52) pending U then positions
    if not cleared:
        p("## micro4052")
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, _ = latch_bottom(guid, g, prev)
        for a_ in (3, 3, 1):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            show(f"mA{a_}", prev, g, d)
        out["micro4052"] = {"pos": (prev["cx"], prev["cy"]) if prev else None, "e8": e8(g)["n"]}
        # continue U logging each cell + e8
        for a_ in (1, 1, 1, 1, 1, 1):
            before_e = e8(g)["n"]
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            show("climb", prev, g, d)
            if e8(g)["n"] != before_e:
                p("  *** e8 change", before_e, "->", e8(g)["n"])
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                break

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_TIP2_BUF"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
