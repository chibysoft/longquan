"""g50t L4: test if c15 drop at (52,28) persists after leave (true pierce vs occlusion).

Also try chaining visits to eat c15 / open path. tags=["g50t_recon"]
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

OUT = ROOT / "tests/fixtures/g50t_l4_c15_persist_test.json"
FRAME = ROOT / "tests/fixtures/g50t_l4_c15_after_leave.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]
TIP_A5 = [2, 2, 2, 4, 2, 5, 5]
TIP_LEAVE = [2, 2, 2, 4, 2, 1, 1]
TO_5228 = [4, 4, 1, 1, 4, 4, 2, 2, 2, 2]


def p(*a, **k):
    print(*a, **k, flush=True)


def einfo(g):
    e = dict(e8(g))
    ys, xs = np.where(g == 8)
    if len(xs):
        e.update(xmin=int(xs.min()), xmax=int(xs.max()), ymin=int(ys.min()), ymax=int(ys.max()))
    return e


def c15n(g):
    return int((g == 15).sum())


def c15_bbox(g):
    ys, xs = np.where(g == 15)
    if not len(xs):
        return None
    return {
        "n": int(len(xs)),
        "xmin": int(xs.min()),
        "xmax": int(xs.max()),
        "ymin": int(ys.min()),
        "ymax": int(ys.max()),
    }


def walk_grid(g):
    rows = {}
    for y in (22, 28, 34, 40, 46, 52):
        cells = []
        for x in (28, 34, 40, 46, 52):
            sub = g[max(0, y - 2) : y + 3, max(0, x - 2) : x + 3]
            n5 = int((sub == 5).sum())
            n15 = int((sub == 15).sum())
            tag = "W" if n5 >= 12 else ("w" if n5 >= 8 else ".")
            if n15 >= 5:
                tag += "C"
            cells.append(f"{x}:{n5:02d}/{n15:02d}{tag}")
        rows[y] = " ".join(cells)
    return rows


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
    events = []

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

    def boot_persist():
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
        ok = e8(g)["n"] == 36
        p("persist", ok, (prev["cx"], prev["cy"]), "c15", c15n(g))
        return guid, g, prev, d, ok

    def note(label, g, prev):
        rec = {
            "label": label,
            "pos": (prev["cx"], prev["cy"]),
            "c15": c15_bbox(g),
            "e8": einfo(g),
            "grid": walk_grid(g),
        }
        events.append(rec)
        p("NOTE", label, "pos", rec["pos"], "c15", rec["c15"], "y28", rec["grid"][28], "y34", rec["grid"][34], "y40", rec["grid"][40])
        return rec

    guid, g, prev, d, ok = boot_persist()
    if not ok:
        return
    note("persist_at3422", g, prev)

    # go to 5228 watching c15 each step
    for a_ in TO_5228:
        bc = c15n(g)
        before = (prev["cx"], prev["cy"])
        d = act(guid, a_)
        if "guid" not in d:
            break
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        dc = c15n(g) - bc
        p(" ", a_, before, "->", (prev["cx"], prev["cy"]), "c15", c15n(g), "dc", dc)
        if dc:
            note(f"step_dc{dc}", g, prev)

    note("on_5228", g, prev)
    FRAME.write_text(
        json.dumps({"frame": d.get("frame"), "pos": (prev["cx"], prev["cy"]), "c15": c15_bbox(g)}, default=str),
        encoding="utf-8",
    )

    # leave UP to (52,22)/(52,16) and check c15 restore
    for a_ in [1, 1, 1, 1]:
        bc = c15n(g)
        before = (prev["cx"], prev["cy"])
        d = act(guid, a_)
        if "guid" not in d:
            break
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        dc = c15n(g) - bc
        p(" leave", a_, before, "->", (prev["cx"], prev["cy"]), "c15", c15n(g), "dc", dc)
        note(f"leave_{a_}", g, prev)

    # re-enter 5228, try L into denser c15 while watching floor open
    for a_ in [2, 2, 2, 3, 3, 2, 3, 2, 3, 2, 2, 2, 2]:
        bc = c15n(g)
        before = (prev["cx"], prev["cy"])
        be = e8(g)["n"]
        d = act(guid, a_)
        if "guid" not in d:
            break
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        pos = (prev["cx"], prev["cy"])
        p(" dig", a_, before, "->", pos, "c15", c15n(g), "dc", c15n(g) - bc, "e8", e8(g)["n"], "de", e8(g)["n"] - be, "lv", d.get("levels_completed"))
        if pos != before or c15n(g) != bc + (0 if pos == before else 0):
            if abs(c15n(g) - bc) > 5 or pos[1] >= 34:
                note(f"dig_{a_}", g, prev)
        if (d.get("levels_completed") or 0) > 3:
            p("*** CLEAR")
            break

    # If occlusion-only: try eating by repeated step on adjacent c15 cells from y40 left?
    # After leave back to top, go (10,40) and check if anything changed
    result = {
        "events": events,
        "final_pos": (prev["cx"], prev["cy"]),
        "final_c15": c15_bbox(g),
        "lv": d.get("levels_completed"),
        "nact": nact[0],
        "occlusion_only": None,
    }
    # occlusion if leave restored to ~120
    leave_c15 = [e["c15"]["n"] for e in events if e["label"].startswith("leave_") and e["c15"]]
    on_c15 = next((e["c15"]["n"] for e in events if e["label"] == "on_5228"), None)
    if leave_c15 and on_c15:
        result["occlusion_only"] = leave_c15[-1] >= 118 and on_c15 <= 115
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    p("READING", {k: result[k] for k in result if k != "events"}, "leave_c15", leave_c15, "on", on_c15)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
