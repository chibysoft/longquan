"""g50t L3: dump frame while standing at (52,16) after latch; compare gate.

Also confirm-sweep: visit each closure cell, retest (52,16) DOWN.

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

OUT = ROOT / "tests/fixtures/g50t_l3_gate_live.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]

# flush-BFS closure (from recon)
CLOSURE = [
    (34, 34),
    (40, 34),
    (34, 28),
    (34, 22),
    (34, 16),
    (34, 10),
    (28, 10),
    (22, 10),
    (16, 10),
    (10, 10),
    (10, 16),
    (10, 22),
    (40, 10),
    (46, 10),
    (52, 10),
    (52, 16),
]


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
        for a_ in seq:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, True
        return guid, g, prev, False

    def latch(guid, g, prev):
        guid, g, prev, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if ok:
            return guid, g, prev, True
        guid, g, prev, ok = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        return guid, g, prev, ok

    def go_5216(guid, g, prev):
        guid, g, prev, ok = play(
            guid, g, prev, [1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4]
        )
        for a_ in (4, 4, 2, 2):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        return guid, g, prev

    def test_down(guid, g, prev, n=4):
        """Settle-ish then try D; return whether y increased past 16."""
        before = (prev["cx"], prev["cy"]) if prev else None
        moved_to = None
        for i in range(n):
            d = act(guid, 2)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            after = (prev["cx"], prev["cy"]) if prev else None
            if after and before and after[1] > before[1] + 3:
                moved_to = after
            if after and after[1] >= 22:
                return guid, g, prev, True, after, d.get("levels_completed")
        return guid, g, prev, False, (prev["cx"], prev["cy"]) if prev else None, d.get("levels_completed")

    out = {"cleared": False}
    cleared = False

    # --- A: dump frame at gate ---
    p("## gate live dump")
    guid, g, prev = enter_l3()
    guid, g, prev, _ = latch(guid, g, prev)
    g_latch = g.copy()
    guid, g, prev = go_5216(guid, g, prev)
    p("  at gate", prev, "e8", e8(g)["n"])
    gate_patch = g[14:26, 48:56]
    latch_patch = g_latch[14:26, 48:56]
    p("  gate patch while standing:\n", gate_patch)
    p("  same region at latch pos:\n", latch_patch)
    p("  ndiff region", int(np.sum(gate_patch != latch_patch)))
    # full body ndiff
    p("  body ndiff vs latch-pos frame", int(np.sum(g[1:63] != g_latch[1:63])))
    OUT_FRAME = ROOT / "tests/fixtures/g50t_l3_gate5216_frame.json"
    OUT_FRAME.write_text(
        json.dumps(
            {
                "actor": prev,
                "e8": e8(g)["n"],
                "c11": int(np.sum(g == 11)),
                "patch_14_26_48_56": gate_patch.tolist(),
                "frame": g.tolist(),
            },
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    p("  wrote", OUT_FRAME)
    # try D and log
    guid, g, prev, opened, pos, lv = test_down(guid, g, prev, n=6)
    p("  DOWN open?", opened, "pos", pos, "lv", lv)
    out["gate_live"] = {
        "actor": prev,
        "opened": opened,
        "pos": pos,
        "ndiff_vs_latchpos": int(np.sum(gate_patch != latch_patch)),
        "patch_unique": sorted(set(gate_patch.ravel().tolist())),
    }
    if opened:
        p("  ** GATE OPEN without confirm — continue hunt")
        # greedy to goal
        for _ in range(30):
            if not prev:
                break
            cx, cy = prev["cx"], prev["cy"]
            if abs(cx - 22) < 4 and abs(cy - 22) < 4:
                p("  near goal", prev, "lv", lv)
            tx, ty = (22.0, 22.0)
            dx, dy = tx - cx, ty - cy
            aid = (4 if dx > 0 else 3) if abs(dx) >= abs(dy) else (2 if dy > 0 else 1)
            b = (cx, cy)
            for a_ in (aid, aid):
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
            a = (prev["cx"], prev["cy"]) if prev else None
            p("  g", b, "->", a, "A", aid, "lv", d.get("levels_completed"))
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                CLEAR.write_text(
                    json.dumps({"cleared": True, "method": "gate_was_open"}, indent=2, default=str),
                    encoding="utf-8",
                )
                break
            if a == b:
                break

    # --- B: confirm sweep — visit each closure cell then retest gate ---
    if not cleared:
        p("## confirm sweep")
        # naive nav sequences from (34,34) latch end toward each cell
        nav = {
            (34, 34): [],
            (40, 34): [4, 4],
            (34, 28): [1, 1],
            (34, 22): [1, 1, 3, 3],
            (34, 16): [1, 1, 1, 1],
            (34, 10): [1, 1, 1, 1, 1, 1],
            (28, 10): [1, 1, 1, 1, 1, 1, 3, 3],
            (22, 10): [1, 1, 1, 1, 1, 1, 3, 3, 3, 3],
            (16, 10): [1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 3],
            (10, 10): [1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 3, 3, 3],
            (10, 16): [1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2],
            (10, 22): [1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2],
            (40, 10): [1, 1, 1, 1, 1, 1, 4, 4],
            (46, 10): [1, 1, 1, 1, 1, 1, 4, 4, 4, 4],
            (52, 10): [1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4],
            (52, 16): [1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2],
        }
        sweep = []
        for cell in CLOSURE:
            seq = nav.get(cell)
            if seq is None:
                continue
            p(f"  -- confirm @{cell}")
            guid, g, prev = enter_l3()
            guid, g, prev, _ = latch(guid, g, prev)
            if seq:
                guid, g, prev, ok = play(guid, g, prev, seq)
                if ok:
                    cleared = True
                    break
            # settle with a noop-ish double of last intent
            if seq:
                last = seq[-1]
                for a_ in (last, last):
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
            at = (int(round(prev["cx"])), int(round(prev["cy"]))) if prev else None
            e_here = e8(g)["n"]
            p("    stood", at, "e8", e_here)
            # now go test gate (fresh path from here may be long — reset latch+gate each time is safer)
            # cheaper: from current, navigate to gate if possible; else re-latch go_5216
            guid, g, prev = enter_l3()
            guid, g, prev, _ = latch(guid, g, prev)
            if seq:
                guid, g, prev, _ = play(guid, g, prev, seq)
                for a_ in (seq[-1], seq[-1]) if seq else ():
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
            # return to latch base then gate — encode: from wherever, use absolute go via top
            # Simplest reliable: after standing confirm, full re-path to gate from known latch end
            # Re-do: latch, stand confirm, then TO gate from (34,34)-relative is messy if not at 3434.
            # Instead: latch → stand confirm → die? no.
            # Just: latch → confirm seq → then append path to gate from that cell.
            to_gate_from = {
                (34, 34): [1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2],
                (40, 34): [3, 3, 1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2],
                (34, 28): [1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2],
                (34, 22): [1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2],
                (34, 16): [1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2],
                (34, 10): [4, 4, 4, 4, 4, 4, 4, 4, 2, 2],
                (28, 10): [4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2],
                (22, 10): [4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2],
                (16, 10): [4] * 12 + [2, 2],
                (10, 10): [4] * 14 + [2, 2],
                (10, 16): [1, 1, 4] * 0 + [1, 1] + [4] * 14 + [2, 2],
                (10, 22): [1, 1, 1, 1] + [4] * 14 + [2, 2],
                (40, 10): [4, 4, 4, 4, 2, 2],
                (46, 10): [4, 4, 2, 2],
                (52, 10): [2, 2],
                (52, 16): [],
            }
            # fresh run: latch, confirm, to gate, test
            guid, g, prev = enter_l3()
            guid, g, prev, _ = latch(guid, g, prev)
            if seq:
                guid, g, prev, _ = play(guid, g, prev, seq)
            tg = to_gate_from.get(cell, [1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2])
            if tg:
                guid, g, prev, _ = play(guid, g, prev, tg)
            # ensure at y16: extra D settle
            for a_ in (4, 4, 2, 2):
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
            gate_at = (prev["cx"], prev["cy"]) if prev else None
            guid, g, prev, opened, pos, lv = test_down(guid, g, prev, n=5)
            p("    gate", gate_at, "open", opened, "->", pos, "e8", e8(g)["n"], "lv", lv)
            sweep.append(
                {
                    "confirm": cell,
                    "stood": at,
                    "gate_at": gate_at,
                    "opened": opened,
                    "after": pos,
                    "e8": e8(g)["n"],
                    "lv": lv,
                }
            )
            if opened:
                p("  *** CONFIRM OPENED GATE", cell)
                # try reach goal
                for _ in range(25):
                    if not prev:
                        break
                    cx, cy = prev["cx"], prev["cy"]
                    dx, dy = 22 - cx, 22 - cy
                    aid = (4 if dx > 0 else 3) if abs(dx) >= abs(dy) else (2 if dy > 0 else 1)
                    for a_ in (aid, aid):
                        d = act(guid, a_)
                        guid = d["guid"]
                        g = plane(d)
                        prev = actor(g, prev)
                    if (d.get("levels_completed") or 0) > 2:
                        cleared = True
                        CLEAR.write_text(
                            json.dumps(
                                {"cleared": True, "method": f"confirm_{cell}", "sweep": sweep},
                                indent=2,
                                default=str,
                            ),
                            encoding="utf-8",
                        )
                        break
                break
            if (lv or 0) > 2:
                cleared = True
                break
        out["sweep"] = sweep

    # --- C: e8=92 shrink scan on closure (no latch) ---
    if not cleared:
        p("## prelatch shrink scan")
        shrinks = []
        guid, g, prev = enter_l3()
        # path covering closure roughly
        scan_seq = (
            [1, 1, 1, 1]
            + [4, 4, 4, 4]
            + [2, 2, 2, 2, 2, 2]
            + [4, 4]
            + [3, 3]
            + [1, 1, 1, 1, 1, 1]
            + [4] * 10
            + [2, 2, 2, 2]
            + [3] * 8
        )
        e_prev = e8(g)["n"]
        for a_ in scan_seq:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            e_now = e8(g)["n"]
            if e_now < e_prev:
                p(
                    "  SHRINK",
                    (prev["cx"], prev["cy"]) if prev else None,
                    e_prev,
                    "->",
                    e_now,
                    "via A",
                    a_,
                )
                shrinks.append(
                    {
                        "actor": prev,
                        "e8": [e_prev, e_now],
                        "a": a_,
                    }
                )
            e_prev = e_now
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                break
        out["prelatch_shrinks"] = shrinks

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_CONFIRM_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
