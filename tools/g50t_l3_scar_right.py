"""g50t L3: retest (52,16) DOWN with settle; probe c2 scar; open-check.

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

OUT = ROOT / "tests/fixtures/g50t_l3_scar_right.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]


def p(*a, **k):
    print(*a, **k, flush=True)


def c2n(g):
    return int(np.sum(g[1:63] == 2))


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
                    "c2": c2n(g),
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

    # --- Trial A: careful right-col descend after latch ---
    p("## rightcol careful")
    guid, g, prev = enter_l3()
    guid, g, prev, _ = latch(guid, g, prev)
    # to (52,10): U to top, R to 52
    guid, g, prev, log, ok = play(
        guid, g, prev, [1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4]
    )
    p("  at", prev, "e8", e8(g)["n"], "c2", c2n(g))
    # settle with extra R (noop)
    for a_ in (4, 4, 4):
        d = act(guid, a_)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        p("  settleR", (prev["cx"], prev["cy"]), "a", a_)
    # NOW single-step D logging every action
    steps = []
    for i in range(16):
        before = (prev["cx"], prev["cy"])
        d = act(guid, 2)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        after = (prev["cx"], prev["cy"]) if prev else None
        row = {
            "i": i,
            "from": before,
            "to": after,
            "e8": e8(g)["n"],
            "c2": c2n(g),
            "lv": d.get("levels_completed"),
            "moved": after != before,
        }
        steps.append(row)
        p(f"  D{i}", before, "->", after, "moved", row["moved"], "e8", row["e8"], "lv", row["lv"])
        if (d.get("levels_completed") or 0) > 2:
            cleared = True
            break
        if after == before and i >= 2:
            # try L detour one step then D
            p("  try L micro then D")
            for a_ in (3, 3):
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
            p("  after L", prev)
            for j in range(4):
                b = (prev["cx"], prev["cy"])
                d = act(guid, 2)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                a = (prev["cx"], prev["cy"]) if prev else None
                p(f"  LthenD{j}", b, "->", a)
                if a == b:
                    break
            break
    out["rightcol"] = {"steps": steps, "final": prev, "e8": e8(g)["n"]}

    # --- Trial B: after latch, stand on c2 scar (revisit tip), A5 / leave / check open ---
    if not cleared:
        p("## c2 scar interact")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch(guid, g, prev)
        p("  latched", prev, "e8", e8(g)["n"], "c2", c2n(g))
        # go to tip — should stand amid c2
        guid, g, prev, log, ok = play(guid, g, prev, [4, 4, 4, 4])
        p("  on tip/scar", prev, "e8", e8(g)["n"], "c2", c2n(g))
        if prev:
            cx, cy = int(round(prev["cx"])), int(round(prev["cy"]))
            patch = g[cy - 2 : cy + 3, cx - 2 : cx + 3]
            p("  under patch\n", patch)
        # A5 on scar
        e0 = e8(g)["n"]
        c20 = c2n(g)
        for a_ in (5, 5):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        p(
            "  A5 on scar",
            prev,
            "e8",
            e0,
            "->",
            e8(g)["n"],
            "c2",
            c20,
            "->",
            c2n(g),
            "lv",
            d.get("levels_completed"),
        )
        out["scar_a5"] = {
            "e8": [e0, e8(g)["n"]],
            "c2": [c20, c2n(g)],
            "actor": prev,
            "lv": d.get("levels_completed"),
        }
        if (d.get("levels_completed") or 0) > 2:
            cleared = True

    # --- Trial C: latch, tip stand (no A5), leave via U? can't; leave L, then immediately check (52,16) down
    #     vs latch-leave without re-tip
    if not cleared:
        p("## after scar-stand (no A5) check rightcol")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch(guid, g, prev)
        # stand on tip briefly
        guid, g, prev, _, _ = play(guid, g, prev, [4, 4])
        p("  scar stand", prev, "c2", c2n(g), "e8", e8(g)["n"])
        # leave L
        guid, g, prev, _, _ = play(guid, g, prev, [3, 3])
        p("  left tip", prev, "c2", c2n(g), "e8", e8(g)["n"])
        # race to right col
        guid, g, prev, _, _ = play(
            guid, g, prev, [1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4]
        )
        p("  at right", prev)
        for a_ in (4, 4):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        for i in range(10):
            b = (prev["cx"], prev["cy"])
            d = act(guid, 2)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            a = (prev["cx"], prev["cy"]) if prev else None
            p(f"  D{i}", b, "->", a, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                break
            if a == b and i >= 1:
                break
        out["scar_then_right"] = {"final": prev, "e8": e8(g)["n"]}

    # --- Trial D: pre-latch go tip, A5 with QUEUE from (34,34): send A5 then R so A5 fires on tip
    #     already done-ish; try A5 from (34,40) if we can get there pre-latch — can't.
    #     Try: without latch, walk tip, leave, walk tip again, A5 — double touch before latch
    if not cleared:
        p("## double-touch tip before A5")
        guid, g, prev = enter_l3()
        seq = TO_3434 + [4, 4, 3, 3, 4, 4, 5, 5]
        guid, g, prev, log, ok = play(guid, g, prev, seq)
        e_series = [r["e8"] for r in log]
        p(
            "  path uniq e_min",
            min(e_series),
            "final",
            e_series[-1],
            "actor",
            prev,
            "lv",
            log[-1]["lv"],
        )
        out["double_touch"] = {
            "e_min": min(e_series),
            "e_final": e_series[-1],
            "final": log[-1],
            "ok": ok,
        }
        if ok:
            cleared = True
        # if dead, revisit for persist and try rightcol
        if prev and prev["cx"] == 10:
            guid, g, prev, _, _ = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
            p("  revisit leave", prev, "e8", e8(g)["n"], "c2", c2n(g))
            guid, g, prev, _, _ = play(
                guid, g, prev, [1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4]
            )
            for a_ in (4, 4):
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
            for i in range(8):
                b = (prev["cx"], prev["cy"])
                d = act(guid, 2)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                a = (prev["cx"], prev["cy"]) if prev else None
                p(f"  postDT D{i}", b, "->", a, "e8", e8(g)["n"])
                if a == b and i >= 1:
                    break
                if (d.get("levels_completed") or 0) > 2:
                    cleared = True
                    break

    # --- Trial E: latch then try walking onto c2 cells that aren't tip center — micro around tip
    if not cleared:
        p("## scar neighborhood after latch")
        guid, g, prev = enter_l3()
        guid, g, prev, _ = latch(guid, g, prev)
        # dump c2 bbox
        ys, xs = np.where(g == 2)
        if len(xs):
            p("  c2 bbox", int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()), "n", len(xs))
        # from (34,34) try U/D/L/R single-action map with settle between
        # already know graph; try go tip and A5 once only (one A5 not two)
        guid, g, prev, _, _ = play(guid, g, prev, [4, 4])
        p("  tip", prev, "e8", e8(g)["n"], "c2", c2n(g))
        d = act(guid, 5)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        p("  single A5 exec?", prev, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
        d = act(guid, 3)  # whatever pending
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        p("  next", prev, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
        out["single_a5"] = {"actor": prev, "e8": e8(g)["n"], "lv": d.get("levels_completed")}

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_SCAR_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    if cleared:
        CLEAR.write_text(json.dumps({"cleared": True, "via": "scar_right", "out": out}, indent=2, default=str), encoding="utf-8")
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
