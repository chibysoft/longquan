"""g50t L4 short probes:
  1) persist36 → y40 cells → flush buffer → pure D → y46?
  2) visit (52,28) → scan color2 tip markers
  3) c15 boundary cells: enter/leave — real pierce = c15 stays down after leave
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

OUT = ROOT / "tests/fixtures/g50t_l4_short_probe.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]
TIP_A5 = [2, 2, 2, 4, 2, 5, 5]
TIP_LEAVE = [2, 2, 2, 4, 2, 1, 1]
TO_1040 = [3, 3, 1, 1, 3, 3, 3, 2, 2, 2, 2, 2, 2]
TO_5228 = [4, 4, 1, 1, 4, 4, 2, 2, 2, 2, 2, 2]


def p(*a, **k):
    print(*a, **k, flush=True)


def c15n(g):
    return int((g == 15).sum())


def c2comps(g):
    mask = g == 2
    vis = np.zeros_like(mask)
    out = []
    for y in range(64):
        for x in range(64):
            if not mask[y, x] or vis[y, x]:
                continue
            pts = [(y, x)]
            vis[y, x] = True
            i = 0
            while i < len(pts):
                cy, cx = pts[i]
                i += 1
                for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < 64 and 0 <= nx < 64 and mask[ny, nx] and not vis[ny, nx]:
                        vis[ny, nx] = True
                        pts.append((ny, nx))
            out.append((len(pts), round(float(np.mean([q[1] for q in pts])), 1), round(float(np.mean([q[0] for q in pts])), 1)))
    return sorted(out, reverse=True)


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
    cleared = False
    y40_d = []
    c2_scan = []
    pierce = []

    def reset():
        return s.post(
            f"{BASE}/api/cmd/RESET",
            headers=H(key, True),
            json={"card_id": card, "game_id": gid},
            timeout=30,
        ).json()

    def act(guid, aid):
        nact[0] += 1
        return s.post(
            f"{BASE}/api/cmd/ACTION{aid}",
            headers=H(key, True),
            json={"game_id": gid, "guid": guid},
            timeout=30,
        ).json()

    def play(guid, g, prev, seq, stop_lv=None):
        d = {"guid": guid}
        for a_ in seq:
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, False, True
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) > 3:
                return guid, g, prev, d, True, False
            if stop_lv is not None and (d.get("levels_completed") or 0) >= stop_lv:
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
        guid, g, prev, d, ok, dead = play(guid, g, prev, TIP_A5 + TIP_LEAVE)
        return guid, g, prev, d, e8(g)["n"] == 36

    def goto_1040(guid, g, prev):
        return play(guid, g, prev, TO_1040)

    # --- Probe 1: y40 cells → flush D → pure D ---
    p("## 1 y40 flush+D")
    y40_targets = [
        ("1040", []),
        ("1640", [4, 4]),
        ("2240", [4, 4, 4, 4]),
        ("2840", [4, 4, 4, 4, 4, 4]),
    ]
    for name, prep in y40_targets:
        guid, g, prev, d, ok = boot_persist()
        if not ok:
            continue
        guid, g, prev, d, ok, dead = goto_1040(guid, g, prev)
        for a_ in prep:
            d = act(guid, a_)
            guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)
        start = (prev["cx"], prev["cy"])
        if start[1] != 40:
            p(f"  {name} skip not y40", start)
            continue
        # flush: one D noop (already at floor edge?) then D execute
        path = [start]
        for step, a_ in enumerate([2, 2, 2, 2, 2, 2]):
            d = act(guid, a_)
            if "guid" not in d:
                break
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            pos = (prev["cx"], prev["cy"])
            if pos != path[-1]:
                path.append(pos)
            p(f"  {name} D{step+1}", start, "->", pos, "lv", d.get("levels_completed"))
            if (d.get("levels_completed") or 0) > 3:
                cleared = True
                y40_d.append({"cell": name, "start": start, "path": path, "cleared": True})
                break
            if pos[1] >= 46:
                y40_d.append({"cell": name, "start": start, "path": path, "hit_y46": True})
                break
        else:
            y40_d.append({"cell": name, "start": start, "path": path, "hit_y46": False})
        if cleared:
            break

    # --- Probe 2: (52,28) visit → color2 scan ---
    if not cleared:
        p("## 2 c2 after 5228")
        guid, g, prev, d, ok = boot_persist()
        if ok:
            scans = [("persist", [])]
            for label, seq in [
                ("to5228", TO_5228),
                ("on5228", []),
                ("leave5228", [1, 1]),
                ("to1040", TO_1040),
                ("to_tip", [1, 1, 4, 4, 4, 4, 4, 2, 2]),
            ]:
                for a_ in seq:
                    d = act(guid, a_)
                    if "guid" not in d:
                        break
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                    if (d.get("levels_completed") or 0) > 3:
                        cleared = True
                        break
                c2 = c2comps(g)
                rec = {"label": label, "pos": (prev["cx"], prev["cy"]), "c2": c2, "c15": c15n(g), "e8": e8(g)["n"]}
                c2_scan.append(rec)
                p("  c2", label, rec["pos"], "c2", c2[:4], "c15", rec["c15"])
                if cleared:
                    break

    # --- Probe 3: c15 enter/leave — persistent reduction? ---
    if not cleared:
        p("## 3 c15 pierce hunt")
        # candidate cells on/near c15 boundary (from frame analysis)
        candidates = [
            ("5228", TO_5228, 1, [1, 1]),  # enter via route, leave U
            ("5222", TO_5228[:-1], 2, [1]),  # stop at 5222, enter D, leave U
            ("4022", [4, 4], 2, [1, 1]),
            ("4628", TO_5228[:5] + [2], 2, [1, 1]),
            ("2834", TO_1040 + [4, 4, 4, 4, 2, 2], 1, [1, 1]),
            ("3434", TO_1040 + [4, 4, 4, 2, 2], 1, [1, 1]),
        ]
        for name, approach, enter_a, leave_seq in candidates:
            guid, g, prev, d, ok = boot_persist()
            if not ok:
                continue
            c_before = c15n(g)
            for a_ in approach:
                d = act(guid, a_)
                if "guid" not in d:
                    break
                guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)
            pos_enter = (prev["cx"], prev["cy"])
            d = act(guid, enter_a)
            if "guid" not in d:
                continue
            guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)
            pos_on = (prev["cx"], prev["cy"])
            c_on = c15n(g)
            dc_enter = c_on - c_before
            for a_ in leave_seq:
                d = act(guid, a_)
                if "guid" not in d:
                    break
                guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)
            pos_leave = (prev["cx"], prev["cy"])
            c_after = c15n(g)
            dc_after_leave = c_after - c_before
            real = dc_after_leave < 0  # still below baseline after leave
            rec = {
                "cell": name,
                "enter": pos_enter,
                "on": pos_on,
                "leave": pos_leave,
                "c_before": c_before,
                "c_on": c_on,
                "c_after": c_after,
                "dc_on": dc_enter,
                "dc_after_leave": dc_after_leave,
                "real_pierce": real,
            }
            pierce.append(rec)
            p(f"  {name}", pos_on, "c", c_before, "->", c_on, "->", c_after, "real?", real)
            if (d.get("levels_completed") or 0) > 3:
                cleared = True
                break

    result = {
        "cleared": cleared,
        "lv": d.get("levels_completed") if d else None,
        "nact": nact[0],
        "y40_d": y40_d,
        "c2_scan": c2_scan,
        "pierce": pierce,
        "real_pierce_cells": [r["cell"] for r in pierce if r.get("real_pierce")],
    }
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    p("READING", {k: result[k] for k in result if k not in ("y40_d", "c2_scan", "pierce")})
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
