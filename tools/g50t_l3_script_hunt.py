"""g50t L3: fast scripted corridor probes + A5 on snake; one enter per scenario.

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
    comps9,
)

TAGS = ["g50t_recon"]
OUT = ROOT / "tests/fixtures/g50t_l3_script_hunt.json"


def p(*a, **k):
    print(*a, **k, flush=True)


def main():
    key = _api_key()
    s = requests.Session()
    card = s.post(
        f"{BASE}/api/scorecard/open", headers=H(key, True), json={"tags": TAGS}, timeout=30
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
        return guid, g, prev, d

    def run(guid, g, prev, seq, label):
        log = []
        for i, a_ in enumerate(seq):
            d = act(guid, a_)
            guid = d["guid"]
            g2 = plane(d)
            prev = actor(g2, prev)
            row = {
                "i": i,
                "a": a_,
                "actor": prev,
                "e8n": e8(g2)["n"],
                "c11": int(np.sum(g2 == 11)),
                "lv": d.get("levels_completed"),
            }
            log.append(row)
            g = g2
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, log, True
        return guid, g, prev, d, log, False

    scenarios = {
        # top ring like L2
        "top_R_then_D_to_goal": [1, 1, 1] + [4] * 10 + [2, 2] + [4, 4, 3, 3, 4],
        # up then right along y10 to far right then down
        "top_farR_down": [1, 1, 1] + [4] * 14 + [2] * 6 + [3] * 4,
        # down-right via bottom after somehow opening — first go top right then bot
        "top_R_bot_loop": [1, 1, 1] + [4] * 8 + [2] * 8 + [3] * 6 + [1] * 4 + [4] * 4,
        # approach mid goal from left via up-right-down
        "to_goal_y22": [1, 1] + [4] * 4 + [2] + [4] * 4,
        # go up-left? spawn already left
        "U_only_then_R": [1] * 6 + [4] * 8 + [2] * 3,
    }

    out = {"scenarios": {}}
    cleared = False

    for name, seq in scenarios.items():
        p(f"## {name}")
        guid, g, prev, d = enter_l3()
        p("  start", prev, "e8", e8(g)["n"], "c11", int(np.sum(g == 11)))
        guid, g, prev, d, log, ok = run(guid, g, prev, seq, name)
        p("  final", prev, "e8", e8(g)["n"], "c11", int(np.sum(g == 11)), "lv", d.get("levels_completed"))
        # sample positions
        pos = [(r["actor"]["cx"], r["actor"]["cy"]) for r in log if r["actor"]]
        uniq = []
        for x in pos:
            if not uniq or uniq[-1] != x:
                uniq.append(x)
        p("  path", uniq[:20], "..." if len(uniq) > 20 else "")
        out["scenarios"][name] = {
            "final": log[-1] if log else None,
            "uniq_pos": uniq,
            "cleared": ok,
            "seq": seq,
        }
        if ok:
            cleared = True
            (ROOT / "tests/fixtures/g50t_l3_clear_attempt.json").write_text(
                json.dumps({"cleared": True, "name": name, "l3_actions": seq, "log": log}, indent=2, default=str),
                encoding="utf-8",
            )
            break

    # Snake hunt: from spawn go down-right toward e8 bbox once top/right opens
    # From ascii: snake heads around (24,52) and (40,52). Need to reach bottom.
    # Try: U to top, R to x52, D all the way
    if not cleared:
        p("## descend right column to snake")
        seq = [1, 1, 1] + [4] * 14 + [2] * 10
        guid, g, prev, d = enter_l3()
        guid, g, prev, d, log, ok = run(guid, g, prev, seq, "right_descend")
        p("  final", prev, "e8", e8(g)["n"], "under check")
        if prev:
            cx, cy = int(round(prev["cx"])), int(round(prev["cy"]))
            p("  patch8", int(np.sum(g[cy - 2 : cy + 3, cx - 2 : cx + 3] == 8)))
            p("  patch11", int(np.sum(g[cy - 2 : cy + 3, cx - 2 : cx + 3] == 11)))
        out["right_descend"] = {"final": log[-1], "uniq": [
            (r["actor"]["cx"], r["actor"]["cy"]) for r in log if r["actor"]
        ]}
        # if on snake, A5
        if prev and int(np.sum(g[cy - 2 : cy + 3, cx - 2 : cx + 3] == 8)) >= 2:
            e0 = e8(g)["n"]
            c0 = int(np.sum(g == 11))
            for _ in range(2):
                d = act(guid, 5)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
            p("  A5 ->", prev, "e8", e0, "->", e8(g)["n"], "c11", c0, "->", int(np.sum(g == 11)), "lv", d.get("levels_completed"))
            out["right_descend"]["a5"] = {
                "e8": [e0, e8(g)["n"]],
                "c11": [c0, int(np.sum(g == 11))],
                "lv": d.get("levels_completed"),
                "actor": prev,
            }
            if (d.get("levels_completed") or 0) > 2:
                cleared = True

    # Walk online from L3: try to visit lattice points along top and right
    if not cleared:
        p("## online lattice walk (no reset), prefer unvisited")
        guid, g, prev, d = enter_l3()
        seen = set()
        trail = []
        events = []
        for step in range(50):
            if not prev:
                break
            pos = (int(round(prev["cx"])), int(round(prev["cy"])))
            seen.add(pos)
            e0 = e8(g)["n"]
            c0 = int(np.sum(g == 11))
            # order: R, U, D, L — explore right/top first
            moved = False
            for aid in (4, 1, 2, 3):
                d1 = act(guid, aid)
                guid = d1["guid"]
                g1 = plane(d1)
                a1 = actor(g1, prev)
                d2 = act(guid, aid)
                guid = d2["guid"]
                g2 = plane(d2)
                a2 = actor(g2, a1)
                if not a2:
                    prev = a1
                    g = g1
                    continue
                npos = (int(round(a2["cx"])), int(round(a2["cy"])))
                e1 = e8(g2)["n"]
                c1 = int(np.sum(g2 == 11))
                trail.append({"a": aid, "to": npos, "e8": e1, "c11": c1, "lv": d2.get("levels_completed")})
                if e1 != e0 or c1 != c0:
                    events.append({"pos": npos, "e8": [e0, e1], "c11": [c0, c1]})
                    p("  EVENT", events[-1])
                g, prev = g2, a2
                if (d2.get("levels_completed") or 0) > 2:
                    cleared = True
                    p("*** CLEAR")
                    break
                if npos not in seen:
                    moved = True
                    break
                # moved to seen — accept anyway to change branch sometimes
                if npos != pos:
                    moved = True
                    break
            if cleared:
                break
            if not moved:
                # try A5
                d = act(guid, 5)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                trail.append({"a": 5, "to": None if not prev else (prev["cx"], prev["cy"]), "e8": e8(g)["n"], "c11": int(np.sum(g == 11))})
        p("  seen", sorted(seen))
        p("  events", events)
        out["lattice"] = {"seen": [list(x) for x in sorted(seen)], "events": events, "trail_tail": trail[-15:]}

    out["reading"] = "L3_CLEAR" if cleared else "L3_SCRIPT_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    p("wrote", OUT)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
