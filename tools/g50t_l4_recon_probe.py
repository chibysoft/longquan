"""g50t L4 recon: clear L1–L3, load true L4, dump frame + smoke tips.

tags=["g50t_recon"]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
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

OUT = ROOT / "tests/fixtures/g50t_l4_recon_probe.json"
FRAME = ROOT / "tests/fixtures/g50t_l4_frame_live.json"
CLEAR = ROOT / "tests/fixtures/g50t_l4_clear_attempt.json"

TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]


def p(*a, **k):
    print(*a, **k, flush=True)


def hist(g):
    return {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))}


def blobs(g, color, min_n=8):
    H_, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(H_):
        for x in range(W):
            if seen[y, x] or int(g[y, x]) != color:
                continue
            stack = [(x, y)]
            seen[y, x] = True
            cells = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 0 <= ny < H_ and not seen[ny, nx] and int(g[ny, nx]) == color:
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            if len(cells) >= min_n:
                xs = [c[0] for c in cells]
                ys = [c[1] for c in cells]
                out.append(
                    {
                        "n": len(cells),
                        "cx": round(sum(xs) / len(cells), 2),
                        "cy": round(sum(ys) / len(cells), 2),
                        "box": [min(xs), min(ys), max(xs), max(ys)],
                    }
                )
    out.sort(key=lambda b: -b["n"])
    return out


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
    meta = s.get(f"{BASE}/api/games/g50t", headers=H(key), timeout=20).json()
    gid = meta["game_id"]
    p("opened", gid, "win_levels", meta.get("win_levels"), "acts", meta.get("available_actions"))
    nact = [0]
    out = {"game_id": gid, "win_levels": meta.get("win_levels"), "acts": meta.get("available_actions")}

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
            d["_nact"] = nact[0]
        return d

    def play(guid, g, prev, seq, stop_lv=None):
        for a_ in seq:
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, False, True
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            lv = d.get("levels_completed") or 0
            if stop_lv is not None and lv >= stop_lv:
                return guid, g, prev, d, True, False
            if lv > 3:
                return guid, g, prev, d, True, False
        return guid, g, prev, d, False, False

    # --- enter L4 via L1–L3 clear ---
    d = reset()
    nact[0] = 0
    guid = d["guid"]
    g = plane(d)
    prev = None

    guid, g, prev, d, ok, dead = play(guid, g, prev, L1_SEQ + [2] * 4 + [4] * 8, stop_lv=1)
    p("L1", d.get("levels_completed"), nact[0], (prev["cx"], prev["cy"]) if prev else None)
    d = act(guid, 3)
    guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)

    guid, g, prev, d, ok, dead = play(guid, g, prev, TO_2840 + L2_ROUTE, stop_lv=2)
    p("L2", d.get("levels_completed"), nact[0], (prev["cx"], prev["cy"]) if prev else None)
    d = act(guid, 3)
    guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)

    # L3 clear
    guid, g, prev, d, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
    if not ok and not dead:
        guid, g, prev, d, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
    p("tip1", e8(g)["n"], nact[0])
    guid, g, prev, d, ok, dead = play(guid, g, prev, TO_TIP2 + [5, 5])
    p("tip2A5", e8(g)["n"], nact[0], "lv", d.get("levels_completed"))
    if (d.get("levels_completed") or 0) < 3 and not dead:
        guid, g, prev, d, ok, dead = play(guid, g, prev, TIP1_LEAVE)
        p("releave", e8(g)["n"], nact[0])
        guid, g, prev, d, ok, dead = play(guid, g, prev, L3_WEST_CLEAR, stop_lv=3)
    p("L3 done", d.get("levels_completed"), nact[0], (prev["cx"], prev["cy"]) if prev else None, "dead", dead)

    if (d.get("levels_completed") or 0) < 3 or dead or "guid" not in d:
        out["reading"] = "L3_ENTER_FAIL"
        out["nact"] = nact[0]
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        p("READING", out["reading"])
        s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)
        return

    # transition into true L4
    clear_frame_hist = hist(g)
    d = act(guid, 1)
    if "guid" not in d:
        out["reading"] = "L4_TRANSITION_FAIL"
        out["trans_err"] = {k: d.get(k) for k in d if k != "frame"}
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        p("READING", out["reading"], out["trans_err"])
        s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)
        return
    guid = d["guid"]
    g = plane(d)
    prev = actor(g, prev)
    lv = d.get("levels_completed") or 0
    h = hist(g)
    p("L4 frame", "lv", lv, "nact", nact[0], "hist", h, "pos", (prev["cx"], prev["cy"]) if prev else None)

    FRAME.write_text(
        json.dumps(
            {
                "frame": d.get("frame"),
                "levels_completed": lv,
                "state": d.get("state"),
                "available_actions": d.get("available_actions"),
                "pos": (prev["cx"], prev["cy"]) if prev else None,
                "hist": h,
                "e8": einfo(g),
                "nact": nact[0],
            },
            default=str,
        ),
        encoding="utf-8",
    )

    out["l4"] = {
        "levels": lv,
        "state": d.get("state"),
        "acts": d.get("available_actions"),
        "hist": h,
        "hist_delta_vs_l3end": {k: h.get(k, 0) - clear_frame_hist.get(k, 0) for k in set(h) | set(clear_frame_hist)},
        "pos": (prev["cx"], prev["cy"]) if prev else None,
        "e8": einfo(g),
        "c9_blobs": blobs(g, 9, 8)[:8],
        "c8_blobs": blobs(g, 8, 8)[:8],
        "c11_blobs": blobs(g, 11, 4)[:6],
        "c2_blobs": blobs(g, 2, 4)[:6],
        "other_colors": sorted(set(h) - {0, 1, 5, 8, 9}),
    }
    p("  e8", out["l4"]["e8"])
    p("  c9", out["l4"]["c9_blobs"][:4])
    p("  c8", out["l4"]["c8_blobs"][:4])
    p("  other", out["l4"]["other_colors"])

    # smoke dirs + A5 (budget-aware: few taps)
    smoke = {}
    for aid in (1, 2, 3, 4, 5):
        if "guid" not in d:
            break
        before = (prev["cx"], prev["cy"]) if prev else None
        e_before = e8(g)["n"]
        d = act(guid, aid)
        if "guid" not in d:
            smoke[aid] = {"err": {k: d.get(k) for k in d if k != "frame"}, "nact": nact[0]}
            break
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        after = (prev["cx"], prev["cy"]) if prev else None
        smoke[aid] = {
            "before": before,
            "after": after,
            "moved": before != after,
            "e8": e8(g)["n"],
            "de8": e8(g)["n"] - e_before,
            "lv": d.get("levels_completed"),
        }
        p(f"  smoke A{aid}", before, "->", after, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
        if (d.get("levels_completed") or 0) > 3:
            CLEAR.write_text(
                json.dumps({"cleared": True, "method": f"smoke_A{aid}", "nact": nact[0]}, indent=2),
                encoding="utf-8",
            )
            out["cleared"] = True
            break
        # second tap to flush buffer
        d = act(guid, aid)
        if "guid" not in d:
            smoke[aid]["flush_err"] = {k: d.get(k) for k in d if k != "frame"}
            break
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        smoke[aid]["after2"] = (prev["cx"], prev["cy"]) if prev else None
        smoke[aid]["e8_2"] = e8(g)["n"]
        if (d.get("levels_completed") or 0) > 3:
            CLEAR.write_text(
                json.dumps({"cleared": True, "method": f"smoke2_A{aid}", "nact": nact[0]}, indent=2),
                encoding="utf-8",
            )
            out["cleared"] = True
            break

    out["smoke"] = smoke
    out["nact"] = nact[0]
    out["reading"] = "L4_CLEAR" if out.get("cleared") else "L4_FRAME"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING", out["reading"], "nact", nact[0])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
