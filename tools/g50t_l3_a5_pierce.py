"""g50t L3: A5 at pierce/snake + map tips; retry west after latch.

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
    comps9,
    floor_grid,
)

OUT = ROOT / "tests/fixtures/g50t_l3_a5_pierce.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"

# proven: lands (34,22) with pending LEFT (west blocked but position stable)
TO_3422 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 3]
# continue to (34,28)/(34,34)
TO_3428 = TO_3422 + [2]  # pending L then D -> may need tune
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]


def p(*a, **k):
    print(*a, **k, flush=True)


def under(g, prev, rad=2):
    if not prev:
        return {"8": 0, "11": 0, "5": 0, "0": 0}
    cx, cy = int(round(prev["cx"])), int(round(prev["cy"]))
    patch = g[max(0, cy - rad) : cy + rad + 1, max(0, cx - rad) : cx + rad + 1]
    return {str(c): int(np.sum(patch == c)) for c in (0, 5, 8, 9, 11)}


def c11_comps(g):
    H_, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(1, 63):
        for x in range(W):
            if seen[y, x] or int(g[y, x]) != 11:
                continue
            stack = [(x, y)]
            seen[y, x] = True
            cells = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 1 <= ny < 63 and not seen[ny, nx] and int(g[ny, nx]) == 11:
                        seen[ny, nx] = True
                        stack.append((nx, ny))
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
    out.sort(key=lambda b: (-b["n"], b["cy"], b["cx"]))
    return out


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

    def run_seq(guid, g, prev, seq):
        log = []
        for a_ in seq:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            log.append(
                {
                    "a": a_,
                    "actor": prev,
                    "e8": e8(g)["n"],
                    "c11": int(np.sum(g == 11)),
                    "lv": d.get("levels_completed"),
                    "under": under(g, prev),
                }
            )
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, log, True
        return guid, g, prev, log, False

    out = {"trials": {}}
    cleared = False

    # Snapshot L3 start perception
    guid, g, prev = enter_l3()
    floors = floor_grid(g)
    out["start"] = {
        "actor": prev,
        "e8": e8(g),
        "c11_n": int(np.sum(g == 11)),
        "c11": c11_comps(g),
        "goals": comps9(g),
        "floor_n": len(floors),
        "floors_y22": [xy for xy in floors if xy[1] == 22],
        "floors_x34": [xy for xy in floors if xy[0] == 34],
        "hist": dict(Counter(g[1:63].ravel().tolist())),
    }
    p("start", prev, "e8", e8(g), "c11", out["start"]["c11"])
    p("floors y22", out["start"]["floors_y22"])
    p("floors x34", out["start"]["floors_x34"])

    trials = {
        "A5_at_3422": TO_3422 + [3, 3, 5, 5],  # settle L then A5
        "A5_at_3422_imm": TO_3422 + [5, 5],
        "A5_at_3428": [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 3, 5, 5],
        "A5_at_3434": TO_3434 + [5, 5],
        # from 3434 try sidestep then A5
        "3434_L_A5": TO_3434 + [3, 3, 5, 5],
        "3434_R_A5": TO_3434 + [4, 4, 5, 5],
        # deeper / more D before A5
        "3434_DD_A5": TO_3434 + [2, 2, 5, 5],
        # hold on 3422 (stand on c11) without A5 — just note under
        "hold_3422": TO_3422 + [3, 3, 3, 3],
    }

    for name, seq in trials.items():
        p(f"## {name}")
        guid, g, prev = enter_l3()
        guid, g, prev, log, ok = run_seq(guid, g, prev, seq)
        uniq = []
        for r in log:
            if r["actor"]:
                t = (r["actor"]["cx"], r["actor"]["cy"])
                if not uniq or uniq[-1] != t:
                    uniq.append(t)
        e_series = [r["e8"] for r in log]
        c_series = [r["c11"] for r in log]
        p("  path", uniq)
        p("  e8", e_series[0], "->", e_series[-1], "min", min(e_series))
        p("  c11", c_series[0], "->", c_series[-1], "min", min(c_series))
        p("  final", prev, "under", log[-1]["under"], "lv", log[-1]["lv"])
        out["trials"][name] = {
            "path": uniq,
            "e8": e_series,
            "c11": c_series,
            "final": log[-1],
            "cleared": ok,
            "seq": seq,
        }
        if ok:
            cleared = True
            CLEAR.write_text(
                json.dumps({"cleared": True, "method": name, "log": log, "seq": seq}, indent=2, default=str),
                encoding="utf-8",
            )
            break

        # If e8 dropped and stayed after move-away, try west to goal
        if min(e_series) < 92 and prev and prev["cx"] == 10 and prev["cy"] == 22:
            p("  respawned after A5; e8 now", e8(g)["n"], " — retry top west route")
            seq2 = TO_3422 + [3, 3, 3, 3, 3, 3]
            guid, g, prev, log2, ok2 = run_seq(guid, g, prev, seq2)
            uniq2 = []
            for r in log2:
                if r["actor"]:
                    t = (r["actor"]["cx"], r["actor"]["cy"])
                    if not uniq2 or uniq2[-1] != t:
                        uniq2.append(t)
            p("  postA5 path", uniq2, "e8", e8(g)["n"], "lv", log2[-1]["lv"])
            out["trials"][name]["post_respawn"] = {
                "path": uniq2,
                "final": log2[-1],
                "e8": e8(g)["n"],
                "cleared": ok2,
            }
            if ok2:
                cleared = True
                break

    # Micro-scan around (34,34): flush each dir, note e8 under
    if not cleared:
        p("## scan around 3434")
        guid, g, prev = enter_l3()
        guid, g, prev, log, _ = run_seq(guid, g, prev, TO_3434)
        p("  at", prev, "under", under(g, prev), "e8", e8(g)["n"])
        scan = []
        for aid, name in ((3, "L"), (4, "R"), (1, "U"), (2, "D")):
            guid, g, prev = enter_l3()
            guid, g, prev, _, _ = run_seq(guid, g, prev, TO_3434)
            before = (prev["cx"], prev["cy"], e8(g)["n"], int(np.sum(g == 11)))
            for a_ in (aid, aid):
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
            after = (
                (prev["cx"], prev["cy"]) if prev else None,
                e8(g)["n"],
                int(np.sum(g == 11)),
                under(g, prev),
            )
            p(f"  {name}", before[:2], "->", after[0], "e8", before[2], "->", after[1], "under", after[3])
            scan.append({"dir": name, "before": before, "after": after})
            # if e8 dropped, A5
            if after[1] < before[2]:
                e0 = after[1]
                for a_ in (5, 5):
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                p("    A5 ->", prev, "e8", e0, "->", e8(g)["n"], "lv", d.get("levels_completed"))
                if (d.get("levels_completed") or 0) > 2:
                    cleared = True
        out["scan3434"] = scan

    # After standing on 3422 (c11 touch), try going U then approach goal from top x22 with somehow open?
    # Or go R from 3422
    if not cleared:
        p("## from 3422 try U/R/D micro")
        for name, extra in (
            ("3422_U", [3, 3, 1, 1, 1, 1]),
            ("3422_R", [3, 3, 4, 4, 4, 4]),
            ("3422_D_L", [3, 3, 2, 2, 3, 3, 3, 3]),
            ("3422_D_R", [3, 3, 2, 2, 4, 4, 4, 4]),
        ):
            guid, g, prev = enter_l3()
            guid, g, prev, log, ok = run_seq(guid, g, prev, TO_3422 + extra)
            uniq = []
            for r in log:
                if r["actor"]:
                    t = (r["actor"]["cx"], r["actor"]["cy"])
                    if not uniq or uniq[-1] != t:
                        uniq.append(t)
            p(f"  {name}", uniq, "lv", log[-1]["lv"], "e8", log[-1]["e8"], "c11", log[-1]["c11"])
            out["trials"][name] = {"path": uniq, "final": log[-1], "cleared": ok}
            if ok:
                cleared = True
                clear_name = name
                CLEAR.write_text(
                    json.dumps({"cleared": True, "method": name, "log": log}, indent=2, default=str),
                    encoding="utf-8",
                )
                break

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_A5_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    p("wrote", OUT)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
