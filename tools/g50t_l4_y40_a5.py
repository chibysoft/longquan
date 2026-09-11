"""g50t L4: after persist36, A5 at y40 corridor cells (L2-analog tip2 hunt).

Watch e8 grow/shrink like L3 tip2 arming. tags=["g50t_recon"]
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

OUT = ROOT / "tests/fixtures/g50t_l4_y40_a5.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]
TIP_A5 = [2, 2, 2, 4, 2, 5, 5]
TIP_LEAVE = [2, 2, 2, 4, 2, 1, 1]
TO_1040 = [3, 3, 1, 1, 3, 3, 3, 2, 2, 2, 2, 2, 2]


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
    trials = []

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
                p(" ", a_, (prev["cx"], prev["cy"]) if prev else None, "e8", e8(g)["n"])
            lv = d.get("levels_completed") or 0
            if stop_lv is not None and lv >= stop_lv:
                return guid, g, prev, d, True, False
            if lv > 3:
                return guid, g, prev, d, True, False
        return guid, g, prev, d, False, False

    def boot_1040():
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
        guid, g, prev, d, ok, dead = play(guid, g, prev, TIP_A5 + TIP_LEAVE, quiet=False)
        guid, g, prev, d, ok, dead = play(guid, g, prev, TO_1040, quiet=False)
        ok = e8(g)["n"] == 36 and (prev["cx"], prev["cy"]) in ((10.0, 40.0), (10, 40))
        p("at1040", ok, (prev["cx"], prev["cy"]), einfo(g), "nact", nact[0])
        return guid, g, prev, d, ok

    # A5 at each of (10,40),(16,40),(22,40),(28,40) — fresh boot each
    targets = [
        ("1040", []),
        ("1640", [4, 4]),  # buffer: first may flush
        ("2240", [4, 4, 4, 4]),
        ("2840", [4, 4, 4, 4, 4, 4]),
    ]

    for name, prep in targets:
        p(f"## A5 @{name}")
        guid, g, prev, d, ok = boot_1040()
        if not ok:
            trials.append({"name": name, "ok": False})
            continue
        # settle at target
        for a_ in prep:
            d = act(guid, a_)
            if "guid" not in d:
                break
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            p("  prep", a_, (prev["cx"], prev["cy"]), "e8", e8(g)["n"])
        # flush: send same dir noop then A5 A5
        before = (prev["cx"], prev["cy"])
        be = e8(g)["n"]
        d = act(guid, 5)
        if "guid" not in d:
            trials.append({"name": name, "fail": True})
            continue
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        p("  A5a", before, "->", (prev["cx"], prev["cy"]), "e8", e8(g)["n"], "de", e8(g)["n"] - be, "lv", d.get("levels_completed"))
        be2 = e8(g)["n"]
        before2 = (prev["cx"], prev["cy"])
        d = act(guid, 5)
        if "guid" not in d:
            # death without guid?
            p("  A5b FAIL", d)
            trials.append({"name": name, "pos": before, "after_a5a": before2, "e8a": be2, "dead": True})
            continue
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        p("  A5b", before2, "->", (prev["cx"], prev["cy"]), "e8", e8(g)["n"], "de", e8(g)["n"] - be2, "lv", d.get("levels_completed"), "einfo", einfo(g))
        trial = {
            "name": name,
            "start": before,
            "e8_before": be,
            "after_a5a": {"pos": before2, "e8": be2},
            "after_a5b": {"pos": (prev["cx"], prev["cy"]), "e8": einfo(g), "lv": d.get("levels_completed")},
        }
        # if e8 changed interestingly or still 36, try tip1 leave / gap push
        if e8(g)["n"] != 52 or (d.get("levels_completed") or 0) > 3:
            p("  *** INTERESTING — try tip revisit / gap")
            for a_ in [2, 2, 2, 4, 2, 1, 1, 3, 3, 1, 1, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2]:
                d = act(guid, a_)
                if "guid" not in d:
                    break
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                p("  +", a_, (prev["cx"], prev["cy"]), "e8", e8(g)["n"], "lv", d.get("levels_completed"))
                if (d.get("levels_completed") or 0) > 3:
                    p("  *** CLEAR")
                    break
            trial["follow"] = {"pos": (prev["cx"], prev["cy"]), "e8": einfo(g), "lv": d.get("levels_completed")}
        trials.append(trial)
        if (d.get("levels_completed") or 0) > 3:
            break

    result = {"trials": trials, "nact": nact[0], "cleared": any((t.get("after_a5b") or {}).get("lv", 0) > 3 for t in trials)}
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    p("READING", result)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
