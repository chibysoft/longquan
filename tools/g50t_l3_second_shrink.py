"""g50t L3: after e8=76 latch, map floors + right column + 2nd shrink probes.

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
    floor_grid,
)

OUT = ROOT / "tests/fixtures/g50t_l3_second_shrink.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]


def p(*a, **k):
    print(*a, **k, flush=True)


def uniq(log):
    u = []
    for r in log:
        if r["actor"]:
            t = (r["actor"]["cx"], r["actor"]["cy"])
            if not u or u[-1] != t:
                u.append(t)
    return u


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
                    "actor": prev,
                    "e8": e8(g)["n"],
                    "c11": int(np.sum(g == 11)),
                    "lv": d.get("levels_completed"),
                }
            )
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, log, True
        return guid, g, prev, log, False

    def latch(guid, g, prev):
        guid, g, prev, _, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if ok:
            return guid, g, prev, True
        guid, g, prev, _, ok = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        return guid, g, prev, ok

    out = {}
    cleared = False

    p("## floors after latch")
    guid, g, prev = enter_l3()
    guid, g, prev, _ = latch(guid, g, prev)
    floors = floor_grid(g)
    by_y = {}
    for x, y in floors:
        by_y.setdefault(y, []).append(x)
    for y in sorted(by_y):
        p(f"  y{y}", sorted(by_y[y]))
    out["floors"] = {"e8": e8(g)["n"], "by_y": {str(k): sorted(v) for k, v in by_y.items()}, "all": floors}

    # Right column: after latch go top, east to ~52, drop
    trials = {
        "x52_drop": [1, 1, 1, 1, 1, 1] + [4] * 10 + [2] * 14,
        "x52_drop_L": [1, 1, 1, 1, 1, 1] + [4] * 10 + [2] * 8 + [3] * 8 + [1] * 6,
        "x46_drop": [1, 1, 1, 1, 1, 1] + [4] * 6 + [2] * 14,
        # along y28 east from 34 toward 52 then down/west
        "y28_east": [1, 1] + [4] * 10 + [2] * 8 + [3] * 10 + [1] * 4,
        # y22 east (c11 bar) toward 52
        "y22_east": [1, 1, 1] + [4] * 12 + [2] * 6 + [3] * 10,
        # tip again then walk snake edge clockwise-ish
        "snake_walk": [4, 4, 4, 2, 2, 4, 2, 2, 3, 2, 2, 3, 3, 1, 1],
    }

    for name, seq in trials.items():
        p(f"## {name}")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch(guid, g, prev)
        e0 = e8(g)["n"]
        guid, g, prev, log, ok = play(guid, g, prev, seq)
        e_series = [r["e8"] for r in log]
        path = uniq(log)
        p("  path", path)
        p("  e8", e0, "min", min(e_series), "final", e_series[-1], "lv", log[-1]["lv"])
        hits = [
            (r["actor"]["cx"], r["actor"]["cy"], r["e8"])
            for r in log
            if r["actor"] and r["e8"] < 76
        ]
        if hits:
            p("  ** e8<76 hits", hits)
        out[name] = {
            "path": path,
            "e_min": min(e_series),
            "e_final": e_series[-1],
            "hits": hits,
            "cleared": ok,
            "seq": seq,
        }
        if ok:
            cleared = True
            CLEAR.write_text(
                json.dumps({"cleared": True, "method": name, "log": log, "seq": seq}, indent=2, default=str),
                encoding="utf-8",
            )
            p("*** L3 CLEAR", name)
            break
        # if new shrink tip found, A5+revisit
        if hits and not ok:
            tip = hits[-1]
            p("  A5 attempt at last hit", tip)
            # may already have moved on; re-run to tip then A5
            guid, g, prev = enter_l3()
            guid, g, prev, _ = latch(guid, g, prev)
            guid, g, prev, log2, ok2 = play(guid, g, prev, seq)
            for a_ in (5, 5):
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
            p("  after A5", prev, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                CLEAR.write_text(
                    json.dumps({"cleared": True, "method": name + "+A5", "log": log2}, indent=2, default=str),
                    encoding="utf-8",
                )
                break
            out[name]["a5"] = {"actor": prev, "e8": e8(g)["n"], "lv": d.get("levels_completed")}

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_SECOND_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    p("wrote", OUT)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
