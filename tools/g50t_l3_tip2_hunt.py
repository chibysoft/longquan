"""g50t L3: hunt 2nd tip after BFS — hold tip1 then D onto (40,40) / latch variants.

BFS seated: after persist-76 latch, reachable only 16 cells; no tip2; no (22,28).
Offline: remaining e8 = left~(22,40) n46 + right~(40,44) n30; tip cands (40,40)/(22,34).
Hypothesis: color-2 scar after latch blocks tip→D; HOLD tip (no A5) may allow D→(40,40).

tags=["g50t_recon"] — opens OWN scorecard (do not reuse parent card).
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

OUT = ROOT / "tests/fixtures/g50t_l3_tip2_hunt.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]


def p(*a, **k):
    print(*a, **k, flush=True)


def uniq(log):
    u = []
    for r in log:
        if r.get("actor"):
            t = (r["actor"]["cx"], r["actor"]["cy"])
            if not u or u[-1] != t:
                u.append(t)
    return u


def center_grid(g):
    return {y: {x: int(g[y, x]) for x in range(10, 55, 6)} for y in range(10, 55, 6)}


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
        d = act(guid, 3)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        return guid, g, prev, d

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
                    "c2": int(np.sum(g == 2)),
                    "c11": int(np.sum(g == 11)),
                    "lv": d.get("levels_completed"),
                }
            )
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, log, True
        return guid, g, prev, d, log, False

    def flush(guid, g, prev, aid, n=2):
        log = []
        for _ in range(n):
            d = act(guid, aid)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            log.append(
                {
                    "a": aid,
                    "actor": prev,
                    "e8": e8(g)["n"],
                    "c2": int(np.sum(g == 2)),
                    "lv": d.get("levels_completed"),
                }
            )
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, log, True
        return guid, g, prev, d, log, False

    out = {"trials": {}, "cleared": False}
    cleared = False

    # --- A: HOLD tip (no A5), probe dirs + patch ---
    p("## hold_tip_probe")
    guid, g, prev, d = enter_l3()
    guid, g, prev, d, log, ok = play(guid, g, prev, TO_3434 + [4, 4])
    p("  on tip", prev, "e8", e8(g)["n"], "c2", int(np.sum(g == 2)))
    if prev:
        cx, cy = int(prev["cx"]), int(prev["cy"])
        patch = g[cy - 3 : cy + 4, cx - 3 : cx + 4]
        p("  patch\n", patch)
        out["hold_tip"] = {
            "actor": prev,
            "e8": e8(g)["n"],
            "c2": int(np.sum(g == 2)),
            "patch": patch.tolist(),
            "centers": center_grid(g),
        }
    hold_dirs = {}
    for aid, dn in ((1, "U"), (2, "D"), (3, "L"), (4, "R")):
        guid, g, prev, d = enter_l3()
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_3434 + [4, 4])
        b = (prev["cx"], prev["cy"], e8(g)["n"]) if prev else None
        guid, g, prev, d, log, ok = flush(guid, g, prev, aid, 2)
        a = (prev["cx"], prev["cy"], e8(g)["n"]) if prev else None
        p(f"  hold-{dn}", b, "->", a, "c2", int(np.sum(g == 2)))
        hold_dirs[dn] = {"from": b, "to": a, "c2": int(np.sum(g == 2)), "ok": ok}
        if a and a[2] < 76:
            p("  ** SHRINK while hold", a)
            # A5 latch 2nd
            for a5 in (5, 5):
                d = act(guid, a5)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
            p("  A5", prev, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
            hold_dirs[dn]["a5"] = {
                "actor": prev,
                "e8": e8(g)["n"],
                "lv": d.get("levels_completed"),
            }
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                CLEAR.write_text(
                    json.dumps({"cleared": True, "method": f"hold_tip_{dn}_a5"}, indent=2, default=str),
                    encoding="utf-8",
                )
        if ok:
            cleared = True
    out["trials"]["hold_dirs"] = hold_dirs

    # --- B: buffer variants onto tip then D (queue D while arriving) ---
    if not cleared:
        variants = {
            "arrive_queue_D": TO_3434 + [4, 2, 2, 2, 2],  # R into tip, pending then D
            "arrive_R_D": TO_3434 + [4, 4, 2, 2, 2, 2],
            "arrive_R_D_A5": TO_3434 + [4, 2, 5, 5],  # queue: R lands, D?, A5
            "arrive_R_D_D_A5": TO_3434 + [4, 2, 2, 5, 5],
            "hold_D_A5": TO_3434 + [4, 4, 2, 2, 5, 5],
            "hold_D4_A5": TO_3434 + [4, 4] + [2] * 4 + [5, 5],
            # latch tip1 first then try tip again D (scar present — control)
            "latch_revisit_D": TO_3434 + [4, 4, 5, 5] + TO_3434 + [4, 4, 2, 2, 2, 2],
            "latch_revisit_D_A5": TO_3434 + [4, 4, 5, 5] + TO_3434 + [4, 4, 2, 2, 5, 5],
        }
        for name, seq in variants.items():
            p(f"## {name}")
            guid, g, prev, d = enter_l3()
            guid, g, prev, d, log, ok = play(guid, g, prev, seq)
            path = uniq(log)
            e_series = [r["e8"] for r in log]
            hits = [
                (r["actor"]["cx"], r["actor"]["cy"], r["e8"])
                for r in log
                if r["actor"] and r["e8"] < 76
            ]
            p("  path", path)
            p("  e8", e_series[0], "->", e_series[-1], "min", min(e_series), "hits<76", hits)
            out["trials"][name] = {
                "path": path,
                "e_min": min(e_series),
                "e_final": e_series[-1],
                "hits": hits,
                "cleared": ok,
                "final": log[-1],
                "seq": seq,
            }
            if hits and not ok:
                # if ended on shrink cell, try A5 + persist cycle
                tip = hits[-1]
                p("  follow-up A5/persist at", tip)
                guid, g, prev, d = enter_l3()
                guid, g, prev, d, log2, ok2 = play(guid, g, prev, seq)
                for a5 in (5, 5):
                    d = act(guid, a5)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                p("  after A5", prev, e8(g)["n"], d.get("levels_completed"))
                # revisit path to tip2
                guid, g, prev, d, log3, ok3 = play(guid, g, prev, seq)
                e_on = e8(g)["n"]
                for a_ in (3, 3, 1, 1):
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                e_leave = e8(g)["n"]
                p("  leave", e_on, "->", e_leave, "at", prev)
                out["trials"][name]["persist"] = {
                    "e_on": e_on,
                    "e_leave": e_leave,
                    "actor": prev,
                    "centers": center_grid(g) if e_leave < 70 else None,
                }
                if e_leave <= 60:
                    p("  ** 2nd persist — hunt goal")
                    for target in ((22, 28), (22, 22), (16, 34), (52, 52), (28, 52)):
                        for _ in range(28):
                            if not prev:
                                break
                            cx, cy = prev["cx"], prev["cy"]
                            if abs(cx - target[0]) < 3 and abs(cy - target[1]) < 3:
                                p("  reached", target, prev, "lv", d.get("levels_completed"))
                                if (d.get("levels_completed") or 0) > 2:
                                    cleared = True
                                break
                            dx, dy = target[0] - cx, target[1] - cy
                            aid = (4 if dx > 0 else 3) if abs(dx) >= abs(dy) else (2 if dy > 0 else 1)
                            b = (cx, cy)
                            guid, g, prev, d, _, okh = flush(guid, g, prev, aid, 2)
                            a = (prev["cx"], prev["cy"]) if prev else None
                            p(f"  ->{target}", b, a, "e8", e8(g)["n"], "lv", d.get("levels_completed"))
                            if (d.get("levels_completed") or 0) > 2:
                                cleared = True
                                CLEAR.write_text(
                                    json.dumps(
                                        {
                                            "cleared": True,
                                            "method": f"{name}_persist_hunt",
                                            "end": a,
                                            "e8": e8(g)["n"],
                                        },
                                        indent=2,
                                        default=str,
                                    ),
                                    encoding="utf-8",
                                )
                                break
                            if a == b:
                                break
                        if cleared:
                            break
            if ok or cleared:
                cleared = True
                CLEAR.write_text(
                    json.dumps({"cleared": True, "method": name, "log": log, "seq": seq}, indent=2, default=str),
                    encoding="utf-8",
                )
                break

    # --- C: if hold-D worked earlier, full clear route ---
    # (covered in persist hunt above)

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_TIP2_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
