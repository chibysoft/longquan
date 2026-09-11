"""g50t L3: buffer-aware west to goal + mid-column drop.

Prior clear_hunt overshot (34,22)->(34,28) because pending stayed DOWN.
Fix: after exactly 2 Downs from top settle, issue LEFT so landing at
(34,22) has pending=LEFT, then west to ~(22,22).

Also try drop from true (22,10): [U]*4+[R]*2 then D's.

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

OUT = ROOT / "tests/fixtures/g50t_l3_buffer_west.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"


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

    def play(name, seq):
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
            if prev:
                p(
                    f"  {i} A{a_}",
                    (prev["cx"], prev["cy"]),
                    "c11",
                    row["c11"],
                    "e8",
                    row["e8"],
                    "lv",
                    row["lv"],
                )
            if (d.get("levels_completed") or 0) > 2:
                p("*** L3 CLEAR", name)
                return True, log, g, prev
        uniq = []
        for r in log:
            if r["actor"]:
                t = (r["actor"]["cx"], r["actor"]["cy"])
                if not uniq or uniq[-1] != t:
                    uniq.append(t)
        p("  path", uniq)
        return False, log, g, prev

    # Buffer model after [1]*4+[4]*4:
    # R1 noop@top, R2..R4 -> 16,22,28; D1 exec last R -> 34; D2 -> 16; D3 -> 22.
    # So [2]*2 then [3]: land (34,22) with pending LEFT.
    variants = {
        # PRIMARY: pending-LEFT land at (34,22) then west
        "bufL_at_3422": [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 3, 3, 3, 3, 3, 3],
        # one extra D settle then L (expect overshoot — control)
        "ctrl_3D_then_L": [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 3, 3, 3, 3],
        # drop from ~x22: only 2R so D1 carries to x22
        "drop_x22": [1, 1, 1, 1, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2],
        # drop x22 then if stuck at y16 try R into goal band
        "drop_x22_nudgeR": [1, 1, 1, 1, 4, 4, 2, 2, 4, 4, 2, 2, 2, 2],
        # drop x22 nudge L
        "drop_x22_nudgeL": [1, 1, 1, 1, 4, 4, 2, 2, 3, 3, 2, 2, 2, 2],
        # top to x28 (3R effective?) then D — [4]*3
        "drop_x28": [1, 1, 1, 1, 4, 4, 4, 2, 2, 2, 2, 2, 2],
        # after bufL path, if at (28,22) try more L / D micro
        "bufL_then_D": [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 3, 3, 3, 2, 3, 3],
    }

    results = {}
    cleared = False
    clear_name = None
    clear_log = None

    for name, seq in variants.items():
        ok, log, g, prev = play(name, seq)
        uniq = []
        for r in log:
            if r["actor"]:
                t = (r["actor"]["cx"], r["actor"]["cy"])
                if not uniq or uniq[-1] != t:
                    uniq.append(t)
        results[name] = {
            "path": uniq,
            "final": log[-1] if log else None,
            "seq": seq,
            "cleared": ok,
        }
        if ok:
            cleared = True
            clear_name = name
            clear_log = log
            CLEAR.write_text(
                json.dumps(
                    {"cleared": True, "method": name, "l3_actions": seq, "log": log},
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
            break

    # Closed-loop: if bufL reached x<34 at y22, keep LEFT until clear/stuck
    if not cleared:
        p("## closed_loop_west")
        seq0 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 3]
        guid, g, prev = enter_l3()
        log = []
        for a_ in seq0:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            log.append(
                {
                    "a": a_,
                    "actor": prev,
                    "c11": int(np.sum(g == 11)),
                    "e8": e8(g)["n"],
                    "lv": d.get("levels_completed"),
                }
            )
            p("  setup", prev, "c11", int(np.sum(g == 11)), "lv", d.get("levels_completed"))
        # now pending should be L at ~(34,22); keep flushing L
        for i in range(10):
            before = (prev["cx"], prev["cy"]) if prev else None
            d = act(guid, 3)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            log.append(
                {
                    "a": 3,
                    "actor": prev,
                    "c11": int(np.sum(g == 11)),
                    "e8": e8(g)["n"],
                    "lv": d.get("levels_completed"),
                }
            )
            after = (prev["cx"], prev["cy"]) if prev else None
            p(f"  L{i}", before, "->", after, "lv", d.get("levels_completed"), "c11", int(np.sum(g == 11)))
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                clear_name = "closed_loop_west"
                clear_log = log
                p("*** L3 CLEAR closed_loop")
                break
            if after == before and i >= 1:
                p("  west stuck")
                break
        uniq = []
        for r in log:
            if r["actor"]:
                t = (r["actor"]["cx"], r["actor"]["cy"])
                if not uniq or uniq[-1] != t:
                    uniq.append(t)
        results["closed_loop_west"] = {"path": uniq, "final": log[-1], "cleared": cleared}
        if cleared:
            CLEAR.write_text(
                json.dumps(
                    {"cleared": True, "method": clear_name, "log": clear_log},
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )

    payload = {
        "cleared": cleared,
        "method": clear_name,
        "log": clear_log,
        "results": results,
        "reading": "L3_CLEAR" if cleared else "L3_BUFFER_PARTIAL",
    }
    OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    p("READING:", payload["reading"])
    p("wrote", OUT)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
