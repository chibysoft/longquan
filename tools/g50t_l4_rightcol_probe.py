"""g50t L4: persist36 @ (34,22) → east right-col → down c15 → west to (10,52).

Do NOT detour to (10,40) first. tags=["g50t_recon"]
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

OUT = ROOT / "tests/fixtures/g50t_l4_rightcol_probe.json"
FRAME = ROOT / "tests/fixtures/g50t_l4_rightcol_frame.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]
TIP_A5 = [2, 2, 2, 4, 2, 5, 5]
TIP_LEAVE = [2, 2, 2, 4, 2, 1, 1]
# after leave: (34,22) pend U — flush with noop-ish then R east
# Prefer: consume pending U then R R toward 40/52, D down
EAST_DOWN = [1, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3]


def p(*a, **k):
    print(*a, **k, flush=True)


def einfo(g):
    e = dict(e8(g))
    ys, xs = np.where(g == 8)
    if len(xs):
        e.update(xmin=int(xs.min()), xmax=int(xs.max()), ymin=int(ys.min()), ymax=int(ys.max()))
    return e


def cell_tags(g, x, y):
    sub = g[max(0, int(y) - 2) : int(y) + 3, max(0, int(x) - 2) : int(x) + 3]
    return {
        "n5": int((sub == 5).sum()),
        "n15": int((sub == 15).sum()),
        "n8": int((sub == 8).sum()),
        "n9": int((sub == 9).sum()),
        "n0": int((sub == 0).sum()),
    }


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
    nact = [0]
    log = []

    def reset():
        return s.post(
            f"{BASE}/api/cmd/RESET",
            headers=H(key, True),
            json={"card_id": card, "game_id": gid},
            timeout=30,
        ).json()

    def act(guid, aid):
        nact[0] += 1
        d = s.post(
            f"{BASE}/api/cmd/ACTION{aid}",
            headers=H(key, True),
            json={"game_id": gid, "guid": guid},
            timeout=30,
        ).json()
        if "guid" not in d:
            p("  FAIL", nact[0], {k: d.get(k) for k in d if k != "frame"})
        return d

    def play(guid, g, prev, seq, stop_lv=None, quiet=True):
        d = {"guid": guid}
        for a_ in seq:
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, False, True
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if not quiet:
                p(" ", a_, (prev["cx"], prev["cy"]) if prev else None, "e8", e8(g)["n"], "lv", d.get("levels_completed"), "n", nact[0])
            lv = d.get("levels_completed") or 0
            if stop_lv is not None and lv >= stop_lv:
                return guid, g, prev, d, True, False
            if lv > 3:
                return guid, g, prev, d, True, False
        return guid, g, prev, d, False, False

    def boot_persist34():
        d = reset()
        nact[0] = 0
        guid = d["guid"]
        g = plane(d)
        prev = None
        guid, g, prev, d, ok, dead = play(guid, g, prev, L1_SEQ + [2] * 4 + [4] * 8, stop_lv=1)
        d = act(guid, 3)
        guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)
        guid, g, prev, d, ok, dead = play(guid, g, prev, TO_2840 + L2_ROUTE, stop_lv=2)
        d = act(guid, 3)
        guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)
        guid, g, prev, d, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if (d.get("levels_completed") or 0) < 3 and not dead:
            guid, g, prev, d, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        guid, g, prev, d, ok, dead = play(guid, g, prev, TO_TIP2 + [5, 5])
        if (d.get("levels_completed") or 0) < 3 and not dead:
            guid, g, prev, d, ok, dead = play(guid, g, prev, TIP1_LEAVE)
            guid, g, prev, d, ok, dead = play(guid, g, prev, L3_WEST_CLEAR, stop_lv=3)
        d = act(guid, 4)
        guid, g, prev = d["guid"], plane(d), actor(plane(d), None)
        guid, g, prev, d, ok, dead = play(guid, g, prev, TIP_A5 + TIP_LEAVE, quiet=False)
        ok = e8(g)["n"] == 36
        p("persist", ok, (prev["cx"], prev["cy"]), e8(g)["n"], "nact", nact[0], "tags", cell_tags(g, prev["cx"], prev["cy"]))
        return guid, g, prev, d, ok

    def slog(label, guid, g, prev, seq):
        d = {"guid": guid}
        for a_ in seq:
            be = e8(g)["n"]
            before = (prev["cx"], prev["cy"])
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, True
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            pos = (prev["cx"], prev["cy"])
            de = e8(g)["n"] - be
            tags = cell_tags(g, pos[0], pos[1])
            rec = {"label": label, "a": a_, "from": before, "to": pos, "e8": e8(g)["n"], "de": de, "lv": d.get("levels_completed"), "tags": tags}
            log.append(rec)
            moved = before != pos
            p(f"  {label}", a_, before, "->", pos, "e8", e8(g)["n"], "mv", moved, "lv", d.get("levels_completed"), tags)
            if (d.get("levels_completed") or 0) > 3:
                p("  *** CLEAR")
                return guid, g, prev, d, False
        return guid, g, prev, d, False

    guid, g, prev, d, ok = boot_persist34()
    if not ok:
        OUT.write_text(json.dumps({"ok": False}, indent=2), encoding="utf-8")
        return

    # Phase 1: from (34,22) flush pending U, go R to 40/46/52, then D
    p("## east from 34,22")
    # sequences to try: flush U then east
    seqs = [
        ("flush_R_D", [1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3]),
        # if stuck, alternate via (40,16) top skip hole
    ]
    guid, g, prev, d, dead = slog("E1", guid, g, prev, seqs[0][1])
    FRAME.write_text(
        json.dumps({"frame": d.get("frame"), "pos": (prev["cx"], prev["cy"]), "e8": einfo(g), "log": log}, default=str),
        encoding="utf-8",
    )
    cleared = (d.get("levels_completed") or 0) > 3

    if not cleared and (prev["cx"], prev["cy"])[0] < 40:
        # stuck — try U to y16 then path (28,16) can't; from wherever go to (40,22)
        p("## retry via 40,22 corridor")
        guid, g, prev, d, ok = boot_persist34()
        if ok:
            # pending U at (34,22): U executes -> (34,16)? but (34,16) is hole — may noop
            # better: L to (28,22), U (28,16), U (28,10), then can't cross 34 hole
            # From (34,22) R should work to (40,22) per frame map
            guid, g, prev, d, dead = slog(
                "E2",
                guid,
                g,
                prev,
                [
                    4,  # may execute pending U first
                    4,
                    4,
                    4,
                    2,
                    4,
                    2,
                    4,
                    2,
                    2,
                    2,
                    2,
                    2,
                    3,
                    3,
                    3,
                    3,
                    3,
                    3,
                    3,
                    1,
                    1,
                ],
            )
            cleared = (d.get("levels_completed") or 0) > 3

    # Phase hold-shrink pierce: stand tip e8=36 WITHOUT leave-latch path — 
    # actually try BEFORE A5: tip step only then east while hold? Skip if cleared.

    if not cleared:
        p("## hold-shrink pierce (no A5 latch)")
        # re-enter L4, step tip for shrink, try east on hold without A5
        d = reset()
        nact[0] = 0
        guid = d["guid"]
        g = plane(d)
        prev = None
        guid, g, prev, d, ok, dead = play(guid, g, prev, L1_SEQ + [2] * 4 + [4] * 8, stop_lv=1)
        d = act(guid, 3)
        guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)
        guid, g, prev, d, ok, dead = play(guid, g, prev, TO_2840 + L2_ROUTE, stop_lv=2)
        d = act(guid, 3)
        guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)
        guid, g, prev, d, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if (d.get("levels_completed") or 0) < 3 and not dead:
            guid, g, prev, d, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        guid, g, prev, d, ok, dead = play(guid, g, prev, TO_TIP2 + [5, 5])
        if (d.get("levels_completed") or 0) < 3 and not dead:
            guid, g, prev, d, ok, dead = play(guid, g, prev, TIP1_LEAVE)
            guid, g, prev, d, ok, dead = play(guid, g, prev, L3_WEST_CLEAR, stop_lv=3)
        d = act(guid, 4)
        guid, g, prev = d["guid"], plane(d), actor(plane(d), None)
        # tip step ONLY (no A5): [2,2,2,4,2] lands tip with shrink
        guid, g, prev, d, ok, dead = play(guid, g, prev, [2, 2, 2, 4, 2, 2], quiet=False)
        p("hold?", (prev["cx"], prev["cy"]), e8(g)["n"])
        # try R while on/near tip with shrink held
        guid, g, prev, d, dead = slog("H", guid, g, prev, [4, 4, 4, 1, 4, 2, 4, 2, 2, 2, 2, 2])
        cleared = (d.get("levels_completed") or 0) > 3

    result = {
        "cleared": cleared,
        "final_pos": (prev["cx"], prev["cy"]) if prev else None,
        "final_e8": einfo(g) if g is not None else None,
        "lv": d.get("levels_completed") if d else None,
        "nact": nact[0],
        "log": log,
    }
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    p("READING", {k: result[k] for k in result if k != "log"})
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
