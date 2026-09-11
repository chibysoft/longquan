"""tr87 L1: mid→phase dial (ink/CC/hash %7); feature-match mid without pixel equality.

H11: each mid cell feature → ACT1 count mod 7 from reset (or absolute cycle index)
H12: dial bottoms so ink/CC matches mid cell (same slot index)
H13: mid color remaps beyond 10→7; best-ham dial; check levels
H14: end selector on slot k after matching; or require exact phase vector from top ink%7

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

OUT = ROOT / "tests/fixtures/tr87_l1_mid_phase.json"
CLEAR = ROOT / "tests/fixtures/tr87_l1_clear_frame.json"
SLOTS = (15, 22, 29, 36, 43)
MID_X = (14, 21, 28, 35, 42)
PAIRS = [
    (12, 22, 4),
    (36, 46, 4),
    (12, 22, 13),
    (36, 46, 13),
    (12, 22, 22),
    (36, 46, 22),
]


def bg(g, si):
    x0 = SLOTS[si]
    return tuple(int(v) for v in g[52:57, x0 : x0 + 5].ravel())


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
        a = 4 if (ti - cur) % 5 <= (cur - ti) % 5 else 3
        d = sess.action(f"ACTION{a}")
        g = plane(d["frame"])
        acts.append(a)
    return g, acts, False


def ink(p, c):
    return int((p == c).sum())


def n_cc(p, c):
    H, W = p.shape
    seen = np.zeros_like(p, dtype=bool)
    n = 0
    for y in range(H):
        for x in range(W):
            if seen[y, x] or int(p[y, x]) != c:
                continue
            n += 1
            stack = [(x, y)]
            seen[y, x] = True
            while stack:
                cx, cy = stack.pop()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 0 <= ny < H and not seen[ny, nx] and int(p[ny, nx]) == c:
                        seen[ny, nx] = True
                        stack.append((nx, ny))
    return n


def mid_patches(g):
    out = []
    for x0 in MID_X:
        # banner cells roughly 7 wide; inner 5x5 like bottoms
        p = g[41:46, x0 + 1 : x0 + 6].copy()
        out.append(p)
    return out


def collect_cycles(sess):
    """Return list[si] -> list of 7 sigs starting at reset glyph (ACT1 order)."""
    cycles = []
    for si in range(5):
        d = sess.reset()
        g = plane(d["frame"])
        g, _, _ = move(sess, g, si)
        start = bg(g, si)
        seq = [start]
        for _ in range(8):
            d = sess.action("ACTION1")
            g = plane(d["frame"])
            sig = bg(g, si)
            if sig == start:
                break
            seq.append(sig)
        cycles.append(seq)
    return cycles


def dial_phases(sess, phases, end_sel=None, use_act2=False):
    """phases[si] in 0..6 = how many ACT1 from reset glyph. Returns (acts, d, lv)."""
    d = sess.reset()
    g = plane(d["frame"])
    acts = []
    flip = 2 if use_act2 else 1
    for si, ph in enumerate(phases):
        ph = int(ph) % 7
        g, m, _ = move(sess, g, si)
        acts.extend(m)
        for _ in range(ph):
            d = sess.action(f"ACTION{flip}")
            g = plane(d["frame"])
            acts.append(flip)
    if end_sel is not None:
        g, m, _ = move(sess, g, end_sel)
        acts.extend(m)
        d = sess.action("ACTION3") if sel(g) == end_sel else d
        # refresh: if already there, nudge with 34 noop
        if sel(g) == end_sel:
            d = sess.action("ACTION4")
            g = plane(d["frame"])
            acts.append(4)
            d = sess.action("ACTION3")
            g = plane(d["frame"])
            acts.append(3)
    else:
        d = sess.action("ACTION4")
        g = plane(d["frame"])
        acts.append(4)
        d = sess.action("ACTION3")
        acts.append(3)
    return acts, d, d.get("levels_completed", 0), g


def try_clear(label, acts, d, out):
    lv = d.get("levels_completed", 0)
    rec = {"label": label, "seq": acts, "levels": lv}
    out["trials"].append(rec)
    print(f"  {label}: lv={lv} n={len(acts)}")
    if lv and lv > 0:
        CLEAR.write_text(
            json.dumps(
                {
                    "label": label,
                    "seq": acts,
                    "levels_completed": lv,
                    "frame": d["frame"],
                    "meta": {k: d.get(k) for k in d if k != "frame"},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print("*** L1_CLEAR ***", label)
        out["cleared"] = True
        return True
    return False


def ham(a, b):
    return int(np.sum(np.array(a) != np.array(b)))


def main():
    sess = Sess(_api_key())
    out = {"trials": [], "cleared": False, "mid_feats": [], "phases_tried": []}
    try:
        sess.open()
        d = sess.reset()
        g = plane(d["frame"])
        mids = mid_patches(g)
        for i, p in enumerate(mids):
            feats = {
                "i": i,
                "hist": {int(k): int(v) for k, v in zip(*np.unique(p, return_counts=True))},
                "ink10": ink(p, 10),
                "ink5": ink(p, 5),
                "ink7": ink(p, 7),
                "cc10": n_cc(p, 10),
                "cc5": n_cc(p, 5),
            }
            out["mid_feats"].append(feats)
            print("mid", feats)

        cycles = collect_cycles(sess)
        out["cycle_lens"] = [len(c) for c in cycles]
        print("cycles", out["cycle_lens"])

        # --- H11 phase vectors from mid ---
        phase_sets = {}
        phase_sets["ink10_mod7"] = [m["ink10"] % 7 for m in out["mid_feats"]]
        phase_sets["ink5_mod7"] = [m["ink5"] % 7 for m in out["mid_feats"]]
        phase_sets["ink10_mod7_inv"] = [(7 - (m["ink10"] % 7)) % 7 for m in out["mid_feats"]]
        phase_sets["cc10_mod7"] = [m["cc10"] % 7 for m in out["mid_feats"]]
        phase_sets["cc5_mod7"] = [m["cc5"] % 7 for m in out["mid_feats"]]
        phase_sets["ink10_minus5_mod7"] = [(m["ink10"] - m["ink5"]) % 7 for m in out["mid_feats"]]
        phase_sets["sum_ink_mod7"] = [(m["ink10"] + m["ink5"]) % 7 for m in out["mid_feats"]]
        # constant phases (sample; full torus already covered elsewhere)
        phase_sets["const_0"] = [0] * 5
        phase_sets["const_1"] = [1] * 5
        phase_sets["const_3"] = [3] * 5
        phase_sets["ramp01234"] = [0, 1, 2, 3, 4]
        phase_sets["ramp65432"] = [6, 5, 4, 3, 2]
        # top7 inkS % 7 for first 5 pairs
        d = sess.reset()
        g = plane(d["frame"])
        top_ink = []
        for ax, sx, y0 in PAIRS:
            S = g[y0 + 1 : y0 + 6, sx + 1 : sx + 6]
            top_ink.append(ink(S, 7))
        phase_sets["topS_ink_mod7_5"] = [top_ink[i] % 7 for i in range(5)]
        phase_sets["topA_ink_mod7_5"] = []
        for ax, sx, y0 in PAIRS[:5]:
            A = g[y0 + 1 : y0 + 6, ax + 1 : ax + 6]
            phase_sets["topA_ink_mod7_5"].append(ink(A, 10) % 7)
        phase_sets["top_ham_mod7_5"] = []
        for ax, sx, y0 in PAIRS[:5]:
            A = np.where(g[y0 + 1 : y0 + 6, ax + 1 : ax + 6] == 10, 7, g[y0 + 1 : y0 + 6, ax + 1 : ax + 6])
            S = g[y0 + 1 : y0 + 6, sx + 1 : sx + 6]
            phase_sets["top_ham_mod7_5"].append(int(np.sum(A != S)) % 7)

        out["phases_tried"] = {k: v for k, v in phase_sets.items()}
        print("phase samples", {k: phase_sets[k] for k in list(phase_sets)[:8]})

        # prioritize feature-derived phases; end_sel only for a few
        priority = [
            "ink10_mod7",
            "ink5_mod7",
            "ink10_mod7_inv",
            "cc10_mod7",
            "sum_ink_mod7",
            "topS_ink_mod7_5",
            "topA_ink_mod7_5",
            "top_ham_mod7_5",
            "ramp01234",
            "const_1",
            "const_3",
        ]
        for name in priority:
            phases = phase_sets[name]
            for end in (None, 0):
                lab = f"H11_{name}_end{end}_a1"
                acts, d, lv, g = dial_phases(sess, phases, end_sel=end, use_act2=False)
                if try_clear(lab, acts, d, out):
                    break
            if out["cleared"]:
                break
            # one ACT2 variant without end
            acts, d, lv, g = dial_phases(sess, phases, end_sel=None, use_act2=True)
            if try_clear(f"H11_{name}_endNone_a2", acts, d, out):
                break

        # --- H12 feature match ink/CC ---
        if not out["cleared"]:
            print("\n=== H12 feature match ===")
            for mode in ("ink7_vs_ink10", "ink7_vs_ink5", "cc7_vs_cc10", "cc7_vs_cc5"):
                d = sess.reset()
                g = plane(d["frame"])
                acts = []
                for si in range(5):
                    mp = mids[si]
                    if mode == "ink7_vs_ink10":
                        want = ink(mp, 10)
                        score = lambda sig: abs(ink(np.array(sig).reshape(5, 5), 7) - want)
                    elif mode == "ink7_vs_ink5":
                        want = ink(mp, 5)
                        score = lambda sig, w=want: abs(ink(np.array(sig).reshape(5, 5), 7) - w)
                    elif mode == "cc7_vs_cc10":
                        want = n_cc(mp, 10)
                        score = lambda sig, w=want: abs(n_cc(np.array(sig).reshape(5, 5), 7) - w)
                    else:
                        want = n_cc(mp, 5)
                        score = lambda sig, w=want: abs(n_cc(np.array(sig).reshape(5, 5), 7) - w)
                    best = min(cycles[si], key=score)
                    # dial to best
                    g, m, _ = move(sess, g, si)
                    acts.extend(m)
                    for _ in range(8):
                        if bg(g, si) == best:
                            break
                        d = sess.action("ACTION1")
                        g = plane(d["frame"])
                        acts.append(1)
                d = sess.action("ACTION4")
                acts.append(4)
                if try_clear(f"H12_{mode}", acts, d, out):
                    break

        # --- H13 remap mid colors into {5,7} then best ham ---
        if not out["cleared"]:
            print("\n=== H13 remaps ===")
            remaps = [
                ("10to7", {10: 7}),
                ("10to5", {10: 5}),
                ("5to7_10to7", {5: 7, 10: 7}),
                ("5to7", {5: 7}),
                ("10to7_5stay", {10: 7}),
                ("swap_5_10_as7", {10: 7, 5: 7}),  # same as flatten
            ]
            for rname, mp in remaps:
                d = sess.reset()
                g = plane(d["frame"])
                acts = []
                hams = []
                for si in range(5):
                    raw = mids[si].copy()
                    tgt = raw.copy()
                    for a, b in mp.items():
                        tgt = np.where(tgt == a, b, tgt)
                    # force non-7/5 to 5 background?
                    tgt = np.where(np.isin(tgt, [5, 7]), tgt, 5)
                    tsig = tuple(int(v) for v in tgt.ravel())
                    best = min(cycles[si], key=lambda s: ham(s, tsig))
                    hams.append(ham(best, tsig))
                    g, m, _ = move(sess, g, si)
                    acts.extend(m)
                    for _ in range(8):
                        if bg(g, si) == best:
                            break
                        d = sess.action("ACTION1")
                        g = plane(d["frame"])
                        acts.append(1)
                d = sess.action("ACTION4")
                acts.append(4)
                out["trials"].append({"label": f"H13_{rname}_hams", "hams": hams})
                print(f"  H13_{rname} hams={hams}")
                if try_clear(f"H13_{rname}", acts, d, out):
                    break

        # --- H14: phase from mid ink10 alone as absolute index into cycle by matching ink ---
        if not out["cleared"]:
            print("\n=== H14 ink-index ===")
            d = sess.reset()
            g = plane(d["frame"])
            acts = []
            for si in range(5):
                want = out["mid_feats"][si]["ink10"]
                # pick cycle glyph with closest ink7
                scored = [(abs(ink(np.array(sig).reshape(5, 5), 7) - want), j, sig) for j, sig in enumerate(cycles[si])]
                scored.sort()
                best = scored[0][2]
                g, m, _ = move(sess, g, si)
                acts.extend(m)
                for _ in range(8):
                    if bg(g, si) == best:
                        break
                    d = sess.action("ACTION1")
                    g = plane(d["frame"])
                    acts.append(1)
            d = sess.action("ACTION4")
            acts.append(4)
            try_clear("H14_ink10_closest", acts, d, out)

        # zero all phases (identity) already in const_0; try reverse order dial
        if not out["cleared"]:
            for name in ("ink10_mod7", "topS_ink_mod7_5", "sum_ink_mod7"):
                phases = list(reversed(phase_sets[name]))
                acts, d, lv, g = dial_phases(sess, phases)
                if try_clear(f"H11rev_{name}", acts, d, out):
                    break

        out["best_lv"] = max((t.get("levels") or 0 for t in out["trials"]), default=0)
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("\nDONE best_lv", out["best_lv"], "cleared", out["cleared"], "trials", len(out["trials"]))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
