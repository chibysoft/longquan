"""g50t L3: post-latch A5 on c11/(34,22); double-latch tip; probe (16,34) access.

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

OUT = ROOT / "tests/fixtures/g50t_l3_postlatch_a5.json"
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

    trials = {
        # latch then U to (34,22) A5
        "a5_at_3422": [1, 1, 1, 5, 5],
        # latch tip again A5 (double latch)
        "double_tip_a5": [4, 4, 5, 5] + TO_3434 + [4, 4, 3, 3],
        # latch, tip, leave, tip, A5 again, revisit
        "triple_cycle": [4, 4, 5, 5] + TO_3434 + [4, 4, 5, 5] + TO_3434 + [4, 4, 3, 3],
        # latch then to (34,28) A5
        "a5_at_3428": [1, 1, 5, 5],
        # latch, top left, down to spawn, A5
        "a5_at_spawn": [1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 2, 2, 5, 5],
        # latch, try micro steps from tip for e8 drop
        "tip_micro": [4, 4, 4, 3, 4, 2, 4, 1, 4, 4],
    }

    for name, seq in trials.items():
        p(f"## {name}")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch(guid, g, prev)
        p("  latched", prev, "e8", e8(g)["n"], "c11", int(np.sum(g == 11)))
        guid, g, prev, log, ok = play(guid, g, prev, seq)
        e_series = [r["e8"] for r in log]
        c_series = [r["c11"] for r in log]
        path = uniq(log)
        p("  path", path)
        p(
            "  e8 min",
            min(e_series),
            "final",
            e_series[-1],
            "c11 min",
            min(c_series),
            "final",
            c_series[-1],
            "lv",
            log[-1]["lv"],
        )
        floors = floor_grid(g)
        y22 = sorted(x for x, y in floors if y == 22)
        y28 = sorted(x for x, y in floors if y == 28)
        p("  floors y22", y22, "y28", y28)
        out[name] = {
            "path": path,
            "e_min": min(e_series),
            "e_final": e_series[-1],
            "c11_min": min(c_series),
            "c11_final": c_series[-1],
            "floors_y22": y22,
            "floors_y28": y28,
            "cleared": ok,
            "final": log[-1],
        }
        if ok:
            cleared = True
            CLEAR.write_text(
                json.dumps({"cleared": True, "method": name, "log": log, "seq": seq}, indent=2, default=str),
                encoding="utf-8",
            )
            p("*** L3 CLEAR")
            break

    # Reachability smoke: after latch, flush each dir from key cells
    if not cleared:
        p("## dir smoke at key cells")
        cells_nav = {
            "from_3434": [],
            "at_3422": [1, 1, 1],
            "at_tip": [4, 4],
            "at_5210": [1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4],
            "at_1010": [1, 1, 1, 1, 1, 1, 3, 3, 3, 3],
            "at_1022": [1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 2, 2],
        }
        smoke = {}
        for cname, nav in cells_nav.items():
            guid, g, prev = enter_l3()
            guid, g, prev, _ = latch(guid, g, prev)
            if nav:
                guid, g, prev, _, _ = play(guid, g, prev, nav)
            base = (prev["cx"], prev["cy"]) if prev else None
            e0 = e8(g)["n"]
            dirs = {}
            for aid, dn in ((1, "U"), (2, "D"), (3, "L"), (4, "R")):
                guid, g, prev = enter_l3()
                guid, g, prev, _ = latch(guid, g, prev)
                if nav:
                    guid, g, prev, _, _ = play(guid, g, prev, nav)
                for a_ in (aid, aid):
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                after = (prev["cx"], prev["cy"]) if prev else None
                dirs[dn] = {
                    "to": after,
                    "e8": e8(g)["n"],
                    "moved": after != base,
                    "lv": d.get("levels_completed"),
                }
                if e8(g)["n"] < 76:
                    p(f"  {cname} {dn} SHRINK", base, "->", after, e8(g)["n"])
                if (d.get("levels_completed") or 0) > 2:
                    cleared = True
                    p("*** CLEAR", cname, dn)
            p(f"  {cname} @{base} e8={e0}", {k: v["to"] for k, v in dirs.items()})
            smoke[cname] = {"base": base, "e8": e0, "dirs": dirs}
            if cleared:
                break
        out["smoke"] = smoke

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_POSTA5_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
