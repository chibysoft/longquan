"""tr87 L1: H21 submit gestures after mid-nearest; H22 search bit-perm remaps into alphabets.

tags=["tr87_recon"]
"""
from __future__ import annotations

import json
import sys
from itertools import permutations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.tr87_recon_probe import Sess, plane  # noqa: E402

OUT = ROOT / "tests/fixtures/tr87_l1_submit_remap.json"
SLOTS = (15, 22, 29, 36, 43)


def p(*a, **k):
    print(*a, **k, flush=True)


def bg(g, si):
    return tuple(int(v) for v in g[52:57, SLOTS[si] : SLOTS[si] + 5].ravel())


def sel(g):
    xs = [int(x) for y, x in np.argwhere(g == 0)]
    return int(np.argmin([abs(min(xs) - s) for s in SLOTS])) if xs else None


def move(sess, g, ti):
    acts = []
    for _ in range(8):
        cur = sel(g)
        if cur == ti:
            return g, acts
        a = 4 if (ti - cur) % 5 <= (cur - ti) % 5 else 3
        d = sess.action(f"ACTION{a}")
        g = plane(d["frame"])
        acts.append(a)
    return g, acts


def go(sess, g, a):
    d = sess.action(f"ACTION{a}")
    return plane(d["frame"]), d


def ham(a, b):
    return int(np.sum(np.array(a) != np.array(b)))


def replay(sess, actions):
    d = sess.reset()
    g = plane(d["frame"])
    for a in actions:
        g, d = go(sess, g, a)
    return g, d


def mid_bits(g0):
    out = []
    for x0 in (15, 22, 29, 36, 43):
        p5 = g0[41:46, x0 : x0 + 5]
        out.append((p5 == 10).astype(np.uint8).ravel())
    return out


def bits_to_sig(bits):
    a = np.where(bits.reshape(5, 5) == 1, 7, 5)
    return tuple(int(v) for v in a.ravel())


def collect_cycles(sess):
    cycles = []
    for si in range(5):
        g, d = replay(sess, [])
        g, _ = move(sess, g, si)
        start = bg(g, si)
        cyc = [start]
        for _ in range(6):
            g, d = go(sess, g, 1)
            sig = bg(g, si)
            if sig == start:
                break
            cyc.append(sig)
        cycles.append(cyc)
        p(f"  cycle{si} len={len(cyc)}")
    return cycles


def phases_to_actions(cycles, phases):
    """Build action list: for each slot, nav + ACT1*phase (from reset)."""
    # approximate nav from slot ring starting at 0
    actions = []
    cur = 0
    for si, ph in enumerate(phases):
        # nav cur -> si
        df = (si - cur) % 5
        db = (cur - si) % 5
        if df <= db:
            actions.extend([4] * df)
        else:
            actions.extend([3] * db)
        cur = si
        actions.extend([1] * (ph % len(cycles[si])))
    return actions


def main():
    g0 = np.asarray(
        json.loads((ROOT / "tests/fixtures/tr87_l1_frame_live.json").read_text(encoding="utf-8"))["frame"]
    )
    if g0.ndim == 3:
        g0 = g0[0]
    mbits = mid_bits(g0)
    mid_id = [bits_to_sig(b) for b in mbits]

    sess = Sess(_api_key())
    out = {}
    try:
        sess.open()
        p("## cycles")
        cycles = collect_cycles(sess)
        out["cycle_lens"] = [len(c) for c in cycles]

        # nearest phase per slot to mid_id
        nearest = []
        for si in range(5):
            best = min(((ham(sig, mid_id[si]), n) for n, sig in enumerate(cycles[si])), key=lambda x: x[0])
            nearest.append(best)
            p(f"  near{si} ham={best[0]} n={best[1]}")
        phases = [n for _, n in nearest]
        base = phases_to_actions(cycles, phases)
        g, d = replay(sess, base)
        lv = d.get("levels_completed")
        p(f"nearest-mid base lv={lv} nact={len(base)}")
        out["nearest"] = {"phases": phases, "hams": [h for h, _ in nearest], "lv": lv, "nact": len(base)}

        # H21: submit gestures after base
        p("## H21 submit gestures")
        gestures = {
            "lap4": [4] * 5,
            "lap3": [3] * 5,
            "lap4_2": [4] * 10,
            "zig": [4, 3, 4, 3, 4],
            "all1": [1] * 5,
            "all2": [2] * 5,
            "12": [1, 2],
            "21": [2, 1],
            "to0_1": None,  # special
            "full_period_each": None,
        }
        hits = []
        for name, gest in gestures.items():
            if name == "to0_1":
                # move to slot0 then ACT1
                g, d = replay(sess, base)
                g, nav = move(sess, g, 0)
                acts = base + nav + [1]
            elif name == "full_period_each":
                acts = list(base)
                cur_sel_actions = []
                # from base end, visit each slot and press 1×7
                g, d = replay(sess, base)
                for si in range(5):
                    g, nav = move(sess, g, si)
                    cur_sel_actions.extend(nav)
                    for _ in range(7):
                        g, d = go(sess, g, 1)
                        cur_sel_actions.append(1)
                acts = base + cur_sel_actions
            else:
                acts = base + gest
            g, d = replay(sess, acts)
            lv1 = d.get("levels_completed")
            p(f"  {name}: lv={lv1} nact={len(acts)}")
            hits.append({"name": name, "lv": lv1, "nact": len(acts)})
            if int(lv1 or 0) > 0:
                out["clear"] = {"name": name, "actions": acts}
                (ROOT / "tests/fixtures/tr87_l1_clear_frame.json").write_text(
                    json.dumps({"frame": d["frame"], "levels": lv1, "actions": acts, "name": name}, indent=2),
                    encoding="utf-8",
                )
                break
        out["gestures"] = hits

        # Also: reset config + only gestures (no nearest)
        if not out.get("clear"):
            p("## gestures from reset only")
            for name, gest in [("lap4", [4] * 5), ("all1_35", [1] * 35), ("walk_flip", [1, 4] * 10)]:
                g, d = replay(sess, gest)
                p(f"  reset+{name} lv={d.get('levels_completed')}")

        # H22: small remaps — row/col shuffle of mid bits, check alphabet membership
        p("## H22 row/col/transpose remaps into alphabets")
        alphas = [set(c) for c in cycles]

        def try_remap(name, transform_bits):
            tgts = [bits_to_sig(transform_bits(mbits[si])) for si in range(5)]
            ok = [tgts[si] in alphas[si] for si in range(5)]
            return name, ok, tgts, sum(ok)

        remaps = []
        # identity
        remaps.append(try_remap("id", lambda b: b))
        remaps.append(try_remap("inv", lambda b: 1 - b))
        # reverse rows
        remaps.append(try_remap("flipud", lambda b: np.flipud(b.reshape(5, 5)).ravel()))
        remaps.append(try_remap("fliplr", lambda b: np.fliplr(b.reshape(5, 5)).ravel()))
        remaps.append(try_remap("T", lambda b: b.reshape(5, 5).T.ravel()))
        for k in range(1, 5):
            remaps.append(
                try_remap(f"rollrow{k}", lambda b, k=k: np.roll(b.reshape(5, 5), k, axis=0).ravel())
            )
            remaps.append(
                try_remap(f"rollcol{k}", lambda b, k=k: np.roll(b.reshape(5, 5), k, axis=1).ravel())
            )
        # row permutations (120) — only check how many slots land
        best_perm = None
        for perm in permutations(range(5)):
            def tf(b, perm=perm):
                a = b.reshape(5, 5)
                return a[list(perm), :].ravel()

            name, ok, tgts, n = try_remap(f"rowperm", tf)
            if best_perm is None or n > best_perm[0]:
                best_perm = (n, perm, ok, tgts)
            if n == 5:
                break
        p(f"  best rowperm slots_hit={best_perm[0]} perm={best_perm[1]} ok={best_perm[2]}")

        best_cperm = None
        for perm in permutations(range(5)):
            def tf(b, perm=perm):
                a = b.reshape(5, 5)
                return a[:, list(perm)].ravel()

            name, ok, tgts, n = try_remap("colperm", tf)
            if best_cperm is None or n > best_cperm[0]:
                best_cperm = (n, perm, ok, tgts)
            if n == 5:
                break
        p(f"  best colperm slots_hit={best_cperm[0]} perm={best_cperm[1]} ok={best_cperm[2]}")

        remap_summary = []
        for name, ok, tgts, n in remaps:
            if n > 0:
                p(f"  {name}: hit={ok} n={n}")
            remap_summary.append({"name": name, "ok": ok, "n": n})
        out["remaps"] = remap_summary
        out["best_rowperm"] = {"n": best_perm[0], "perm": best_perm[1], "ok": best_perm[2]}
        out["best_colperm"] = {"n": best_cperm[0], "perm": best_cperm[1], "ok": best_cperm[2]}

        # If any remap hits all 5, dial it
        winner = None
        for name, ok, tgts, n in remaps:
            if n == 5:
                winner = (name, tgts)
                break
        if best_perm[0] == 5:
            winner = ("rowperm", best_perm[3])
        if best_cperm[0] == 5:
            winner = ("colperm", best_cperm[3])

        if winner and not out.get("clear"):
            p(f"## dial remap winner {winner[0]}")
            tgts = winner[1]
            phases = []
            for si, tgt in enumerate(tgts):
                n = cycles[si].index(tgt)
                phases.append(n)
            acts = phases_to_actions(cycles, phases)
            g, d = replay(sess, acts)
            lv1 = d.get("levels_completed")
            p(f"  lv={lv1}")
            out["remap_dial"] = {"name": winner[0], "lv": lv1, "phases": phases, "actions": acts}
            if int(lv1 or 0) > 0:
                out["clear"] = {"name": f"remap_{winner[0]}", "actions": acts}
                (ROOT / "tests/fixtures/tr87_l1_clear_frame.json").write_text(
                    json.dumps({"frame": d["frame"], "levels": lv1, "actions": acts}, indent=2),
                    encoding="utf-8",
                )
            # try gestures after remap dial
            for gname, gest in [("lap4", [4] * 5), ("12", [1, 2])]:
                g, d = replay(sess, acts + gest)
                p(f"  +{gname} lv={d.get('levels_completed')}")

        # H23: pair-selection mask — mid ink signature → which of 6 pairs; show S on bottom
        p("## H23 pair mask → bottom S (fuzzy)")
        pairs_S = []
        for y0 in (4, 13, 22):
            for x0 in (22, 46):
                pairs_S.append(tuple(int(v) for v in g0[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6].ravel()))
        # select 5 of 6 by dropping the pair whose A is farthest from any mid
        pairs_A = []
        for y0 in (4, 13, 22):
            for x0 in (12, 36):
                patch = np.where(g0[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6] == 10, 1, 0).astype(np.uint8).ravel()
                pairs_A.append(patch)
        # for each mid, best pair index
        chosen = []
        for si in range(5):
            bi = min(range(6), key=lambda j: int(np.sum(mbits[si] != pairs_A[j])))
            chosen.append(bi)
            p(f"  mid{si} -> pair{bi} A_ham={int(np.sum(mbits[si]!=pairs_A[bi]))}")
        # dial each slot to nearest to pairs_S[chosen[si]]
        phases = []
        hams = []
        for si in range(5):
            tgt = pairs_S[chosen[si]]
            best = min(((ham(sig, tgt), n) for n, sig in enumerate(cycles[si])), key=lambda x: x[0])
            phases.append(best[1])
            hams.append(best[0])
            p(f"  slot{si} vs S ham={best[0]} n={best[1]}")
        acts = phases_to_actions(cycles, phases)
        g, d = replay(sess, acts)
        p(f"  pair-mask lv={d.get('levels_completed')} hams={hams}")
        out["pair_mask"] = {"chosen": chosen, "hams": hams, "lv": d.get("levels_completed"), "actions": acts}
        for gname, gest in [("lap4", [4] * 5), ("noop", [])]:
            g, d = replay(sess, acts + gest)
            if int(d.get("levels_completed") or 0) > 0:
                out["clear"] = {"name": f"pairmask_{gname}", "actions": acts + gest}
                p("*** CLEAR", gname)

        cleared = bool(out.get("clear"))
        out["reading"] = "L1_CLEAR" if cleared else "SUBMIT_REMAP_PARTIAL"
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        p("READING:", out["reading"])
        p("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
