"""g50t L3: after latch, settle (34,22) and walk c11 bar east; hunt (22,28).

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

OUT = ROOT / "tests/fixtures/g50t_l3_c11_east.json"
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

    # Settle at (34,22) from (34,34) with pending=L after latch leave:
    # U: noop L; U: ->28; L: exec U ->22 pending L; L: noop settle.
    settle_3422 = [1, 1, 3, 3]

    trials = {
        # east along c11
        "east_c11": settle_3422 + [4] * 12,
        # east then down
        "east_then_D": settle_3422 + [4] * 8 + [2] * 10,
        # east to 52, down, west along y28 toward 22
        "east_D_west28": settle_3422 + [4] * 8 + [2, 2, 2, 2] + [3] * 10 + [1, 1, 1, 1],
        # without latch: can we east on c11 at e8=92?
        "nolatch_east": None,  # special
    }

    for name, seq in trials.items():
        p(f"## {name}")
        guid, g, prev = enter_l3()
        if name != "nolatch_east":
            guid, g, prev, _ = latch(guid, g, prev)
            p("  latched", prev, "e8", e8(g)["n"])
            guid, g, prev, log, ok = play(guid, g, prev, seq)
        else:
            # top to 34, down to 22 settle, east
            seq = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 3, 3] + [4] * 10
            guid, g, prev, log, ok = play(guid, g, prev, seq)
        path = uniq(log)
        p("  path", path)
        p("  final", prev, "e8", e8(g)["n"], "c11", int(np.sum(g == 11)), "lv", log[-1]["lv"])
        # print each step briefly when x changes on y22
        for r in log:
            if r["actor"] and abs(r["actor"]["cy"] - 22) < 3:
                p("   ", r["a"], (r["actor"]["cx"], r["actor"]["cy"]), "c11", r["c11"], "e8", r["e8"])
        out[name] = {"path": path, "final": log[-1], "cleared": ok, "e8": e8(g)["n"]}
        if ok:
            cleared = True
            CLEAR.write_text(
                json.dumps({"cleared": True, "method": name, "log": log}, indent=2, default=str),
                encoding="utf-8",
            )
            p("*** L3 CLEAR")
            break

    # Closed-loop: latch, go to 3422 settled, then try R flush repeatedly
    if not cleared:
        p("## closed east from settled 3422")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch(guid, g, prev)
        guid, g, prev, log0, _ = play(guid, g, prev, settle_3422)
        # flush L to clear pending
        for a_ in (3, 3):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        p("  settled", prev, "e8", e8(g)["n"])
        log = []
        for i in range(12):
            before = (prev["cx"], prev["cy"]) if prev else None
            for a_ in (4, 4):
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                log.append({"a": a_, "actor": prev, "e8": e8(g)["n"], "c11": int(np.sum(g == 11)), "lv": d.get("levels_completed")})
                if (d.get("levels_completed") or 0) > 2:
                    cleared = True
                    break
            after = (prev["cx"], prev["cy"]) if prev else None
            p(f"  R{i}", before, "->", after, "e8", e8(g)["n"], "c11", int(np.sum(g == 11)))
            if after == before:
                p("  east blocked — try D")
                for a_ in (2, 2):
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                p("  after D", prev)
                break
            if cleared:
                break
        out["closed_east"] = {"path": uniq(log), "final": log[-1] if log else None, "cleared": cleared}

        # From wherever, try reach (22,28): if at x52 y16/22, D and L
        if not cleared and prev:
            p("## from here hunt 2228")
            for i in range(20):
                if not prev:
                    break
                cx, cy = prev["cx"], prev["cy"]
                # target (22,28)
                dx, dy = 22 - cx, 28 - cy
                if abs(dx) < 3 and abs(dy) < 3:
                    aid = 1  # then up to goal
                    for a_ in (1, 1, 1, 1):
                        d = act(guid, a_)
                        guid = d["guid"]
                        g = plane(d)
                        prev = actor(g, prev)
                        p("  togoal", prev, "lv", d.get("levels_completed"))
                        if (d.get("levels_completed") or 0) > 2:
                            cleared = True
                            CLEAR.write_text(
                                json.dumps({"cleared": True, "method": "hunt2228", "actor": prev}, indent=2, default=str),
                                encoding="utf-8",
                            )
                            break
                    break
                if abs(dx) >= abs(dy) and abs(dx) >= 3:
                    aid = 4 if dx > 0 else 3
                else:
                    aid = 2 if dy > 0 else 1
                before = (cx, cy)
                for a_ in (aid, aid):
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                after = (prev["cx"], prev["cy"]) if prev else None
                p(f"  h{i}", before, "->", after, "A", aid, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
                if after == before:
                    # try all alts once
                    moved = False
                    for alt in (1, 2, 3, 4):
                        b2 = (prev["cx"], prev["cy"])
                        for a_ in (alt, alt):
                            d = act(guid, a_)
                            guid = d["guid"]
                            g = plane(d)
                            prev = actor(g, prev)
                        if prev and (prev["cx"], prev["cy"]) != b2:
                            p(f"   alt{alt}", b2, "->", (prev["cx"], prev["cy"]))
                            moved = True
                            break
                    if not moved:
                        break
                if (d.get("levels_completed") or 0) > 2:
                    cleared = True
                    break

    # Snapshot walkable after latch: dump color under grid centers
    if not cleared:
        p("## grid colors after latch")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch(guid, g, prev)
        grid = {}
        for y in range(10, 55, 6):
            row = {}
            for x in range(10, 55, 6):
                row[x] = int(g[y, x])
            grid[y] = row
            p(f"  y{y}", row)
        out["grid_after_latch"] = grid
        out["floors"] = floor_grid(g)

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_C11_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
