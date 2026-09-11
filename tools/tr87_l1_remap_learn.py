"""tr87 L1: learn A→7 remap from 6 top pairs; LOO validate; apply to mid; dial.

H7: mid(A-style) under learned remap = bottom targets; levels↑ if dialed.

tags=["tr87_recon"]
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.tr87_recon_probe import Sess, plane  # noqa: E402

OUT = ROOT / "tests/fixtures/tr87_l1_remap_learn.json"
SLOTS = (15, 22, 29, 36, 43)
PAIRS = [(4, 12, 22), (4, 36, 46), (13, 12, 22), (13, 36, 46), (22, 12, 22), (22, 36, 46)]


def Aink(g, y0, x0):
    p = g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6]
    return (p == 10).astype(np.uint8).ravel()


def Sink(g, y0, x0):
    p = g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6]
    return (p == 7).astype(np.uint8).ravel()


def mid_ink(g, si):
    x0 = (14, 21, 28, 35, 42)[si]
    p = g[41:46, x0 + 1 : x0 + 6]
    return (p == 10).astype(np.uint8).ravel()


def bits_to_sig(bits):
    """ink bits → 5/7 glyph tuple."""
    a = np.where(bits.reshape(5, 5) == 1, 7, 5)
    return tuple(int(v) for v in a.ravel())


def asc(sig):
    a = np.array(sig).reshape(5, 5)
    return ["".join(str(int(v)) for v in r) for r in a]


def fit_bit(X, y, maxk=3):
    """Return list of all minimal rules that fit (kind, idxs)."""
    n, d = X.shape
    hits = []
    if np.all(y == 0):
        return [("const0", ())]
    if np.all(y == 1):
        return [("const1", ())]
    for k in range(1, maxk + 1):
        for comb in combinations(range(d), k):
            pred = np.zeros(n, dtype=np.uint8)
            for i in comb:
                pred ^= X[:, i]
            if np.array_equal(pred, y):
                hits.append(("xor", comb))
            if np.array_equal(pred ^ 1, y):
                hits.append(("nxor", comb))
        if hits:
            return hits  # minimal k only
    return []


def apply_rule(x, rule):
    kind, idxs = rule
    if kind == "const0":
        return 0
    if kind == "const1":
        return 1
    pred = 0
    for i in idxs:
        pred ^= int(x[i])
    if kind == "nxor":
        pred ^= 1
    return pred


def apply_rules(x, rules):
    return np.array([apply_rule(x, r) for r in rules], dtype=np.uint8)


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


def collect_alpha(sess, si):
    d = sess.reset()
    g = plane(d["frame"])
    g, _, _ = move(sess, g, si)
    start = bg(g, si)
    seen = {start: (1, 0)}
    for fl in (1, 2):
        d = sess.reset()
        g = plane(d["frame"])
        g, _, _ = move(sess, g, si)
        for n in range(1, 8):
            d = sess.action(f"ACTION{fl}")
            g = plane(d["frame"])
            sig = bg(g, si)
            if sig not in seen or n < seen[sig][1]:
                seen[sig] = (fl, n)
            if sig == start:
                break
    return seen


def main():
    # ---- offline from fixture first ----
    g0 = np.asarray(json.loads((ROOT / "tests/fixtures/tr87_l1_frame_live.json").read_text(encoding="utf-8"))["frame"])
    if g0.ndim == 3:
        g0 = g0[0]

    X = np.stack([Aink(g0, y, a) for y, a, s in PAIRS])
    Y = np.stack([Sink(g0, y, s) for y, a, s in PAIRS])

    # Fit on all 6 — pick first minimal rule per bit
    rules_all = []
    for j in range(25):
        hits = fit_bit(X, Y[:, j], 3)
        rules_all.append(hits[0] if hits else None)
    print("## fit-all rules (minimal)")
    for j, r in enumerate(rules_all):
        print(f"  bit{j}: {r}")

    # LOO: for each held-out pair, refit on 5, predict
    print("\n## leave-one-out")
    loo_hams = []
    loo_detail = []
    for hold in range(6):
        tr = [i for i in range(6) if i != hold]
        Xt, Yt = X[tr], Y[tr]
        rules = []
        ok = True
        for j in range(25):
            hits = fit_bit(Xt, Yt[:, j], 3)
            if not hits:
                ok = False
                rules.append(None)
            else:
                rules.append(hits[0])
        if not ok:
            print(f"  hold {hold}: incomplete fit")
            loo_hams.append(None)
            continue
        pred = apply_rules(X[hold], rules)
        h = int(np.sum(pred != Y[hold]))
        loo_hams.append(h)
        print(f"  hold {PAIRS[hold]}: ham={h}")
        loo_detail.append({"hold": PAIRS[hold], "ham": h})

    out = {
        "rules_all": [(r[0], list(r[1])) if r else None for r in rules_all],
        "loo": loo_detail,
        "loo_hams": loo_hams,
    }

    # Also try: same-position only / neighborhood templates
    print("\n## baseline id / inv / neigh majority")
    for name, fn in [
        ("id", lambda x: x.copy()),
        ("inv", lambda x: 1 - x),
    ]:
        hams = [int(np.sum(fn(X[i]) != Y[i])) for i in range(6)]
        print(f"  {name}: {hams} sum={sum(hams)}")

    # 3x3 neighborhood: for each out pos, OR/XOR/AND of A neighborhood — fit on pairs
    # Try: out[j] = A[j] XOR A[nbr] for each nbr offset
    offsets = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1), (0, 0)]
    best_nbr = []
    for j in range(25):
        jy, jx = divmod(j, 5)
        cand = []
        for dy, dx in offsets:
            ny, nx = jy + dy, jx + dx
            if not (0 <= ny < 5 and 0 <= nx < 5):
                continue
            i = ny * 5 + nx
            for kind in ("xor", "nxor", "copy", "ncopy"):
                ok = True
                for p in range(6):
                    a = int(X[p, i])
                    if kind == "xor":
                        pred = a ^ int(X[p, j]) if i != j else a
                    elif kind == "nxor":
                        pred = 1 - (a ^ int(X[p, j]) if i != j else a)
                    elif kind == "copy":
                        pred = a
                    else:
                        pred = 1 - a
                    # for xor with self confusing — simplify:
                    if kind == "copy":
                        pred = a
                    elif kind == "ncopy":
                        pred = 1 - a
                    elif kind == "xor":
                        pred = int(X[p, j]) ^ a if i != j else a
                    elif kind == "nxor":
                        pred = 1 - (int(X[p, j]) ^ a if i != j else a)
                    if pred != int(Y[p, j]):
                        ok = False
                        break
                if ok:
                    cand.append((kind, i, (dy, dx)))
        best_nbr.append(cand[:3])
    n_with = sum(1 for c in best_nbr if c)
    print(f"  simple nbr rules covering bits: {n_with}/25")

    # Apply fit-all remap to mid
    print("\n## mid under fit-all remap")
    mid_tgts = []
    for si in range(5):
        bits = apply_rules(mid_ink(g0, si), rules_all)
        sig = bits_to_sig(bits)
        mid_tgts.append(sig)
        print(f"  M{si} ->")
        for line in asc(sig):
            print("   ", line)

    # Identity 10→7 for comparison already known unreachable
    mid_id = [bits_to_sig(mid_ink(g0, si)) for si in range(5)]

    # Online: alphabets + dial
    sess = Sess(_api_key())
    try:
        sess.open()
        alphas = [collect_alpha(sess, si) for si in range(5)]
        print("\n## alphabet membership (remap targets)")
        plans = []
        for si, tgt in enumerate(mid_tgts):
            in_alpha = tgt in alphas[si]
            # also check id target
            in_id = mid_id[si] in alphas[si]
            best = min((int(np.sum(np.array(s) != np.array(tgt))), s, st) for s, st in alphas[si].items())
            print(f"  slot{si} remap_in={in_alpha} id_in={in_id} best_ham={best[0]} steps={best[2]}")
            plans.append(
                {
                    "in_alpha": in_alpha,
                    "id_in": in_id,
                    "best_ham": best[0],
                    "steps": best[2] if in_alpha else (best[2] if best[0] == 0 else None),
                    "exact_steps": alphas[si].get(tgt),
                }
            )
        out["plans"] = plans
        out["mid_remap_ascii"] = [asc(s) for s in mid_tgts]

        # If all exact in alphabet, execute
        runnable = all(p["exact_steps"] is not None for p in plans)
        print(f"\n## execute runnable={runnable}")
        d = sess.reset()
        g = plane(d["frame"])
        lv0 = d.get("levels_completed")
        actions = []
        if runnable:
            for si, p in enumerate(plans):
                d = sess.reset()
                g = plane(d["frame"])
                for a in actions:
                    d = sess.action(f"ACTION{a}")
                    g = plane(d["frame"])
                g, nav, _ = move(sess, g, si)
                trial = actions + nav
                fl, n = p["exact_steps"]
                trial = trial + [fl] * n
                d = sess.reset()
                g = plane(d["frame"])
                for a in trial:
                    d = sess.action(f"ACTION{a}")
                    g = plane(d["frame"])
                assert bg(g, si) == mid_tgts[si]
                actions = trial
            d = sess.reset()
            g = plane(d["frame"])
            for a in actions:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            lv1 = d.get("levels_completed")
        else:
            # fuzzy: dial each to best_ham glyph vs remap target
            for si in range(5):
                tgt = mid_tgts[si]
                best_sig = min(alphas[si].keys(), key=lambda s: int(np.sum(np.array(s) != np.array(tgt))))
                fl, n = alphas[si][best_sig]
                d = sess.reset()
                g = plane(d["frame"])
                for a in actions:
                    d = sess.action(f"ACTION{a}")
                    g = plane(d["frame"])
                g, nav, _ = move(sess, g, si)
                # re-find from current prefix
                trial = actions + nav
                found = None
                for fll in (1, 2):
                    for nn in range(0, 8):
                        d = sess.reset()
                        g = plane(d["frame"])
                        for a in trial:
                            d = sess.action(f"ACTION{a}")
                            g = plane(d["frame"])
                        for _ in range(nn):
                            d = sess.action(f"ACTION{fll}")
                            g = plane(d["frame"])
                        if bg(g, si) == best_sig:
                            found = (fll, nn)
                            break
                    if found:
                        break
                if found and found[1]:
                    trial = trial + [found[0]] * found[1]
                actions = trial
                print(f"  fuzzy slot{si} ham={int(np.sum(np.array(best_sig)!=np.array(tgt)))} found={found}")
            d = sess.reset()
            g = plane(d["frame"])
            for a in actions:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            lv1 = d.get("levels_completed")

        print(f"  lv {lv0}->{lv1} nact={len(actions)}")
        out["combined"] = {"lv0": lv0, "lv1": lv1, "actions": actions, "runnable": runnable}

        # ---- topology fallback features while online ----
        print("\n## topology: ink CC count on top pairs / mid / bottom alpha")

        def n_cc(bits5):
            a = bits5.reshape(5, 5)
            seen = np.zeros_like(a, dtype=bool)
            n = 0
            for y in range(5):
                for x in range(5):
                    if seen[y, x] or a[y, x] == 0:
                        continue
                    n += 1
                    stack = [(x, y)]
                    seen[y, x] = True
                    while stack:
                        cx, cy = stack.pop()
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < 5 and 0 <= ny < 5 and not seen[ny, nx] and a[ny, nx]:
                                seen[ny, nx] = True
                                stack.append((nx, ny))
            return n

        pair_topo = []
        for i, (y, a, s) in enumerate(PAIRS):
            pair_topo.append(
                {
                    "pair": (y, a, s),
                    "A_cc": n_cc(X[i]),
                    "S_cc": n_cc(Y[i]),
                    "A_ink": int(X[i].sum()),
                    "S_ink": int(Y[i].sum()),
                }
            )
            print(f"  pair{i}: A_cc={pair_topo[-1]['A_cc']} S_cc={pair_topo[-1]['S_cc']} ink {pair_topo[-1]['A_ink']}->{pair_topo[-1]['S_ink']}")
        out["pair_topo"] = pair_topo

        mid_topo = [{"cc": n_cc(mid_ink(g0, si)), "ink": int(mid_ink(g0, si).sum())} for si in range(5)]
        print("  mid topo", mid_topo)
        out["mid_topo"] = mid_topo

        # Try dial each slot to match mid's CC count (and ink if possible)
        print("\n## dial to match mid CC")
        actions = []
        d = sess.reset()
        lv0 = d.get("levels_completed")
        for si in range(5):
            want_cc = mid_topo[si]["cc"]
            cands = []
            for sig, st in alphas[si].items():
                bits = (np.array(sig).reshape(5, 5) == 7).astype(np.uint8).ravel()
                if n_cc(bits) == want_cc:
                    cands.append((abs(int(bits.sum()) - mid_topo[si]["ink"]), sig, st))
            cands.sort()
            print(f"  slot{si} want_cc={want_cc} n_cand={len(cands)}")
            if not cands:
                continue
            tgt = cands[0][1]
            d = sess.reset()
            g = plane(d["frame"])
            for a in actions:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            g, nav, _ = move(sess, g, si)
            trial = actions + nav
            found = None
            for fl in (1, 2):
                for n in range(0, 8):
                    d = sess.reset()
                    g = plane(d["frame"])
                    for a in trial:
                        d = sess.action(f"ACTION{a}")
                        g = plane(d["frame"])
                    for _ in range(n):
                        d = sess.action(f"ACTION{fl}")
                        g = plane(d["frame"])
                    if bg(g, si) == tgt:
                        found = (fl, n)
                        break
                if found:
                    break
            if found and found[1]:
                trial = trial + [found[0]] * found[1]
            actions = trial
        d = sess.reset()
        g = plane(d["frame"])
        for a in actions:
            d = sess.action(f"ACTION{a}")
            g = plane(d["frame"])
        lv1 = d.get("levels_completed")
        print(f"  CC-match lv {lv0}->{lv1}")
        out["cc_match"] = {"lv0": lv0, "lv1": lv1, "actions": actions}

        cleared = (
            int(out["combined"]["lv1"] or 0) > int(out["combined"]["lv0"] or 0)
            or int(lv1 or 0) > int(lv0 or 0)
        )
        # LOO quality
        loo_ok = all(h == 0 for h in loo_hams if h is not None) and None not in loo_hams
        out["loo_perfect"] = loo_ok
        out["reading"] = "L1_CLEAR" if cleared else ("REMAP_LOO_FAIL" if not loo_ok else "REMAP_PARTIAL")
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("READING:", out["reading"], "loo_perfect", loo_ok)
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
