"""tr87 L1: match bottom 5 glyphs to mid-band y40-46 targets (10→7 remap).

Hypothesis H5b: mid strip is the answer key; ACTION1/2 walk a shared
period-7 cycle (2 = 1^{-1}); clear when all 5 slots match.

tags=["tr87_recon"]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.tr87_recon_probe import Sess, plane  # noqa: E402

OUT = ROOT / "tests/fixtures/tr87_l1_midband_match.json"

SLOTS_X0 = (15, 22, 29, 36, 43)  # bottom interior x0
MID_FRAME_X0 = (14, 21, 28, 35, 42)  # mid 7-wide cells
GLYPH_Y0, GLYPH_Y1 = 52, 56
MID_Y0, MID_Y1 = 41, 45  # interior of mid band


def color0_x0(g):
    xs = [int(x) for y, x in np.argwhere(g == 0)]
    return min(xs) if xs else None


def slot_index(g):
    x0 = color0_x0(g)
    if x0 is None:
        return None
    return int(np.argmin([abs(x0 - s) for s in SLOTS_X0]))


def bottom_glyph(g, si):
    x0 = SLOTS_X0[si]
    return tuple(int(v) for v in g[GLYPH_Y0 : GLYPH_Y1 + 1, x0 : x0 + 5].ravel())


def mid_glyph(g, si, remap=True):
    x0 = MID_FRAME_X0[si]
    patch = g[MID_Y0 : MID_Y1 + 1, x0 + 1 : x0 + 6].copy()
    if remap:
        patch = np.where(patch == 10, 7, patch)
    return tuple(int(v) for v in patch.ravel())


def ascii5(sig):
    a = np.array(sig, dtype=int).reshape(5, 5)
    return ["".join(str(int(v)) for v in row) for row in a]


def go(sess, n):
    return sess.action(f"ACTION{n}")


def move_to_slot(sess, g, target_i):
    actions = []
    for _ in range(8):
        cur = slot_index(g)
        if cur == target_i:
            return g, actions, True
        if cur is None:
            return g, actions, False
        d_fwd = (target_i - cur) % 5
        d_bwd = (cur - target_i) % 5
        a = 4 if d_fwd <= d_bwd else 3
        d = go(sess, a)
        g = plane(d["frame"])
        actions.append(a)
    return g, actions, slot_index(g) == target_i


def collect_cycle(sess, g, si, flip, max_steps=10):
    """From current (already on slot), walk ACTION{flip} until repeat."""
    start = bottom_glyph(g, si)
    seen = {start: 0}
    seq = [start]
    for step in range(1, max_steps + 1):
        d = go(sess, flip)
        g = plane(d["frame"])
        sig = bottom_glyph(g, si)
        seq.append(sig)
        if sig in seen:
            return g, seq, step - seen[sig]
        seen[sig] = step
    return g, seq, None


def main():
    key = _api_key()
    sess = Sess(key)
    out = {}
    try:
        sess.open()
        d = sess.reset()
        g = plane(d["frame"])
        lv0 = d.get("levels_completed")

        mids = [mid_glyph(g, i) for i in range(5)]
        bots = [bottom_glyph(g, i) for i in range(5)]
        print("## mid targets (10→7)")
        for i, s in enumerate(mids):
            print(f"  M{i}")
            for line in ascii5(s):
                print("   ", line)
        print("## bottom reset")
        for i, s in enumerate(bots):
            print(f"  B{i} match_mid={s == mids[i]}")
            for line in ascii5(s):
                print("   ", line)
        out["mid"] = [ascii5(s) for s in mids]
        out["bottom_reset"] = [ascii5(s) for s in bots]
        out["reset_eq"] = [bots[i] == mids[i] for i in range(5)]

        # also try inverted ink: 5↔7 on mid after remap
        mids_inv = []
        for s in mids:
            a = np.array(s).reshape(5, 5)
            inv = np.where(a == 7, 5, np.where(a == 5, 7, a))
            mids_inv.append(tuple(int(v) for v in inv.ravel()))
        out["mid_inv"] = [ascii5(s) for s in mids_inv]

        # Per-slot: is mid (or mid_inv) in ACT1 cycle?
        plans = []
        for si in range(5):
            d = sess.reset()
            g = plane(d["frame"])
            g, nav, ok = move_to_slot(sess, g, si)
            assert ok, f"nav fail slot{si}"
            # capture ACT1 cycle from reset glyph
            g, seq1, per1 = collect_cycle(sess, g, si, 1)
            # reset slot again for ACT2
            d = sess.reset()
            g = plane(d["frame"])
            g, _, ok = move_to_slot(sess, g, si)
            g, seq2, per2 = collect_cycle(sess, g, si, 2)

            target = mids[si]
            target_inv = mids_inv[si]
            hit1 = next((k for k, s in enumerate(seq1) if s == target), None)
            hit2 = next((k for k, s in enumerate(seq2) if s == target), None)
            hit1i = next((k for k, s in enumerate(seq1) if s == target_inv), None)
            hit2i = next((k for k, s in enumerate(seq2) if s == target_inv), None)

            # also Hamming distance of closest in cycle
            def best_ham(seq, tgt):
                best = (25, None, None)
                t = np.array(tgt)
                for k, s in enumerate(seq[:-1] if seq[-1] == seq[0] else seq):
                    h = int(np.sum(np.array(s) != t))
                    if h < best[0]:
                        best = (h, k, ascii5(s))
                return {"ham": best[0], "k": best[1], "ascii": best[2]}

            entry = {
                "slot": si,
                "period1": per1,
                "period2": per2,
                "cycle1_n": len(set(seq1)),
                "hit_act1": hit1,
                "hit_act2": hit2,
                "hit_act1_inv": hit1i,
                "hit_act2_inv": hit2i,
                "best_vs_mid": best_ham(seq1, target),
                "best_vs_inv": best_ham(seq1, target_inv),
                "cycle1_ascii": [ascii5(s) for s in seq1[:8]],
            }
            # choose plan: prefer fewest presses
            cand = []
            if hit1 is not None and hit1 > 0:
                cand.append(("1", hit1, [1] * hit1))
            if hit2 is not None and hit2 > 0:
                cand.append(("2", hit2, [2] * hit2))
            if hit1 == 0 or hit2 == 0:
                cand.append(("nop", 0, []))
            if hit1i is not None and hit1i > 0:
                cand.append(("1inv", hit1i, [1] * hit1i))
            if hit2i is not None and hit2i > 0:
                cand.append(("2inv", hit2i, [2] * hit2i))
            cand.sort(key=lambda x: x[1])
            entry["plan"] = {"kind": cand[0][0], "seq": cand[0][2]} if cand else None
            print(
                f"  slot{si} hit1={hit1} hit2={hit2} inv1={hit1i} inv2={hit2i} "
                f"best_ham={entry['best_vs_mid']} plan={entry['plan']}"
            )
            plans.append(entry)

        out["plans"] = [
            {k: v for k, v in p.items() if k != "cycle1_ascii"} | {"cycle1_ascii": p["cycle1_ascii"]}
            for p in plans
        ]

        # Execute if every slot has a plan (including nop / already matched)
        runnable = all(p["plan"] is not None or p["hit_act1"] == 0 for p in plans)
        # fix: already matched → empty plan
        for p in plans:
            if p["plan"] is None and (p["hit_act1"] == 0 or p["hit_act2"] == 0):
                p["plan"] = {"kind": "nop", "seq": []}
            if p["plan"] is None and (p["hit_act1_inv"] == 0 or p["hit_act2_inv"] == 0):
                p["plan"] = {"kind": "nop_inv", "seq": []}

        runnable = all(p["plan"] is not None for p in plans)
        print(f"\n## execute runnable={runnable}")
        d = sess.reset()
        g = plane(d["frame"])
        actions = []
        if runnable:
            for si, p in enumerate(plans):
                g, nav, ok = move_to_slot(sess, g, si)
                actions.extend(nav)
                for a in p["plan"]["seq"]:
                    d = go(sess, a)
                    g = plane(d["frame"])
                    actions.append(a)
        lv1 = d.get("levels_completed")
        bots_after = [bottom_glyph(g, i) for i in range(5)]
        eq_after = [bots_after[i] == mids[i] for i in range(5)]
        eq_inv = [bots_after[i] == mids_inv[i] for i in range(5)]
        print(f"  actions={actions} lv {lv0}->{lv1}")
        print(f"  eq_mid={eq_after} eq_inv={eq_inv}")
        out["combined"] = {
            "runnable": runnable,
            "actions": actions,
            "lv0": lv0,
            "lv1": lv1,
            "eq_mid": eq_after,
            "eq_inv": eq_inv,
            "bottom_after": [ascii5(s) for s in bots_after],
        }

        # Fallback: even if not all hittable, report ham matrix slot×mid
        print("\n## ham matrix bottom_reset × mid")
        ham = []
        for bi, b in enumerate(bots):
            row = []
            for mi, m in enumerate(mids):
                h = int(np.sum(np.array(b) != np.array(m)))
                row.append(h)
            print(f"  B{bi}: {row}")
            ham.append(row)
        out["ham_reset"] = ham

        # Compare bottom cycles to TOP-right 7-frame icons (option alphabet)
        print("\n## top 7-frame interiors (right of each pair)")
        top7 = []
        for y0 in (4, 13, 22):
            for x0 in (21, 42):  # right tiles approx
                if int(g[y0, x0]) == 7 and int(g[y0 + 6, x0 + 6]) == 7:
                    patch = g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6]
                    sig = tuple(int(v) for v in patch.ravel())
                    top7.append({"x0": x0, "y0": y0, "ascii": ascii5(sig), "sig": sig})
                    print(f"  @({x0},{y0})")
                    for line in ascii5(sig):
                        print("   ", line)
        # after execute g may be mutated — re-read from reset for top
        d = sess.reset()
        g = plane(d["frame"])
        top7 = []
        for y0 in (4, 13, 22):
            for x0 in (21, 42):
                if int(g[y0, x0]) == 7 and int(g[y0 + 6, x0 + 6]) == 7:
                    patch = g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6]
                    sig = tuple(int(v) for v in patch.ravel())
                    top7.append({"x0": x0, "y0": y0, "ascii": ascii5(sig)})
        out["top7"] = top7

        # Is each top7 in slot0 ACT1 cycle?
        d = sess.reset()
        g = plane(d["frame"])
        g, _, _ = move_to_slot(sess, g, 0)
        _, seq0, _ = collect_cycle(sess, g, 0, 1)
        set0 = set(seq0)
        top_in_cycle = []
        for t in top7:
            sig = tuple(int(v) for v in np.array([[int(c) for c in line] for line in t["ascii"]]).ravel())
            # rebuild from ascii
            sig = tuple(int(c) for line in t["ascii"] for c in line)
            top_in_cycle.append({"pos": (t["x0"], t["y0"]), "in_slot0_cycle": sig in set0})
        print("top7 in slot0 cycle:", top_in_cycle)
        out["top7_in_slot0_cycle"] = top_in_cycle

        # Left A-frame interiors remapped
        print("\n## top A-frame interiors (10→7)")
        topA = []
        for y0 in (4, 13, 22):
            for x0 in (12, 33):
                if int(g[y0, x0]) == 10 and int(g[y0 + 6, x0 + 6]) == 10:
                    patch = g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6]
                    rem = np.where(patch == 10, 7, patch)
                    sig = tuple(int(v) for v in rem.ravel())
                    topA.append({"x0": x0, "y0": y0, "ascii": ascii5(sig)})
                    print(f"  @({x0},{y0})")
                    for line in ascii5(sig):
                        print("   ", line)
        out["topA"] = topA
        topA_in = []
        for t in topA:
            sig = tuple(int(c) for line in t["ascii"] for c in line)
            topA_in.append({"pos": (t["x0"], t["y0"]), "in_slot0_cycle": sig in set0})
        print("topA in slot0 cycle:", topA_in)
        out["topA_in_slot0_cycle"] = topA_in

        reading = "L1_CLEAR" if int(lv1 or 0) > int(lv0 or 0) else "MIDBAND_PARTIAL"
        if runnable and all(eq_after) and reading != "L1_CLEAR":
            reading = "MID_MATCH_NO_CLEAR"
        out["reading"] = reading
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("READING:", reading)
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
