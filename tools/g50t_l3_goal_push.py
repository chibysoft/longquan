"""g50t L3: explicit seq to (22,10)/(34,16); drop/A5/c11; hunt clear.

Buffer discipline: after arriving, send intended dir twice (flush).
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

OUT = ROOT / "tests/fixtures/g50t_l3_goal_push.json"


def p(*a, **k):
    print(*a, **k, flush=True)


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
            log.append({
                "a": a_,
                "actor": prev,
                "e8": e8(g)["n"],
                "c11": int(np.sum(g == 11)),
                "lv": d.get("levels_completed"),
            })
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, log, True
        return guid, g, prev, log, False

    # Known path: spawn(10,22) -U-> (10,16) -U-> (10,10) -R*n-> 
    # Use explicit counts matching script_hunt success
    to_top = [1, 1, 1]  # buffer-aware ups to y10
    # After to_top last pending is U; first R executes U (noop at top?), second R moves R
    # Safer: extra U to settle at top, then R's
    to_x22 = to_top + [1] + [4] * 4  # settle + right toward 22
    to_x34 = to_top + [1] + [4] * 8
    to_x52 = to_top + [1] + [4] * 14

    trials = {
        "at22_then_DDD": to_x22 + [2, 2, 2, 2, 2, 2],
        "at22_DRD": to_x22 + [2, 2, 4, 4, 2, 2],
        "at22_DLD": to_x22 + [2, 2, 3, 3, 2, 2],
        "at34_DD_A5": to_x34 + [2, 2, 2, 2, 5, 5],
        "at52_DD_A5": to_x52 + [2, 2, 2, 2, 5, 5],
        "at34_L_to_goal": to_x34 + [2, 2, 3, 3, 3, 3, 2, 2],
        "at28_D": to_top + [1] + [4] * 6 + [2, 2, 2, 2, 2, 2],
    }

    out = {"trials": {}}
    cleared = False
    for name, seq in trials.items():
        p(f"## {name}")
        guid, g, prev = enter_l3()
        p("  start", prev)
        guid, g, prev, log, ok = play(guid, g, prev, seq)
        # unique path
        uniq = []
        for r in log:
            if not r["actor"]:
                continue
            t = (r["actor"]["cx"], r["actor"]["cy"])
            if not uniq or uniq[-1] != t:
                uniq.append(t)
        p("  path", uniq)
        p("  final", prev, "e8", e8(g)["n"], "c11", int(np.sum(g == 11)), "lv", log[-1]["lv"] if log else None)
        out["trials"][name] = {"path": uniq, "final": log[-1] if log else None, "cleared": ok, "seq": seq}
        if ok:
            cleared = True
            (ROOT / "tests/fixtures/g50t_l3_clear_attempt.json").write_text(
                json.dumps({"cleared": True, "name": name, "l3_actions": seq, "log": log}, indent=2, default=str),
                encoding="utf-8",
            )
            break
        # if on c11/c8 at end, note
        if prev:
            cx, cy = int(round(prev["cx"])), int(round(prev["cy"]))
            out["trials"][name]["under"] = {
                "8": int(np.sum(g[cy - 2 : cy + 3, cx - 2 : cx + 3] == 8)),
                "11": int(np.sum(g[cy - 2 : cy + 3, cx - 2 : cx + 3] == 11)),
            }

    # Additional: from (34,16) walk left along y16 toward x22 then D
    if not cleared:
        p("## y16 west toward goal then D")
        seq = to_x34 + [2, 2] + [3] * 8 + [2, 2, 2, 2]
        guid, g, prev = enter_l3()
        guid, g, prev, log, ok = play(guid, g, prev, seq)
        uniq = []
        for r in log:
            if r["actor"]:
                t = (r["actor"]["cx"], r["actor"]["cy"])
                if not uniq or uniq[-1] != t:
                    uniq.append(t)
        p("  path", uniq)
        p("  final", prev, "lv", log[-1]["lv"])
        out["y16_west"] = {"path": uniq, "final": log[-1], "cleared": ok}
        if ok:
            cleared = True

    # Touch color11: get to (40,16) which is above the E bar, then D into it
    if not cleared:
        p("## dive into c11 from (40,16)")
        seq = to_top + [1] + [4] * 10 + [2, 2, 2, 2, 5, 1, 5]
        guid, g, prev = enter_l3()
        guid, g, prev, log, ok = play(guid, g, prev, seq)
        uniq = []
        for r in log:
            if r["actor"]:
                t = (r["actor"]["cx"], r["actor"]["cy"])
                if not uniq or uniq[-1] != t:
                    uniq.append(t)
        p("  path", uniq)
        p("  final", prev, "e8", e8(g)["n"], "c11", int(np.sum(g == 11)), "lv", log[-1]["lv"])
        # print c11 still
        if prev:
            cx, cy = int(round(prev["cx"])), int(round(prev["cy"]))
            p("  under8/11", int(np.sum(g[cy-2:cy+3,cx-2:cx+3]==8)), int(np.sum(g[cy-2:cy+3,cx-2:cx+3]==11)))
        out["c11_dive"] = {"path": uniq, "final": log[-1], "cleared": ok}

    out["reading"] = "L3_CLEAR" if cleared else "L3_GOAL_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    p("wrote", OUT)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
