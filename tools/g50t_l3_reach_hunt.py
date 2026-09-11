"""g50t L3: reachability BFS (1-step buffer), probe c8/c11, hunt path to goal.

tags=["g50t_recon"]
"""
from __future__ import annotations

import json
import sys
from collections import deque
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
    body_ndiff,
)

TAGS = ["g50t_recon"]
OUT = ROOT / "tests/fixtures/g50t_l3_reach_hunt.json"


def p(*a, **k):
    print(*a, **k, flush=True)


DIRS = {1: (0, -6), 2: (0, 6), 3: (-6, 0), 4: (6, 0)}


def main():
    key = _api_key()
    s = requests.Session()
    card = s.post(
        f"{BASE}/api/scorecard/open", headers=H(key, True), json={"tags": TAGS}, timeout=30
    ).json()["card_id"]
    gid = s.get(f"{BASE}/api/games/g50t", headers=H(key), timeout=20).json()["game_id"]
    p("opened", gid, card)

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
        d = act(guid, 3)  # true L3
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        return guid, g, prev, d

    out = {}

    # ---- online BFS with buffer: state = (cx,cy, pending_dir or 0) ----
    # Simpler approach: from each reached cell, try flush each dir (send dir twice)
    p("## reachability via flush dirs")
    guid, g, prev, d = enter_l3()
    start = (int(round(prev["cx"])), int(round(prev["cy"])))
    goals = comps9(g)
    goal = next((x for x in goals if x["n"] > 10), goals[-1] if goals else None)
    p("start", start, "goal", goal, "e8", e8(g), "c11", int(np.sum(g == 11)))

    visited = {start: []}
    q = deque([start])
    shrink_events = []
    parent_act = {}

    # For each node we need to restore by replaying path — expensive.
    # Budget: explore up to 40 cells.
    while q and len(visited) < 45:
        pos = q.popleft()
        path = visited[pos]
        # restore to L3 + path
        guid, g, prev, d = enter_l3()
        for a_ in path:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        if not prev:
            continue
        e_before = e8(g)["n"]
        c11_before = int(np.sum(g == 11))
        for aid in (1, 2, 3, 4):
            # flush: aid, aid
            guid2, g2 = guid, g
            prev2 = prev
            d1 = act(guid2, aid)
            guid2 = d1["guid"]
            g2 = plane(d1)
            prev2 = actor(g2, prev2)
            d2 = act(guid2, aid)
            guid2 = d2["guid"]
            g2 = plane(d2)
            a2 = actor(g2, prev2)
            if not a2:
                # restore by full enter+path again next iter — need re-enter now
                guid, g, prev, d = enter_l3()
                for a_ in path:
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                continue
            npos = (int(round(a2["cx"])), int(round(a2["cy"])))
            e_after = e8(g2)["n"]
            c11_after = int(np.sum(g2 == 11))
            if e_after != e_before or c11_after != c11_before:
                shrink_events.append({
                    "from": pos,
                    "to": npos,
                    "aid": aid,
                    "e8": [e_before, e_after],
                    "c11": [c11_before, c11_after],
                    "lv": d2.get("levels_completed"),
                })
                p("  EVENT", shrink_events[-1])
            if (d2.get("levels_completed") or 0) > 2:
                p("*** CLEAR via", path + [aid, aid])
                out["clear"] = {"path": path + [aid, aid], "final": a2}
                (ROOT / "tests/fixtures/g50t_l3_clear_attempt.json").write_text(
                    json.dumps({"cleared": True, "l3_actions": path + [aid, aid], "final": a2}, indent=2, default=str),
                    encoding="utf-8",
                )
                out["reading"] = "L3_CLEAR"
                OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
                s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)
                return
            if npos != pos and npos not in visited:
                visited[npos] = path + [aid, aid]
                q.append(npos)
                p(f"  reach {npos} via A{aid} (n={len(visited)})")
            # restore for next aid from same pos
            guid, g, prev, d = enter_l3()
            for a_ in path:
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)

    p("reached", len(visited), "cells:", sorted(visited.keys()))
    out["reached"] = [{"pos": list(k), "nact": len(v)} for k, v in visited.items()]
    out["shrink_events"] = shrink_events

    # Can we reach near goal?
    if goal:
        gx, gy = int(round(goal["cx"])), int(round(goal["cy"]))
        near = [(x, y) for x, y in visited if abs(x - gx) + abs(y - gy) <= 12]
        p("near goal", near)
        out["near_goal"] = near

    # ---- probe: path top corridor then right then down ----
    p("## scripted: U to top, R across, approach goal")
    guid, g, prev, d = enter_l3()
    # U U to y10
    script = [1, 1, 1, 1]  # buffered ups
    # then R many
    script += [4] * 12
    # then D toward y22
    script += [2] * 4
    # then L/R toward goal x22
    script += [4] * 2 + [3] * 2
    log = []
    for i, a_ in enumerate(script):
        d = act(guid, a_)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        row = {"i": i, "a": a_, "actor": prev, "e8": e8(g), "c11": int(np.sum(g == 11)), "lv": d.get("levels_completed")}
        log.append(row)
        if i % 4 == 0:
            p(" ", row)
        if (d.get("levels_completed") or 0) > 2:
            p("*** CLEAR scripted")
            out["clear"] = {"script": script[: i + 1], "log": log}
            out["reading"] = "L3_CLEAR"
            break
    else:
        out["scripted"] = {"final": log[-1] if log else None, "log_tail": log[-8:]}
        p("scripted final", log[-1] if log else None)

    # ---- stand on c8 tips / try A5 ----
    p("## find c8 stand cells among reached + try A5")
    # re-enter, go to each reached cell that has c8 nearby, press 5
    a5_trials = []
    for pos, path in list(visited.items())[:25]:
        guid, g, prev, d = enter_l3()
        for a_ in path:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        if not prev:
            continue
        cx, cy = int(round(prev["cx"])), int(round(prev["cy"]))
        under8 = int(np.sum(g[cy - 2 : cy + 3, cx - 2 : cx + 3] == 8))
        under11 = int(np.sum(g[cy - 2 : cy + 3, cx - 2 : cx + 3] == 11))
        if under8 < 2 and under11 < 2:
            continue
        e0 = e8(g)["n"]
        c0 = int(np.sum(g == 11))
        # flush a noop-ish: press 5 twice (buffer)
        d = act(guid, 5)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        d = act(guid, 5)
        guid = d["guid"]
        g2 = plane(d)
        a2 = actor(g2, prev)
        trial = {
            "pos": pos,
            "under8": under8,
            "under11": under11,
            "e8": [e0, e8(g2)["n"]],
            "c11": [c0, int(np.sum(g2 == 11))],
            "actor_after": a2,
            "lv": d.get("levels_completed"),
            "b": body_ndiff(g, g2) if False else body_ndiff(plane({"frame": [g]}), g2) if False else int(np.sum(g[1:63] != g2[1:63])),
        }
        # fix body_ndiff
        trial["b"] = int(np.sum(g[1:63] != g2[1:63]))
        p("  A5@", pos, trial)
        a5_trials.append(trial)
        if (d.get("levels_completed") or 0) > 2:
            out["clear"] = {"a5_at": pos, "path": path + [5, 5]}
            out["reading"] = "L3_CLEAR"
            break

    out["a5_trials"] = a5_trials
    if "reading" not in out:
        out["reading"] = "L3_REACH_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"], "n_reached", len(visited))
    p("wrote", OUT)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
