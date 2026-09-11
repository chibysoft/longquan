"""g50t L3 clear hunt: pierce c11 at x34 → y22 → west to goal ~(22,22).

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

OUT = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"


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

    # Primary: top → x34 → down to y22 → west to x22
    # Empirically: [1]*4 + [4]*4 reaches (34,10); [2]*4 reaches ~(34,22)+
    variants = {
        "west_from_3422": [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 3, 3, 3, 3],
        "west_more_D": [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 3, 3, 3, 3],
        "west_less_D": [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 3, 3, 3, 3],
        "west_settle_L": [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3],
        # continue down to snake then A5 then up to goal
        "down_snake_A5": [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2, 5, 5],
        # after piercing, go to (28,22) then (22,22)
        "stop_y22_west": [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 3, 2, 3, 3, 3],
    }

    results = {}
    cleared = False
    clear_name = None
    clear_log = None

    for name, seq in variants.items():
        p(f"## {name}")
        guid, g, prev = enter_l3()
        log = []
        for i, a_ in enumerate(seq):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            row = {
                "i": i,
                "a": a_,
                "actor": prev,
                "e8": e8(g)["n"],
                "c11": int(np.sum(g == 11)),
                "lv": d.get("levels_completed"),
            }
            log.append(row)
            if prev and i % 2 == 0:
                p(f"  {i} A{a_}", (prev["cx"], prev["cy"]), "c11", row["c11"], "lv", row["lv"])
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                clear_name = name
                clear_log = log
                p("*** L3 CLEAR", name)
                break
        uniq = []
        for r in log:
            if r["actor"]:
                t = (r["actor"]["cx"], r["actor"]["cy"])
                if not uniq or uniq[-1] != t:
                    uniq.append(t)
        p("  path", uniq, "final_lv", log[-1]["lv"])
        results[name] = {"path": uniq, "final": log[-1], "seq": seq}
        if cleared:
            break

    # If we got near goal without clear, try more L from best position
    if not cleared:
        p("## extend west_from_3422 with more L/D micro")
        seq = variants["west_from_3422"] + [3, 3, 2, 3, 3, 1, 3, 3]
        guid, g, prev = enter_l3()
        log = []
        for i, a_ in enumerate(seq):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            log.append({"i": i, "a": a_, "actor": prev, "c11": int(np.sum(g == 11)), "lv": d.get("levels_completed"), "e8": e8(g)["n"]})
            if prev and (abs(prev["cx"] - 22) < 4 and abs(prev["cy"] - 22) < 4):
                p("  NEAR GOAL", prev, "lv", d.get("levels_completed"))
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                clear_name = "extend_west"
                clear_log = log
                p("*** CLEAR")
                break
        uniq = []
        for r in log:
            if r["actor"]:
                t = (r["actor"]["cx"], r["actor"]["cy"])
                if not uniq or uniq[-1] != t:
                    uniq.append(t)
        p("  path", uniq)
        results["extend_west"] = {"path": uniq, "final": log[-1], "seq": seq}

    payload = {
        "cleared": cleared,
        "method": clear_name,
        "log": clear_log,
        "results": results,
        "reading": "L3_CLEAR" if cleared else "L3_WEST_PARTIAL",
    }
    OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    p("READING:", payload["reading"])
    p("wrote", OUT)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
