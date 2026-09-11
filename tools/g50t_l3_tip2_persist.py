"""g50t L3: tip2 A5 then same-session confirm (L2-style persist).

Hypothesis: tip2 A5 arms latch; confirm at tip1/(28,40)/(34,34) persists e8=60.
Then left-climb (10,34)->(22,34)->(22,28)->(22,22) for CLEAR.

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

OUT = ROOT / "tests/fixtures/g50t_l3_tip2_persist.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]


def p(*a, **k):
    print(*a, **k, flush=True)


def einfo(g):
    e = dict(e8(g))
    ys, xs = np.where(g == 8)
    if len(xs):
        e.update(xmin=int(xs.min()), xmax=int(xs.max()), ymin=int(ys.min()), ymax=int(ys.max()))
    return e


def show(tag, prev, g, d=None):
    p(
        f"  {tag}",
        (prev["cx"], prev["cy"]) if prev else None,
        "e8",
        einfo(g),
        "lv",
        None if d is None else d.get("levels_completed"),
    )


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

    def play(guid, g, prev, seq, quiet=False):
        log = []
        for a_ in seq:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            log.append({"a": a_, "pos": (prev["cx"], prev["cy"]) if prev else None, "e8": e8(g)["n"], "lv": d.get("levels_completed")})
            if not quiet:
                pass
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, log, True
        return guid, g, prev, d, log, False

    def tip1_latch(guid, g, prev):
        guid, g, prev, d, log, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5], quiet=True)
        if ok:
            return guid, g, prev, d, log, True
        return play(guid, g, prev, TO_3434 + [4, 4, 3, 3], quiet=True)

    def tip2_and_A5(guid, g, prev):
        guid, g, prev, d, log, ok = play(guid, g, prev, TO_TIP2, quiet=True)
        if ok:
            return guid, g, prev, d, log, True
        for a_ in (5, 5):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            log.append({"a": a_, "pos": (prev["cx"], prev["cy"]) if prev else None, "e8": e8(g)["n"], "lv": d.get("levels_completed")})
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, log, True
        return guid, g, prev, d, log, False

    out = {"cleared": False}
    cleared = False

    confirms = {
        # after tip2 A5 at spawn (10,22), e8=92
        "visit_tip1_leave": TO_3434 + [4, 4, 3, 3],  # visit tip leave to 3434, NO A5
        "visit_tip1_A5_leave": TO_3434 + [4, 4, 5, 5] + TO_3434 + [4, 4, 3, 3],
        "to_3434_only": TO_3434,
        "to_2840ish": [1, 1, 4, 4, 4, 2, 2, 2, 3, 3],
        "to_4040": TO_3434 + [4, 4, 2],
        "to_2210_down": [1, 1, 4, 4, 2, 2, 2, 2],
    }

    for name, seq in confirms.items():
        p(f"## confirm {name}")
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, ok = tip1_latch(guid, g, prev)
        show("tip1", prev, g, d)
        if e8(g)["n"] != 76:
            p("  SKIP bad tip1", e8(g)["n"])
            continue
        guid, g, prev, d, _, ok = tip2_and_A5(guid, g, prev)
        show("after_tip2_A5", prev, g, d)
        e_after = e8(g)["n"]
        guid, g, prev, d, log, ok = play(guid, g, prev, seq)
        show("after_confirm", prev, g, d)
        e_conf = e8(g)["n"]
        out[name] = {
            "e_after_A5": e_after,
            "e_confirm": e_conf,
            "pos": (prev["cx"], prev["cy"]) if prev else None,
            "path_tail": [r["pos"] for r in log[-6:]],
        }
        p("  e8", e_after, "->", e_conf, "at", out[name]["pos"])
        if ok or (d.get("levels_completed") or 0) > 2:
            cleared = True
            CLEAR.write_text(json.dumps({"cleared": True, "method": name}, indent=2), encoding="utf-8")
            break
        # if e8==60, try left climb clear
        if e_conf == 60:
            p("  PERSIST 60 — left climb clear")
            # need bottom access: re-open right with persist 60
            guid, g, prev, d, _, ok = play(guid, g, prev, TO_BOTTOM + [3, 3, 3, 3, 3, 3, 3] + [1] * 5 + [4] * 3 + [1] * 3 + [4])
            show("climb", prev, g, d)
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                CLEAR.write_text(json.dumps({"cleared": True, "method": name + "+climb"}, indent=2), encoding="utf-8")
                break

    if not cleared:
        # Direct: tip1 → tip2 hold (no A5) is useless for persist.
        # Try tip2 A5 → tip1 latch with VERBOSE
        p("## verbose tip1 after tip2 A5")
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, _ = tip1_latch(guid, g, prev)
        guid, g, prev, d, _, _ = tip2_and_A5(guid, g, prev)
        show("spawn", prev, g, d)
        for a_ in TO_3434 + [4, 4, 5, 5]:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            show(f"vA{a_}", prev, g, d)
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                break
        out["verbose_A5"] = {"pos": (prev["cx"], prev["cy"]) if prev else None, "e8": einfo(g)}
        # continue leave sequence
        if not cleared:
            for a_ in TO_3434 + [4, 4, 3, 3]:
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                show(f"v2A{a_}", prev, g, d)
            out["verbose_leave"] = {"pos": (prev["cx"], prev["cy"]) if prev else None, "e8": einfo(g)}
            p("  final e8", e8(g)["n"])

    if not cleared:
        # tip1 → tip2 NO A5 → left climb while... can't keep 60.
        # Alternate persist: die on tip2, then visit tip2 via tip1 path and leave
        p("## A5 then re-tip2 leave (need tip1 for path)")
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, _ = tip1_latch(guid, g, prev)
        guid, g, prev, d, _, _ = tip2_and_A5(guid, g, prev)
        show("dead", prev, g, d)
        # try tip1 latch verbose result; if 76, go tip2 leave
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, _ = tip1_latch(guid, g, prev)
        # WITHOUT tip2 A5 this run — instead tip2, leave, check; baseline
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_TIP2)
        show("on60", prev, g, d)
        # try confirm WITHOUT leaving: A5 is death. What about walking to tip1 WHILE... impossible.

        # NEW: from tip2 e8=60, use death that is NOT A5? Only A5 kills.
        # NEW: maybe need tip2 step BEFORE tip1 A5 latch
        p("## tip2 BEFORE tip1 latch")
        guid, g, prev = enter_l3()
        # can we reach tip2 without tip1? earlier no.
        # tip1 HOLD without persist: step tip1 (76 hold), leave restores 92 — no bottom.
        # Must tip1 persist first.

        # Try double pad: tip1 latch, tip2, leave to 28, IMMEDIATELY back to tip2, leave again — still 76.
        pass

    if not cleared:
        # CRITICAL CLEAR ATTEMPT if we can get persist another way:
        # Hold tip2 e8=60 — snake clears (22,34). Can we reach (22,34) FROM THE RIGHT/TOP
        # without leaving tip2? No.
        # BUT: maybe (22,34) is reachable from (34,34)/(10,34) if we tip2-A5-confirm first.
        #
        # Try: while on tip2, the LEFT column path is "armed" globally — test by
        # having tip2 held... can't be in two places.
        #
        # Online co-op? No.
        #
        # Last idea: tip2 persist = leave tip2 to (16,52) then U to (16,34)/(10,34) then R
        # in the SAME buffered sequence so fast that... no e8 restores on first leave frame.
        #
        # Unless restore happens only when tip2 is unoccupied at end of turn AND we check
        # after full action — always restored when we leave.
        #
        # Try leaving tip2 with A5 pending that fires on a confirm? too wild.
        #
        # Probe: tip1 latch, tip2, leave R, check e8; then immediately visit (22,34) from left
        # (will be snake). Visit (40,34) tip1 again leave — e8?
        p("## tip2 leave then tip1 re-leave")
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, _ = tip1_latch(guid, g, prev)
        guid, g, prev, d, _, _ = play(guid, g, prev, TO_TIP2)
        show("t2", prev, g, d)
        for a_ in (4, 4):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            show("leave", prev, g, d)
        # go tip1 via right col up
        for a_ in [4] * 5 + [1] * 4 + [3] * 2 + [3, 3]:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            show(f"A{a_}", prev, g, d)
            if e8(g)["n"] not in (76, 92, 60):
                p("  new e8", e8(g)["n"])
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                break
        out["revisit_tip1"] = {"pos": (prev["cx"], prev["cy"]) if prev else None, "e8": einfo(g)}

    # CLEAR ROUTE if e8 somehow 60 at (10,34) or after any confirm
    if not cleared:
        p("## attempt clear with forced tip2 hold simulation — left from bottom at e76 vs need e60")
        # Show (22,34) blocked at 76 by trying left climb R
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, _ = tip1_latch(guid, g, prev)
        seq = TO_BOTTOM + [3, 3, 3, 3, 3, 3, 3, 1, 1, 1, 1, 4, 4, 4, 1, 1, 1]
        guid, g, prev, d, log, ok = play(guid, g, prev, seq)
        path = []
        for r in log:
            if r["pos"] and (not path or path[-1] != r["pos"]):
                path.append(r["pos"])
        show("end", prev, g, d)
        out["left_at_76"] = {"path": path, "e8": einfo(g)}
        p("  path", path)
        if ok:
            cleared = True

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_TIP2_PERSIST"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
