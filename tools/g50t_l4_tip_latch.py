"""g50t L4 clear: tip (34,28) 52→36; A5 latch; left col to ~(10,52).

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
LOG = ROOT / "tests/fixtures/g50t_l4_tip_latch.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]
# land tip with A5 armed: D to y22, R, A5(exec R→34,22), A5(exec D→34,28 + fire?)
# Better: [2,2,2,4,2] land tip pend D; then need A5 on tip.
# Buffer A5 onto tip: at (34,22) pend D send A5 → land tip pend A5 → fire
TO_TIP = [2, 2, 2, 4, 5]  # careful trace below


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
    out = {"cleared": False}

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
        log = []
        for a_ in seq:
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, log, False, True
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
            p(" ", a_, log[-1]["pos"], "e8", log[-1]["e8"], "lv", log[-1]["lv"], "n", nact[0])
            lv = d.get("levels_completed") or 0
            if stop_lv is not None and lv >= stop_lv:
                return guid, g, prev, d, log, True, False
            if lv > 3:
                return guid, g, prev, d, log, True, False
        return guid, g, prev, d, log, False, False

    def enter_l4():
        d = reset()
        nact[0] = 0
        guid = d["guid"]
        g = plane(d)
        prev = None
        guid, g, prev, d, log, ok, dead = play(guid, g, prev, L1_SEQ + [2] * 4 + [4] * 8, stop_lv=1)
        d = act(guid, 3)
        guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)
        guid, g, prev, d, log, ok, dead = play(guid, g, prev, TO_2840 + L2_ROUTE, stop_lv=2)
        d = act(guid, 3)
        guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)
        guid, g, prev, d, log, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if not ok and not dead:
            guid, g, prev, d, log, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        guid, g, prev, d, log, ok, dead = play(guid, g, prev, TO_TIP2 + [5, 5])
        if (d.get("levels_completed") or 0) < 3 and not dead:
            guid, g, prev, d, log, ok, dead = play(guid, g, prev, TIP1_LEAVE)
            guid, g, prev, d, log, ok, dead = play(guid, g, prev, L3_WEST_CLEAR, stop_lv=3)
        if (d.get("levels_completed") or 0) < 3 or "guid" not in d:
            return None, None, None, d, False
        d = act(guid, 4)
        if "guid" not in d:
            return None, None, None, d, False
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, None)
        p("L4", (prev["cx"], prev["cy"]), "e8", e8(g)["n"], "nact", nact[0])
        return guid, g, prev, d, True

    # --- A: hold tip leave (no A5) ---
    p("## hold leave")
    guid, g, prev, d, ok = enter_l4()
    # [2,2,2,4,2] → (34,28) e8=36
    guid, g, prev, d, log, ok, dead = play(guid, g, prev, [2, 2, 2, 4, 2])
    p("on tip", (prev["cx"], prev["cy"]), e8(g)["n"])
    # leave U then check e8
    guid, g, prev, d, log2, ok, dead = play(guid, g, prev, [1, 1])
    out["hold_leave"] = {"on": 36, "after": e8(g)["n"], "pos": (prev["cx"], prev["cy"]) if prev else None}
    p("  leave e8", e8(g)["n"])

    # --- B: A5 on tip (standing) then revisit leave ---
    p("## A5 then revisit leave")
    guid, g, prev, d, ok = enter_l4()
    # land tip, A5 fire
    guid, g, prev, d, log, ok, dead = play(guid, g, prev, [2, 2, 2, 4, 2, 5, 5])
    p("after A5", (prev["cx"], prev["cy"]) if prev else None, e8(g)["n"])
    # revisit tip and leave (L3 tip1 style)
    guid, g, prev, d, log, ok, dead = play(guid, g, prev, [2, 2, 2, 4, 2, 1, 1])
    e_leave = e8(g)["n"]
    out["A5_revisit"] = {"e_leave": e_leave, "pos": (prev["cx"], prev["cy"]) if prev else None, "einfo": einfo(g)}
    p("  revisit leave e8", e_leave, einfo(g))

    cleared = False
    if e_leave <= 36:
        p("## persist — left goal hunt")
        # from ~ (34,22) after leave U: go west top / left col down to (10,52)
        # snake xmin should be >10 if persist
        for a_ in [3, 3, 3, 3, 1, 1, 3, 2, 2, 2, 2, 2, 2, 2, 2, 3, 2, 2]:
            d = act(guid, a_)
            if "guid" not in d:
                break
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            p("  h", a_, (prev["cx"], prev["cy"]), "e8", e8(g)["n"], "lv", d.get("levels_completed"))
            if (d.get("levels_completed") or 0) > 3:
                cleared = True
                break
        out["hunt"] = {"pos": (prev["cx"], prev["cy"]) if prev else None, "e8": einfo(g), "lv": d.get("levels_completed")}

    # --- C: buffer A5 onto tip then leave without second death ---
    if not cleared:
        p("## buffer A5 onto tip + leave U")
        guid, g, prev, d, ok = enter_l4()
        # at (28,22) pend D: R → stay? Trace proven: [2,2,2,4,2] lands tip
        # For A5 on land: [2,2,2,4,5] — at (28,22) pend D, A4 exec D noop pend R, A5 exec R→(34,22) pend A5
        # Need one more D before A5 fire: [2,2,2,4,2,5]
        # Or: [2,2,2,4,5,2,5] messy
        # Proven land then A5: [2,2,2,4,2,5] — first A5 drains pend D (noop), queues A5; need second A5 to fire while ON tip
        guid, g, prev, d, log, ok, dead = play(guid, g, prev, [2, 2, 2, 4, 2, 5])
        p("armed?", (prev["cx"], prev["cy"]), e8(g)["n"])
        # fire A5 while on tip
        d = act(guid, 1)  # fire A5 with U next? or 5 again
        if "guid" in d:
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            p("  fire via U", (prev["cx"], prev["cy"]) if prev else None, e8(g)["n"], "lv", d.get("levels_completed"))
        # if died, revisit
        if e8(g)["n"] == 52 and prev and prev["cy"] < 20:
            guid, g, prev, d, log, ok, dead = play(guid, g, prev, [2, 2, 2, 4, 2, 1, 3, 3, 3, 2, 2, 2, 2, 2, 2])
            p("  after revisit path", (prev["cx"], prev["cy"]), e8(g)["n"], "lv", d.get("levels_completed"))
            if (d.get("levels_completed") or 0) > 3:
                cleared = True
            out["bufA5"] = {"e8": einfo(g), "pos": (prev["cx"], prev["cy"]) if prev else None, "lv": d.get("levels_completed")}

    # --- D: hold tip e8=36, can we U-L to left while... no. 
    # While on tip, does (10,28) open in frame? dump
    if not cleared:
        p("## dump hold tip frame + try leave L toward goal corridor")
        guid, g, prev, d, ok = enter_l4()
        guid, g, prev, d, log, ok, dead = play(guid, g, prev, [2, 2, 2, 4, 2])
        g = plane(d)
        # check (10,28) and (16,28)
        cells = {}
        for x, y in [(10, 28), (16, 28), (22, 28), (28, 28), (10, 34), (10, 40), (10, 52)]:
            sub = g[y - 2 : y + 3, x - 2 : x + 3]
            cells[(x, y)] = {
                "c": int(g[y, x]),
                "n8": int((sub == 8).sum()),
                "n0": int((sub == 0).sum()),
                "n5": int((sub == 5).sum()),
            }
        out["hold_cells"] = {str(k): v for k, v in cells.items()}
        p("  cells", cells)
        # leave L: may go to (28,28)? tip is (34,28), L→(28,28) still snake?
        for a_ in [3, 3, 3, 3, 1, 1, 3, 2, 2, 2, 2]:
            before_e = e8(g)["n"]
            d = act(guid, a_)
            if "guid" not in d:
                break
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            p("  L", a_, (prev["cx"], prev["cy"]), "e8", e8(g)["n"], "de", e8(g)["n"] - before_e, "lv", d.get("levels_completed"))
            if (d.get("levels_completed") or 0) > 3:
                cleared = True
                break
        out["hold_leave_L"] = {"pos": (prev["cx"], prev["cy"]) if prev else None, "e8": einfo(g)}

    out["cleared"] = cleared
    out["nact"] = nact[0]
    out["reading"] = "L4_CLEAR" if cleared else "L4_LATCH_PARTIAL"
    payload = out
    if cleared:
        payload = {
            "cleared": True,
            "levels_completed": 4,
            "method": "tip3428_latch",
            "nact": nact[0],
            **{k: out[k] for k in out if k not in ("cleared", "reading")},
        }
    OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    LOG.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
