"""g50t L3: latch at (40,34) shrink tip; L2-style A5 queue + revisit.

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

OUT = ROOT / "tests/fixtures/g50t_l3_latch4034.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"

TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_3422 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 3, 3]


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
                    "A",
                    a_,
                    "e8",
                    row["e8"],
                    "c11",
                    row["c11"],
                    "lv",
                    row["lv"],
                )
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, log, True
        return guid, g, prev, log, False

    def uniq_path(log):
        u = []
        for r in log:
            if r["actor"]:
                t = (r["actor"]["cx"], r["actor"]["cy"])
                if not u or u[-1] != t:
                    u.append(t)
        return u

    out = {"trials": {}}
    cleared = False

    variants = {
        # settle on tip then A5
        "settle_R_A5": TO_3434 + [4, 4, 4, 5, 5],
        # L2-style: queue A5 so it executes on tip after R carries in
        "queue_A5_from_3434": TO_3434 + [4, 5, 5],
        "queue_A5_R_A5": TO_3434 + [4, 5, 4, 5],
        # double visit: A5 die, return to tip, leave and check persist
        "a5_revisit": TO_3434 + [4, 4, 5, 5] + TO_3434 + [4, 4, 3, 3],
        # hold tip without A5, leave L, see restore; control
        "hold_leave": TO_3434 + [4, 4, 4, 4, 3, 3, 3, 3],
        # explore from tip for second shrink
        "tip_explore": TO_3434 + [4, 4, 4, 2, 2, 4, 4, 1, 1, 3, 3],
        "tip_D": TO_3434 + [4, 4, 2, 2, 2, 2],
        "tip_U": TO_3434 + [4, 4, 1, 1, 1, 1],
    }

    for name, seq in variants.items():
        p(f"## {name}")
        guid, g, prev = enter_l3()
        guid, g, prev, log, ok = play(guid, g, prev, seq, label=name[:6])
        path = uniq_path(log)
        e_series = [r["e8"] for r in log]
        p("  path", path)
        p("  e8", e_series[0], "->", e_series[-1], "min", min(e_series), "last5", e_series[-5:])
        p("  final", prev, "lv", log[-1]["lv"])
        out["trials"][name] = {
            "path": path,
            "e8": e_series,
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

    # Dedicated: A5 on tip -> respawn -> revisit tip -> leave to (34,34) -> check e8
    if not cleared:
        p("## persist_check")
        guid, g, prev = enter_l3()
        # to tip and A5
        guid, g, prev, log1, _ = play(guid, g, prev, TO_3434 + [4, 4], "to_tip")
        p("  on tip", prev, "e8", e8(g)["n"])
        e_on = e8(g)["n"]
        for a_ in (5, 5):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        p("  after A5", prev, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
        e_after_a5 = e8(g)["n"]
        # revisit
        guid, g, prev, log2, _ = play(guid, g, prev, TO_3434 + [4, 4], "revisit")
        e_rev = e8(g)["n"]
        p("  revisit tip", prev, "e8", e_rev)
        # leave west/left toward shaft
        for a_ in (3, 3, 3, 3):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        e_leave = e8(g)["n"]
        p("  after leave", prev, "e8", e_leave)
        floors = floor_grid(g)
        y22 = [xy for xy in floors if xy[1] == 22]
        p("  floors y22", y22)
        out["persist_check"] = {
            "e_on_tip": e_on,
            "e_after_a5": e_after_a5,
            "e_revisit": e_rev,
            "e_leave": e_leave,
            "actor_leave": prev,
            "floors_y22": y22,
            "lv": d.get("levels_completed"),
        }
        # if persist (e_leave < 92), try go to goal
        if e_leave < 90:
            p("  PERSIST shrink — hunt goal")
            # try top route to 3422 then hope west open, or left-column approach
            for hunt_name, hunt_seq in (
                ("west_3422", TO_3422 + [3, 3, 3, 3, 3, 3]),
                ("via_spawn_R", [4, 4, 4, 4, 4, 4, 4, 4]),
                ("top_drop22", [1, 1, 1, 1, 4, 4, 2, 2, 2, 2, 2, 2]),
            ):
                # continue from current state first for west; for others re-latch fresh
                if hunt_name == "west_3422":
                    # go up x34 to 22 then west
                    seq_h = [1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 3]
                    guid, g, prev, logh, ok = play(guid, g, prev, seq_h, hunt_name)
                else:
                    guid, g, prev = enter_l3()
                    # re-do latch quickly
                    guid, g, prev, _, _ = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
                    guid, g, prev, _, _ = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
                    guid, g, prev, logh, ok = play(guid, g, prev, hunt_seq, hunt_name)
                p(f"  hunt {hunt_name}", uniq_path(logh), "e8", e8(g)["n"], "lv", logh[-1]["lv"])
                out["persist_check"][hunt_name] = {
                    "path": uniq_path(logh),
                    "final": logh[-1],
                    "e8": e8(g)["n"],
                    "floors_y22": [xy for xy in floor_grid(g) if xy[1] == 22],
                    "cleared": ok,
                }
                if ok:
                    cleared = True
                    CLEAR.write_text(
                        json.dumps(
                            {"cleared": True, "method": f"latch+{hunt_name}", "log": logh},
                            indent=2,
                            default=str,
                        ),
                        encoding="utf-8",
                    )
                    break
                if cleared:
                    break

    # Also: while e8=76 ON tip (no A5), check floor map / c11 — does shrink open y22?
    if not cleared:
        p("## while_holding_tip map")
        guid, g, prev = enter_l3()
        guid, g, prev, _, _ = play(guid, g, prev, TO_3434 + [4, 4])
        floors = floor_grid(g)
        p("  hold e8", e8(g)["n"], "c11", int(np.sum(g == 11)))
        p("  floors y22", [xy for xy in floors if xy[1] == 22])
        p("  floors x34", [xy for xy in floors if xy[0] == 34])
        p("  floors x22", [xy for xy in floors if xy[0] == 22])
        p("  floors x28", [xy for xy in floors if xy[0] == 28])
        p("  floors x40", [xy for xy in floors if xy[0] == 40])
        out["holding_map"] = {
            "e8": e8(g)["n"],
            "c11": int(np.sum(g == 11)),
            "floors_y22": [xy for xy in floors if xy[1] == 22],
            "floors_x22": [xy for xy in floors if xy[0] == 22],
            "floors_x28": [xy for xy in floors if xy[0] == 28],
            "floors_x34": [xy for xy in floors if xy[0] == 34],
            "floors_x40": [xy for xy in floors if xy[0] == 40],
            "all_floors": floors,
        }

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_LATCH_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    p("wrote", OUT)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
