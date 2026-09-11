"""g50t L3 clear: latch (40,34) A5+revisit persist e8=76, then reach (22,22).

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

OUT = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]


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

    def play(guid, g, prev, seq, label=""):
        log = []
        for a_ in seq:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            row = {
                "a": a_,
                "actor": prev,
                "e8": e8(g)["n"],
                "c11": int(np.sum(g == 11)),
                "lv": d.get("levels_completed"),
            }
            log.append(row)
            if label and prev:
                p(
                    f"  {label}",
                    (prev["cx"], prev["cy"]),
                    f"A{a_}",
                    "e8",
                    row["e8"],
                    "lv",
                    row["lv"],
                )
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, log, True
        return guid, g, prev, log, False

    def uniq(log):
        u = []
        for r in log:
            if r["actor"]:
                t = (r["actor"]["cx"], r["actor"]["cy"])
                if not u or u[-1] != t:
                    u.append(t)
        return u

    def latch(guid, g, prev):
        """A5 on (40,34) + revisit + leave to (34,34); expect e8 persist 76."""
        guid, g, prev, log1, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5], "a5")
        if ok:
            return guid, g, prev, log1, True
        guid, g, prev, log2, ok = play(guid, g, prev, TO_3434 + [4, 4, 3, 3], "rev")
        return guid, g, prev, log1 + log2, ok

    results = {}
    cleared = False
    clear_log = None
    clear_name = None

    hunts = {
        # From (34,34) after latch: U once into buffer then L at y22
        # Buffer: at (34,34) pending L from leave; U exec L? careful.
        # Safer explicit: settle D noop, U U to reach y22 with pending U, then L
        "U_to_22_then_L": [2, 2, 1, 1, 1, 3, 3, 3, 3, 3, 3],
        # U U (34,34)->(34,28)->(34,22) then L
        "UU_L": [1, 1, 1, 3, 3, 3, 3, 3, 3],
        # go to (34,28) then L toward (22,28) then U to goal
        "L_at_28_then_U": [1, 1, 3, 3, 3, 3, 1, 1, 1, 1],
        # top to x22, drop (maybe open now)
        "top_x22_drop": [1, 1, 1, 1, 1, 1, 3, 3, 2, 2, 2, 2, 2, 2],
        # to left column y22 then R to goal
        "left_col_R": [1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 2, 2, 4, 4, 4, 4],
        # bottom via x34 to 52 then west/north
        "down_to_52": [2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 1, 1, 1, 1],
        # from tip side: R stay, D? explore (40,28)/(40,40)
        "from_tip_D": [4, 4, 2, 2, 2, 2, 3, 3, 1, 1],
        "from_tip_moreR": [4, 4, 4, 4, 2, 2, 3, 3, 3, 3],
    }

    for name, seq in hunts.items():
        p(f"## {name}")
        guid, g, prev = enter_l3()
        guid, g, prev, log0, ok = latch(guid, g, prev)
        if ok:
            cleared, clear_name, clear_log = True, "latch_clear", log0
            p("*** CLEAR during latch")
            break
        p("  latched at", prev, "e8", e8(g)["n"])
        floors = floor_grid(g)
        p(
            "  floors y22",
            [xy for xy in floors if xy[1] == 22],
            "x22",
            [xy for xy in floors if xy[0] == 22],
            "y28",
            [xy for xy in floors if xy[1] == 28],
        )
        guid, g, prev, log1, ok = play(guid, g, prev, seq, name[:8])
        path = uniq(log0 + log1)
        p("  path", uniq(log1), "e8", e8(g)["n"], "lv", log1[-1]["lv"])
        results[name] = {
            "path": path,
            "hunt_path": uniq(log1),
            "final": log1[-1],
            "e8": e8(g)["n"],
            "floors_y22": [xy for xy in floor_grid(g) if xy[1] == 22],
            "floors_y28": [xy for xy in floor_grid(g) if xy[1] == 28],
            "cleared": ok,
            "seq": seq,
        }
        if ok:
            cleared, clear_name, clear_log = True, name, log0 + log1
            p("*** L3 CLEAR", name)
            break

    # Closed-loop greedy after latch toward (22,22)
    if not cleared:
        p("## greedy_to_goal")
        guid, g, prev = enter_l3()
        guid, g, prev, log0, ok = latch(guid, g, prev)
        log = list(log0)
        target = (22.0, 22.0)
        stuck = 0
        for i in range(40):
            if not prev:
                break
            cx, cy = prev["cx"], prev["cy"]
            dx, dy = target[0] - cx, target[1] - cy
            if abs(dx) < 3 and abs(dy) < 3:
                # on goal — flush same dir
                aid = 3 if dx <= 0 else 4
            elif abs(dx) >= abs(dy):
                aid = 4 if dx > 0 else 3
            else:
                aid = 2 if dy > 0 else 1
            before = (cx, cy)
            # flush pair
            for a_ in (aid, aid):
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
                    cleared, clear_name, clear_log = True, "greedy", log
                    p("*** L3 CLEAR greedy")
                    break
            if cleared:
                break
            after = (prev["cx"], prev["cy"]) if prev else None
            p(f"  g{i}", before, "->", after, "A", aid, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
            if after == before:
                stuck += 1
                # try alternate axis
                if stuck >= 2:
                    p("  stuck — try alternate dirs")
                    moved = False
                    for alt in (1, 2, 3, 4):
                        if alt == aid:
                            continue
                        b2 = (prev["cx"], prev["cy"])
                        for a_ in (alt, alt):
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
                        a2 = (prev["cx"], prev["cy"]) if prev else None
                        p(f"    alt A{alt}", b2, "->", a2)
                        if a2 != b2:
                            moved = True
                            stuck = 0
                            break
                    if not moved:
                        break
            else:
                stuck = 0
        results["greedy"] = {"path": uniq(log), "final": log[-1] if log else None, "cleared": cleared}

    payload = {
        "cleared": cleared,
        "method": clear_name,
        "log": clear_log,
        "results": results,
        "reading": "L3_CLEAR" if cleared else "L3_POSTLATCH_PARTIAL",
    }
    OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    p("READING:", payload["reading"])
    p("wrote", OUT)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
