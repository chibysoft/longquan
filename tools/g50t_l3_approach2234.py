"""g50t L3: from persist60, approach (22,34) carefully; dump responses.

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

OUT = ROOT / "tests/fixtures/g50t_l3_approach2234.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]


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
    p("opened", gid, "card", card)

    def reset():
        return s.post(
            f"{BASE}/api/cmd/RESET",
            headers=H(key, True),
            json={"card_id": card, "game_id": gid},
            timeout=30,
        ).json()

    def act_raw(guid, aid):
        r = s.post(
            f"{BASE}/api/cmd/ACTION{aid}",
            headers=H(key, True),
            json={"game_id": gid, "guid": guid},
            timeout=30,
        )
        try:
            d = r.json()
        except Exception:
            return {"_http": r.status_code, "_text": r.text[:500]}
        return d

    def act(guid, aid):
        d = act_raw(guid, aid)
        if "guid" not in d:
            raise RuntimeError(json.dumps({k: d.get(k) for k in d if k != "frame"}, default=str))
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
        for a_ in seq:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, True
        return guid, g, prev, d, False

    def tip1_latch(guid, g, prev):
        guid, g, prev, d, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if ok:
            return guid, g, prev, d, True
        return play(guid, g, prev, TO_3434 + [4, 4, 3, 3])

    out = {}
    guid, g, prev = enter_l3()
    guid, g, prev, d, ok = tip1_latch(guid, g, prev)
    p("tip1", e8(g)["n"], prev)
    guid, g, prev, d, ok = play(guid, g, prev, TO_TIP2 + [5, 5])
    p("after A5", e8(g)["n"], prev)
    guid, g, prev, d, ok = play(guid, g, prev, TIP1_LEAVE)
    p("releave", e8(g)["n"], prev)
    guid, g, prev, d, ok = play(guid, g, prev, TO_TIP2 + [4, 4])
    p("persist", e8(g)["n"], prev)
    assert e8(g)["n"] == 60

    # to (10,34)
    for a_ in [3, 3, 3, 3, 1, 1, 1, 1]:
        d = act(guid, a_)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        p("climb", a_, (prev["cx"], prev["cy"]), e8(g)["n"])
    # drain U
    for a_ in [1, 4]:
        d = act(guid, a_)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        p("drain", a_, (prev["cx"], prev["cy"]))

    # now (10,34) pend R — go to (16,34)
    d = act(guid, 4)
    guid = d["guid"]
    g = plane(d)
    prev = actor(g, prev)
    p("at16", (prev["cx"], prev["cy"]), e8(g)["n"])
    cx, cy = int(round(prev["cx"])), int(round(prev["cy"]))
    sub = g[cy - 2 : cy + 3, cx - 2 : cx + 15]
    out["at16_patch"] = sub.tolist()
    out["cell_2234"] = {
        "center": int(g[34, 22]),
        "hist": {int(k): int(v) for k, v in zip(*np.unique(g[32:37, 20:25], return_counts=True))},
    }
    p("cell2234", out["cell_2234"])

    # Try variants to enter (22,34)
    trials = []
    # save guid state — can't clone. Do one attempt per full reset.

    # Attempt A: U (buffer land with pend U)
    d = act_raw(guid, 1)
    trials.append({"try": "U_from_16", "keys": list(d.keys()), "meta": {k: d.get(k) for k in d if k != "frame"}})
    p("try U", trials[-1]["meta"])
    if "guid" in d:
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        p("  pos", (prev["cx"], prev["cy"]), "lv", d.get("levels_completed"))
        if (d.get("levels_completed") or 0) > 2:
            CLEAR.write_text(json.dumps({"cleared": True, "method": "U_from_16"}, indent=2), encoding="utf-8")
            out["cleared"] = True
    else:
        out["fail_U"] = trials[-1]["meta"]
        # reopen
        guid, g, prev = enter_l3()
        guid, g, prev, d, ok = tip1_latch(guid, g, prev)
        guid, g, prev, d, ok = play(guid, g, prev, TO_TIP2 + [5, 5])
        guid, g, prev, d, ok = play(guid, g, prev, TIP1_LEAVE)
        guid, g, prev, d, ok = play(guid, g, prev, TO_TIP2 + [4, 4])
        for a_ in [3, 3, 3, 3, 1, 1, 1, 1, 1, 4, 4]:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        p("retry at", (prev["cx"], prev["cy"]), e8(g)["n"])
        # Attempt B: R into (22,34)
        d = act_raw(guid, 4)
        trials.append({"try": "R_from_16", "meta": {k: d.get(k) for k in d if k != "frame"}})
        p("try R", trials[-1]["meta"])
        if "guid" in d:
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            p("  pos", (prev["cx"], prev["cy"]), "lv", d.get("levels_completed"))
            if (d.get("levels_completed") or 0) > 2:
                CLEAR.write_text(json.dumps({"cleared": True, "method": "R_from_16"}, indent=2), encoding="utf-8")
                out["cleared"] = True
            # then U toward goal
            for a_ in [1, 1, 1, 3, 1]:
                d2 = act_raw(guid, a_)
                p("  next", a_, {k: d2.get(k) for k in d2 if k != "frame"})
                if "guid" not in d2:
                    trials.append({"try": f"afterR_A{a_}", "meta": {k: d2.get(k) for k in d2 if k != "frame"}})
                    break
                guid = d2["guid"]
                g = plane(d2)
                prev = actor(g, prev)
                p("    pos", (prev["cx"], prev["cy"]), "lv", d2.get("levels_completed"))
                if (d2.get("levels_completed") or 0) > 2:
                    CLEAR.write_text(
                        json.dumps({"cleared": True, "method": "R_then_U", "pos": (prev["cx"], prev["cy"])}, indent=2),
                        encoding="utf-8",
                    )
                    out["cleared"] = True
                    break

    # Attempt C: from (10,34) R,R,R
    if not out.get("cleared"):
        guid, g, prev = enter_l3()
        guid, g, prev, d, ok = tip1_latch(guid, g, prev)
        guid, g, prev, d, ok = play(guid, g, prev, TO_TIP2 + [5, 5])
        guid, g, prev, d, ok = play(guid, g, prev, TIP1_LEAVE)
        guid, g, prev, d, ok = play(guid, g, prev, TO_TIP2 + [4, 4])
        for a_ in [3, 3, 3, 3, 1, 1, 1, 1, 1, 4]:  # end (10,34) pend R
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        p("C start", (prev["cx"], prev["cy"]))
        for a_ in [4, 4, 4]:  # 10→16→22→28?
            d = act_raw(guid, a_)
            meta = {k: d.get(k) for k in d if k != "frame"}
            p("C A4", meta.get("error"), meta if "guid" not in d else None)
            if "guid" not in d:
                trials.append({"try": "C_RRR", "meta": meta})
                break
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            p("  ", (prev["cx"], prev["cy"]), "lv", d.get("levels_completed"), "e8", e8(g)["n"])
            if (d.get("levels_completed") or 0) > 2:
                out["cleared"] = True
                CLEAR.write_text(json.dumps({"cleared": True, "method": "C_RRR"}, indent=2), encoding="utf-8")
                break

    out["trials"] = trials
    out["cleared"] = bool(out.get("cleared"))
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING", "L3_CLEAR" if out["cleared"] else "L3_APPROACH", out.get("cleared"))
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
