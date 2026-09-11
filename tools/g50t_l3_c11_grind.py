"""g50t L3: grind c11 down at x34; retest west + right-col drop.

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

OUT = ROOT / "tests/fixtures/g50t_l3_c11_grind.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_3422 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 3]


def p(*a, **k):
    print(*a, **k, flush=True)


def main():
    key = _api_key()
    s = requests.Session()
    card = s.post(
        f"{BASE}/api/scorecard/open", headers=H(key, True), json={"tags": ["g50t_recon"]}, timeout=30
    ).json()["card_id"]
    gid = s.get(f"{BASE}/api/games/g50t", headers=H(key), timeout=20).json()["game_id"]
    p("opened", gid)

    def reset():
        return s.post(
            f"{BASE}/api/cmd/RESET", headers=H(key, True), json={"card_id": card, "game_id": gid}, timeout=30
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
        return guid, g, prev, d

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
                    "actor": prev,
                    "e8": e8(g)["n"],
                    "c11": int(np.sum(g == 11)),
                    "lv": d.get("levels_completed"),
                }
            )
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, log, True
        return guid, g, prev, d, log, False

    def latch(guid, g, prev):
        guid, g, prev, d, _, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if ok:
            return guid, g, prev, d, True
        guid, g, prev, d, _, ok = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        return guid, g, prev, d, ok

    def flush(guid, g, prev, aid, n=2):
        for _ in range(n):
            d = act(guid, aid)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, True
        return guid, g, prev, d, False

    out = {"trials": {}, "cleared": False}
    cleared = False

    # 1) no latch: grind c11 at 3422 by UD oscillation
    p("## grind c11 no-latch")
    guid, g, prev, d = enter_l3()
    guid, g, prev, d, _, _ = play(guid, g, prev, TO_3422)
    series = [{"pos": (prev["cx"], prev["cy"]), "c11": int(np.sum(g == 11)), "e8": e8(g)["n"]}]
    p("  start", series[0])
    # oscillate U/D on shaft and poke L/R
    pattern = [1, 1, 2, 2, 3, 3, 4, 4, 2, 2, 1, 1, 3, 3, 2, 2, 1, 1, 2, 2] * 3
    for a_ in pattern:
        d = act(guid, a_)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        c = int(np.sum(g == 11))
        row = {"a": a_, "pos": (prev["cx"], prev["cy"]) if prev else None, "c11": c, "e8": e8(g)["n"], "lv": d.get("levels_completed")}
        if c != series[-1]["c11"] or (prev and (prev["cx"], prev["cy"]) != series[-1]["pos"]):
            series.append(row)
            if c != series[-2]["c11"]:
                p("  c11", series[-2]["c11"], "->", c, "at", row["pos"])
        if (d.get("levels_completed") or 0) > 2:
            cleared = True
            break
        # if c11 low, try west hard
        if c <= 24 and prev and abs(prev["cy"] - 22) < 4:
            for _ in range(6):
                b = (prev["cx"], prev["cy"])
                guid, g, prev, d, ok = flush(guid, g, prev, 3, 2)
                a = (prev["cx"], prev["cy"]) if prev else None
                p("  west", b, a, "c11", int(np.sum(g == 11)), "lv", d.get("levels_completed"))
                if ok or (d.get("levels_completed") or 0) > 2:
                    cleared = True
                    break
                if a == b:
                    break
            break
    out["trials"]["grind_nolatch"] = {
        "c11_min": min(r["c11"] for r in series),
        "c11_series": series[:40],
        "final": series[-1],
        "centers_y22": {x: int(g[22, x]) for x in range(10, 55, 6)},
    }
    p("  c11_min", out["trials"]["grind_nolatch"]["c11_min"], "y22", out["trials"]["grind_nolatch"]["centers_y22"])

    # 2) latch then grind + right drop when c11 low
    if not cleared:
        p("## grind c11 after latch")
        guid, g, prev, d = enter_l3()
        guid, g, prev, d, _ = latch(guid, g, prev)
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_3422)
        series = [{"pos": (prev["cx"], prev["cy"]), "c11": int(np.sum(g == 11)), "e8": e8(g)["n"]}]
        p("  start", series[0])
        pattern = [1, 1, 2, 2, 3, 3, 2, 2, 1, 1, 4, 4, 2, 2] * 4
        min_c = series[0]["c11"]
        for a_ in pattern:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            c = int(np.sum(g == 11))
            if c < min_c:
                min_c = c
                p("  c11_min", min_c, "at", (prev["cx"], prev["cy"]) if prev else None, "e8", e8(g)["n"])
                p("  y22", {x: int(g[22, x]) for x in range(10, 55, 6)})
                p("  y16", {x: int(g[16, x]) for x in range(10, 55, 6)})
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                break
        out["trials"]["grind_latch"] = {
            "c11_min": min_c,
            "final_c11": int(np.sum(g == 11)),
            "e8": e8(g)["n"],
            "actor": prev,
            "y22": {x: int(g[22, x]) for x in range(10, 55, 6)},
            "y28": {x: int(g[28, x]) for x in range(10, 55, 6)},
        }
        # from here try west then rightcol
        if prev and not cleared:
            p("  try west")
            for i in range(8):
                b = (prev["cx"], prev["cy"])
                guid, g, prev, d, ok = flush(guid, g, prev, 3, 2)
                a = (prev["cx"], prev["cy"]) if prev else None
                p(f"  L{i}", b, a, "c11", int(np.sum(g == 11)), "lv", d.get("levels_completed"))
                if ok or (d.get("levels_completed") or 0) > 2:
                    cleared = True
                    CLEAR.write_text(
                        json.dumps({"cleared": True, "method": "c11_grind_west"}, indent=2, default=str),
                        encoding="utf-8",
                    )
                    break
                if a == b:
                    break
                if abs((a[0] if a else 0) - 22) < 3 and abs((a[1] if a else 0) - 22) < 3:
                    p("  NEAR GOAL", a)
        if not cleared and prev:
            p("  try right drop from top")
            # go top then x52
            for a_ in [1] * 6 + [4] * 10 + [2] * 10:
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                if prev and prev["cy"] >= 22 and prev["cx"] >= 50:
                    p("  ** right passed y16!", prev, "e8", e8(g)["n"], "c11", int(np.sum(g == 11)))
                    break
                if (d.get("levels_completed") or 0) > 2:
                    cleared = True
                    break
            p("  right end", prev, "e8", e8(g)["n"], "c11", int(np.sum(g == 11)))
            out["trials"]["grind_latch"]["right_end"] = prev

    # 3) hold tip: does c11 change? dump + try if any new move
    if not cleared:
        p("## hold tip c11 + bottom centers")
        guid, g, prev, d = enter_l3()
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_3434 + [4, 4])
        p("  hold", prev, "e8", e8(g)["n"], "c11", int(np.sum(g == 11)))
        p("  y52", {x: int(g[52, x]) for x in range(10, 55, 6)})
        p("  y46", {x: int(g[46, x]) for x in range(10, 55, 6)})
        p("  y40", {x: int(g[40, x]) for x in range(10, 55, 6)})
        out["trials"]["hold_bottom"] = {
            "c11": int(np.sum(g == 11)),
            "y40": {x: int(g[40, x]) for x in range(10, 55, 6)},
            "y46": {x: int(g[46, x]) for x in range(10, 55, 6)},
            "y52": {x: int(g[52, x]) for x in range(10, 55, 6)},
        }

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_C11_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
