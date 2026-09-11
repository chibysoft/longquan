"""g50t L4 clear: persist36 → reliable (10,40) → gap/second-tip/goal.

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

OUT = ROOT / "tests/fixtures/g50t_l4_clear_attempt.json"
FRAME = ROOT / "tests/fixtures/g50t_l4_at1040_frame.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]
TIP_A5 = [2, 2, 2, 4, 2, 5, 5]
TIP_LEAVE = [2, 2, 2, 4, 2, 1, 1]
# after persist (34,22) pend U → (10,40)
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
        for a_ in seq:
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, False, True
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if not quiet:
                p(" ", a_, (prev["cx"], prev["cy"]) if prev else None, "e8", e8(g)["n"], "lv", d.get("levels_completed"), "n", nact[0])
            lv = d.get("levels_completed") or 0
            if stop_lv is not None and lv >= stop_lv:
                return guid, g, prev, d, True, False
            if lv > 3:
                return guid, g, prev, d, True, False
        return guid, g, prev, d, False, False

    def boot_l4_persist():
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
        d = act(guid, 4)
        guid, g, prev = d["guid"], plane(d), actor(plane(d), None)
        guid, g, prev, d, ok, dead = play(guid, g, prev, TIP_A5 + TIP_LEAVE, quiet=False)
        ok = e8(g)["n"] == 36
        p("persist", ok, (prev["cx"], prev["cy"]), e8(g)["n"], "nact", nact[0])
        return guid, g, prev, d, ok

    cleared = False
    guid, g, prev, d, ok = boot_l4_persist()
    if not ok:
        OUT.write_text(json.dumps({"cleared": False, "reason": "persist"}, indent=2), encoding="utf-8")
        return

    guid, g, prev, d, ok, dead = play(guid, g, prev, TO_1040, quiet=False)
    p("at1040?", (prev["cx"], prev["cy"]), e8(g)["n"])
    FRAME.write_text(
        json.dumps({"frame": d.get("frame"), "pos": (prev["cx"], prev["cy"]), "e8": einfo(g)}, default=str),
        encoding="utf-8",
    )

    # analyze y46 in this frame
    gg = plane(d)
    for x in range(4, 58, 6):
        sub = gg[44:49, x - 2 : x + 3]
        n5 = int((sub == 5).sum())
        n0 = int((sub == 0).sum())
        if n5 >= 15:
            p("  walkish y46", x, "n5", n5, "n0", n0)

    # From (10,40): east along corridor, probe D each column; also back to y28 for tip2
    phases = [
        ("east_probe_D", [4, 2, 4, 2, 4, 2, 4, 2, 1, 2]),
        ("back_y28_R_tip", [1, 1, 4, 4, 4, 4, 5, 5]),  # up to 28 then R — careful no unlock A5 off tip
        ("R_on_y28", [1, 1, 4, 4, 2, 4, 2, 3]),  # step on snake cells
    ]

    # phase 1 inline
    path = [(prev["cx"], prev["cy"])]
    for a_ in phases[0][1]:
        be = e8(g)["n"]
        d = act(guid, a_)
        if "guid" not in d:
            break
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        pos = (prev["cx"], prev["cy"])
        if path[-1] != pos:
            path.append(pos)
        p("  p1", a_, pos, "e8", e8(g)["n"], "de", e8(g)["n"] - be, "lv", d.get("levels_completed"))
        if (d.get("levels_completed") or 0) > 3:
            cleared = True
            break

    if not cleared:
        # step on left snake from (10,28): go U to 28 if at 40, R
        p("## tip2 hunt on y28")
        # get to (10,28)
        for a_ in [1, 1, 4, 4, 4, 2, 2]:  # adjust live
            be = e8(g)["n"]
            before = (prev["cx"], prev["cy"])
            d = act(guid, a_)
            if "guid" not in d:
                break
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            p("  t2", a_, (prev["cx"], prev["cy"]), "e8", e8(g)["n"], "de", e8(g)["n"] - be, "lv", d.get("levels_completed"))
            if e8(g)["n"] < 36:
                p("  *** SECOND SHRINK", e8(g)["n"], einfo(g))
                # leave and check persist; try goal again
                for a2 in [1, 1, 3, 2, 2, 2, 2, 2]:
                    d = act(guid, a2)
                    if "guid" not in d:
                        break
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                    p("  aft", a2, (prev["cx"], prev["cy"]), "e8", e8(g)["n"], "lv", d.get("levels_completed"))
                    if (d.get("levels_completed") or 0) > 3:
                        cleared = True
                        break
                break
            if (d.get("levels_completed") or 0) > 3:
                cleared = True
                break

    # Fresh: direct clear attempt with best-known path + R from 1040 to 2840 then try D
    if not cleared:
        p("## fresh goal push")
        guid, g, prev, d, ok = boot_l4_persist()
        if ok:
            seq = TO_1040 + [4, 4, 4, 2, 4, 2, 1, 1, 2, 2, 2, 3, 3, 2]
            for a_ in seq:
                d = act(guid, a_)
                if "guid" not in d:
                    p("  fail", {k: d.get(k) for k in d if k != "frame"})
                    break
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                p(" ", a_, (prev["cx"], prev["cy"]), "e8", e8(g)["n"], "lv", d.get("levels_completed"))
                if (d.get("levels_completed") or 0) > 3:
                    cleared = True
                    break

    result = {
        "cleared": cleared,
        "levels_completed": d.get("levels_completed") if d else None,
        "final_pos": (prev["cx"], prev["cy"]) if prev else None,
        "final_e8": einfo(g) if prev else None,
        "path": path,
        "nact": nact[0],
        "reading": "L4_CLEAR" if cleared else "L4_1040_PARTIAL",
    }
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    p("READING", result["reading"], result["final_pos"], result["final_e8"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
