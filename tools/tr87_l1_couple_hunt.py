"""tr87 L1: cross-slot coupling; try match bottom to top7 column; submit hunts.

tags=["tr87_recon"]
"""
from __future__ import annotations

import json
import sys
from itertools import product
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.tr87_recon_probe import Sess, plane  # noqa: E402

OUT = ROOT / "tests/fixtures/tr87_l1_couple_hunt.json"
SLOTS = (15, 22, 29, 36, 43)


def bg(g, si):
    x0 = SLOTS[si]
    return tuple(int(v) for v in g[52:57, x0 : x0 + 5].ravel())


def all_b(g):
    return [bg(g, i) for i in range(5)]


def sel(g):
    xs = [int(x) for y, x in np.argwhere(g == 0)]
    if not xs:
        return None
    return int(np.argmin([abs(min(xs) - s) for s in SLOTS]))


def move(sess, g, ti):
    acts = []
    for _ in range(8):
        cur = sel(g)
        if cur == ti:
            return g, acts, True
        df = (ti - cur) % 5
        db = (cur - ti) % 5
        a = 4 if df <= db else 3
        d = sess.action(f"ACTION{a}")
        g = plane(d["frame"])
        acts.append(a)
    return g, acts, sel(g) == ti


def asc(sig):
    a = np.array(sig).reshape(5, 5)
    return ["".join(str(int(v)) for v in r) for r in a]


def main():
    sess = Sess(_api_key())
    out = {}
    try:
        sess.open()
        # ---- coupling: flip slot0, watch all slots ----
        d = sess.reset()
        g0 = plane(d["frame"])
        b0 = all_b(g0)
        d = sess.action("ACTION1")
        g1 = plane(d["frame"])
        b1 = all_b(g1)
        couple = [b0[i] != b1[i] for i in range(5)]
        print("ACT1 on slot0 changes slots:", couple)
        out["couple_act1_slot0"] = couple

        # flip slot1
        d = sess.reset()
        g = plane(d["frame"])
        g, _, _ = move(sess, g, 1)
        b0 = all_b(g)
        d = sess.action("ACTION1")
        g = plane(d["frame"])
        b1 = all_b(g)
        couple1 = [b0[i] != b1[i] for i in range(5)]
        print("ACT1 on slot1 changes slots:", couple1)
        out["couple_act1_slot1"] = couple1

        # ---- catalog top7 ----
        d = sess.reset()
        g = plane(d["frame"])
        top7 = {}
        for y0 in (4, 13, 22):
            for x0 in (22, 46):
                patch = g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6]
                top7[(x0, y0)] = tuple(int(v) for v in patch.ravel())

        # ---- For each slot, steps of ACT1 to hit each reachable top7 ----
        # Build per-slot: map sig -> min presses of ACT1 from reset (on that slot)
        slot_maps = []
        for si in range(5):
            d = sess.reset()
            g = plane(d["frame"])
            g, _, _ = move(sess, g, si)
            start = bg(g, si)
            m = {start: 0}
            for step in range(1, 8):
                d = sess.action("ACTION1")
                g = plane(d["frame"])
                sig = bg(g, si)
                if sig not in m:
                    m[sig] = step
                if sig == start and step > 0:
                    break
            # also ACT2 direction
            d = sess.reset()
            g = plane(d["frame"])
            g, _, _ = move(sess, g, si)
            start = bg(g, si)
            for step in range(1, 8):
                d = sess.action("ACTION2")
                g = plane(d["frame"])
                sig = bg(g, si)
                if sig not in m or step < m[sig]:
                    m[sig] = -step  # negative => ACT2
                if sig == start and step > 0:
                    break
            slot_maps.append(m)
            reachable_t7 = [p for p, s in top7.items() if s in m]
            print(f"slot{si} reachable top7: {reachable_t7} alphabet={len(m)}")

        out["reachable_top7"] = {
            str(si): [p for p, s in top7.items() if s in slot_maps[si]] for si in range(5)
        }

        # ---- Hypothesis: set each bottom slot equal to top7@(22, y) for y in rows
        # only 3 left-col top7; 5 slots — no.
        # Hypothesis: make all 5 identical to one chosen glyph in shared alphabet
        print("\n## all-equal hunts (shared alphabet of slot0)")
        d = sess.reset()
        g = plane(d["frame"])
        # get slot0 alphabet ordered by ACT1
        g, _, _ = move(sess, g, 0)
        start = bg(g, 0)
        alpha = [start]
        for _ in range(6):
            d = sess.action("ACTION1")
            g = plane(d["frame"])
            sig = bg(g, 0)
            if sig == start:
                break
            alpha.append(sig)
        print("alphabet n", len(alpha))

        results = []
        # For each target glyph in alpha, try set slots 0,2,3,4 (same alpha) to it;
        # slot1 has different alphabet — set to its start or cycle through its targets
        for ti, target in enumerate(alpha):
            d = sess.reset()
            g = plane(d["frame"])
            lv0 = d.get("levels_completed")
            actions = []
            # slots that share alphabet with 0: 0,3,4 (and partially 2)
            for si in (0, 2, 3, 4):
                if target not in slot_maps[si]:
                    continue
                steps = slot_maps[si][target]
                g, nav, ok = move(sess, g, si)
                actions.extend(nav)
                if steps > 0:
                    for _ in range(steps):
                        d = sess.action("ACTION1")
                        g = plane(d["frame"])
                        actions.append(1)
                elif steps < 0:
                    for _ in range(-steps):
                        d = sess.action("ACTION2")
                        g = plane(d["frame"])
                        actions.append(2)
            lv1 = d.get("levels_completed")
            bots = all_b(g)
            eq = sum(1 for b in bots if b == target)
            cleared = int(lv1 or 0) > int(lv0 or 0)
            print(f"  target#{ti} eq={eq}/5 lv {lv0}->{lv1} nact={len(actions)} clear={cleared}")
            results.append({"ti": ti, "eq": eq, "lv0": lv0, "lv1": lv1, "nact": len(actions), "cleared": cleared})
            if cleared:
                break
        out["all_equal"] = results

        # ---- Hypothesis: bottom mirrors left column top7 vertically into 3 slots
        # Put top7(22,4)->slot0, (22,13)->slot1, (22,22)->slot2; leave 3,4
        print("\n## left-col top7 into slots 0,1,2")
        plan = [
            (0, top7[(22, 4)]),
            (1, top7[(22, 13)]),
            (2, top7[(22, 22)]),
        ]
        d = sess.reset()
        g = plane(d["frame"])
        lv0 = d.get("levels_completed")
        actions = []
        ok_all = True
        for si, tgt in plan:
            if tgt not in slot_maps[si]:
                print(f"  slot{si} CANNOT reach target")
                ok_all = False
                continue
            steps = slot_maps[si][tgt]
            g, nav, _ = move(sess, g, si)
            actions.extend(nav)
            flip = 1 if steps >= 0 else 2
            for _ in range(abs(steps)):
                d = sess.action(f"ACTION{flip}")
                g = plane(d["frame"])
                actions.append(flip)
            print(f"  slot{si} steps={steps} match={bg(g,si)==tgt}")
        lv1 = d.get("levels_completed")
        print(f"  lv {lv0}->{lv1} ok_all_reachable check done")
        out["left_col_plan"] = {
            "ok_targets_in_map": ok_all,
            "lv0": lv0,
            "lv1": lv1,
            "actions": actions,
            "bottom": [asc(s) for s in all_b(g)],
        }

        # Check reachability for left col plan
        for si, tgt in plan:
            print(f"  reach slot{si}: {tgt in slot_maps[si]}")

        # ---- slot2 special: can it reach top7(22,22)? ----
        print("slot2 has top7(22,22)?", top7[(22, 22)] in slot_maps[2])
        print("slot1 has top7(22,13)?", top7[(22, 13)] in slot_maps[1])
        print("slot0 has top7(22,4)?", top7[(22, 4)] in slot_maps[0])

        # ---- Try: set slot0 to top7(22,4), slot1 to top7(22,13) only (partial)
        d = sess.reset()
        g = plane(d["frame"])
        lv0 = d.get("levels_completed")
        actions = []
        for si, key in [(0, (22, 4)), (1, (22, 13))]:
            tgt = top7[key]
            steps = slot_maps[si][tgt]
            g, nav, _ = move(sess, g, si)
            actions.extend(nav)
            flip = 1 if steps >= 0 else 2
            for _ in range(abs(steps)):
                d = sess.action(f"ACTION{flip}")
                g = plane(d["frame"])
                actions.append(flip)
        # also try right column into slots 3,4 if reachable
        for si, key in [(3, (46, 4)), (4, (46, 13)), (2, (46, 22))]:
            tgt = top7[key]
            if tgt not in slot_maps[si]:
                print(f"  skip slot{si} no {key}")
                continue
            steps = slot_maps[si][tgt]
            g, nav, _ = move(sess, g, si)
            actions.extend(nav)
            flip = 1 if steps >= 0 else 2
            for _ in range(abs(steps)):
                d = sess.action(f"ACTION{flip}")
                g = plane(d["frame"])
                actions.append(flip)
            print(f"  set slot{si} <- {key}")
        lv1 = d.get("levels_completed")
        print(f"partial top7 map lv {lv0}->{lv1}")
        out["partial_top7"] = {"lv0": lv0, "lv1": lv1, "actions": actions}

        # ---- Brute: for slot1 alone, walk full cycle watching levels ----
        print("\n## slot1 full cycle levels watch")
        d = sess.reset()
        g = plane(d["frame"])
        g, _, _ = move(sess, g, 1)
        lv_path = [d.get("levels_completed")]
        for i in range(8):
            d = sess.action("ACTION1")
            g = plane(d["frame"])
            lv_path.append(d.get("levels_completed"))
        print("  lv path", lv_path)

        # ---- Make bottom match RESET order but rotated / sorted?
        # Try setting all slots to slot0's reset glyph if possible
        print("\n## unify to B0 reset glyph")
        d = sess.reset()
        g = plane(d["frame"])
        target = bg(g, 0)
        lv0 = d.get("levels_completed")
        actions = []
        for si in range(5):
            if target not in slot_maps[si]:
                print(f"  slot{si} cannot")
                continue
            steps = slot_maps[si][target]
            g, nav, _ = move(sess, g, si)
            actions.extend(nav)
            flip = 1 if steps >= 0 else 2
            for _ in range(abs(steps)):
                d = sess.action(f"ACTION{flip}")
                g = plane(d["frame"])
                actions.append(flip)
        lv1 = d.get("levels_completed")
        print(f"  lv {lv0}->{lv1} matches={[bg(g,i)==target for i in range(5)]}")
        out["unify_b0"] = {"lv0": lv0, "lv1": lv1, "match": [bg(g, i) == target for i in range(5)]}

        reading = "L1_CLEAR" if any(
            int(r.get("lv1") or 0) > int(r.get("lv0") or 0) for r in results
        ) or int(out.get("partial_top7", {}).get("lv1") or 0) > 0 else "COUPLE_PARTIAL"
        # fix reading
        cleared_any = False
        for key in ("partial_top7", "unify_b0", "left_col_plan"):
            e = out.get(key) or {}
            if int(e.get("lv1") or 0) > int(e.get("lv0") or 0):
                cleared_any = True
        if any(r.get("cleared") for r in results):
            cleared_any = True
        out["reading"] = "L1_CLEAR" if cleared_any else "COUPLE_PARTIAL"
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("READING:", out["reading"])
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
