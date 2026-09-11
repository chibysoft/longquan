"""tr87 L1: H25 non-pixel dictionary — mid≈topA by moments/skeleton → dial paired S
(or nearest dialable). Also try mid features → nearest alphabet glyph directly.

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

OUT = ROOT / "tests/fixtures/tr87_l1_feat_dict.json"
SLOTS = (15, 22, 29, 36, 43)
PAIRS = [(4, 12, 22), (4, 36, 46), (13, 12, 22), (13, 36, 46), (22, 12, 22), (22, 36, 46)]


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


def replay(sess, actions):
    d = sess.reset()
    g = plane(d["frame"])
    for a in actions:
        g, d = go(sess, g, a)
    return g, d


def phases_to_actions(phases):
    actions, cur = [], 0
    for si, ph in enumerate(phases):
        df, db = (si - cur) % 5, (cur - si) % 5
        actions.extend([4] * df if df <= db else [3] * db)
        cur = si
        actions.extend([1] * int(ph))
    return actions


# ---- features ----

def ink_bits_from_patch(patch, ink_val):
    return (patch == ink_val).astype(np.uint8)


def n_cc(bits):
    a = bits.reshape(5, 5) if bits.ndim == 1 else bits
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


def skeletonize(bits5):
    """Simple iterative thinning for 5x5 binary."""
    img = bits5.reshape(5, 5).astype(np.uint8).copy()

    def neighbors(y, x):
        pts = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                ny, nx = y + dy, x + dx
                if 0 <= ny < 5 and 0 <= nx < 5:
                    pts.append(int(img[ny, nx]))
                else:
                    pts.append(0)
        # order: p2 p3 p4 p5 p6 p7 p8 p9 (N,NE,E,SE,S,SW,W,NW)
        return [pts[1], pts[2], pts[4], pts[7], pts[6], pts[5], pts[3], pts[0]]

    changed = True
    guard = 0
    while changed and guard < 20:
        guard += 1
        changed = False
        for step in (0, 1):
            to_del = []
            for y in range(5):
                for x in range(5):
                    if img[y, x] == 0:
                        continue
                    nbr = neighbors(y, x)
                    bp = sum(nbr)
                    if not (2 <= bp <= 6):
                        continue
                    # transitions
                    seq = nbr + [nbr[0]]
                    a = sum(1 for i in range(8) if seq[i] == 0 and seq[i + 1] == 1)
                    if a != 1:
                        continue
                    p2, p4, p6, p8 = nbr[0], nbr[2], nbr[4], nbr[6]
                    if step == 0:
                        if p4 * p6 * p8 != 0:
                            continue
                        if p2 * p4 * p6 != 0:
                            continue
                    else:
                        if p2 * p4 * p8 != 0:
                            continue
                        if p2 * p6 * p8 != 0:
                            continue
                    to_del.append((y, x))
            if to_del:
                changed = True
                for y, x in to_del:
                    img[y, x] = 0
    return img.ravel()


def moments(bits):
    a = bits.reshape(5, 5).astype(np.float64)
    ink = float(a.sum())
    if ink < 1:
        return (0.0,) * 8
    ys, xs = np.mgrid[0:5, 0:5]
    cx = float((xs * a).sum() / ink)
    cy = float((ys * a).sum() / ink)
    mu20 = float((((xs - cx) ** 2) * a).sum() / ink)
    mu02 = float((((ys - cy) ** 2) * a).sum() / ink)
    mu11 = float((((xs - cx) * (ys - cy)) * a).sum() / ink)
    # Hu-ish
    hu1 = mu20 + mu02
    hu2 = (mu20 - mu02) ** 2 + 4 * mu11**2
    sk = skeletonize(bits.astype(np.uint8))
    return (ink, cx, cy, mu20, mu02, mu11, hu1, hu2, float(sk.sum()), float(n_cc(bits)))


def feat_dist(fa, fb, weights=None):
    a, b = np.array(fa, dtype=float), np.array(fb, dtype=float)
    # normalize by scale of each dim using (a+b)/2 + eps
    scale = np.abs(a) + np.abs(b) + 1e-6
    d = (a - b) / scale
    if weights is not None:
        d = d * np.array(weights)
    return float(np.sqrt((d**2).sum()))


def row_proj(bits):
    return tuple(int(x) for x in bits.reshape(5, 5).sum(axis=1))


def col_proj(bits):
    return tuple(int(x) for x in bits.reshape(5, 5).sum(axis=0))


def proj_dist(a, b):
    return sum(abs(x - y) for x, y in zip(a, b))


def bits_to_sig(bits):
    return tuple(int(v) for v in np.where(np.asarray(bits).reshape(5, 5) == 1, 7, 5).ravel())


def sig_to_bits(sig):
    return (np.array(sig).reshape(5, 5) == 7).astype(np.uint8).ravel()


def main():
    g0 = np.asarray(
        json.loads((ROOT / "tests/fixtures/tr87_l1_frame_live.json").read_text(encoding="utf-8"))["frame"]
    )
    if g0.ndim == 3:
        g0 = g0[0]

    # mid ink = color10
    mids = []
    for x0 in (15, 22, 29, 36, 43):
        mids.append(ink_bits_from_patch(g0[41:46, x0 : x0 + 5], 10).ravel())

    pairs = []
    for y0, ax, sx in PAIRS:
        Ab = ink_bits_from_patch(g0[y0 + 1 : y0 + 6, ax + 1 : ax + 6], 10).ravel()
        Sb = ink_bits_from_patch(g0[y0 + 1 : y0 + 6, sx + 1 : sx + 6], 7).ravel()
        pairs.append({"A": Ab, "S": Sb, "pos": (y0, ax, sx), "fA": moments(Ab), "fS": moments(Sb)})

    mid_f = [moments(m) for m in mids]
    p("## mid feats", [ (round(f[0],1), round(f[1],2), round(f[2],2), int(f[9])) for f in mid_f ])

    # Match mid → nearest A by feature dist; target = paired S
    p("## dict: mid → nearest A → S")
    dict_targets = []
    for si in range(5):
        best = min(
            ((feat_dist(mid_f[si], pr["fA"]), ji, pr) for ji, pr in enumerate(pairs)),
            key=lambda x: x[0],
        )
        # also proj match
        best_p = min(
            (
                (
                    proj_dist(row_proj(mids[si]), row_proj(pr["A"]))
                    + proj_dist(col_proj(mids[si]), col_proj(pr["A"])),
                    ji,
                    pr,
                )
                for ji, pr in enumerate(pairs)
            ),
            key=lambda x: x[0],
        )
        p(
            f"  M{si} feat→pair{best[1]}{best[2]['pos']} d={best[0]:.3f} | "
            f"proj→pair{best_p[1]} d={best_p[0]}"
        )
        dict_targets.append(bits_to_sig(best[2]["S"]))

    # Also: mid → nearest A by skeleton ham
    p("## dict: mid skel ham → A → S")
    skel_targets = []
    for si in range(5):
        msk = skeletonize(mids[si])
        best = min(
            ((int(np.sum(msk != skeletonize(pr["A"]))), ji, pr) for ji, pr in enumerate(pairs)),
            key=lambda x: x[0],
        )
        p(f"  M{si} skel→pair{best[1]} ham={best[0]}")
        skel_targets.append(bits_to_sig(best[2]["S"]))

    sess = Sess(_api_key())
    out = {"dict_assign": [], "plans": {}}
    try:
        sess.open()
        # cycles
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
            p(f"  cycle{si}={len(cyc)}")

        def dial_targets(name, targets):
            phases, hams, exact = [], [], []
            for si, tgt in enumerate(targets):
                if tgt in cycles[si]:
                    phases.append(cycles[si].index(tgt))
                    hams.append(0)
                    exact.append(True)
                else:
                    best = min(
                        (int(np.sum(np.array(sig) != np.array(tgt))), n)
                        for n, sig in enumerate(cycles[si])
                    )
                    phases.append(best[1])
                    hams.append(best[0])
                    exact.append(False)
            acts = phases_to_actions(phases)
            g, d = replay(sess, acts)
            lv = d.get("levels_completed")
            p(f"  [{name}] exact={exact} hams={hams} lv={lv} nact={len(acts)}")
            # try lap submit
            g2, d2 = replay(sess, acts + [4] * 5)
            lv2 = d2.get("levels_completed")
            p(f"  [{name}+lap4] lv={lv2}")
            rec = {
                "exact": exact,
                "hams": hams,
                "phases": phases,
                "lv": lv,
                "lv_lap": lv2,
                "actions": acts,
            }
            if int(lv or 0) > 0 or int(lv2 or 0) > 0:
                rec["cleared"] = True
                (ROOT / "tests/fixtures/tr87_l1_clear_frame.json").write_text(
                    json.dumps({"frame": d2["frame"] if int(lv2 or 0) > 0 else d["frame"],
                                "levels": max(int(lv or 0), int(lv2 or 0)),
                                "name": name, "actions": acts}, indent=2),
                    encoding="utf-8",
                )
            return rec

        out["plans"]["feat_dict"] = dial_targets("feat_dict", dict_targets)
        out["plans"]["skel_dict"] = dial_targets("skel_dict", skel_targets)

        # H25b: map mid features directly onto each slot's alphabet (no pairs)
        p("## direct: mid feats → nearest glyph in slot alphabet")
        phases = []
        for si in range(5):
            mf = mid_f[si]
            msk = skeletonize(mids[si])
            mrow, mcol = row_proj(mids[si]), col_proj(mids[si])
            best = None
            for n, sig in enumerate(cycles[si]):
                b = sig_to_bits(sig)
                # composite score
                d_mom = feat_dist(mf, moments(b))
                d_skel = int(np.sum(msk != skeletonize(b)))
                d_proj = proj_dist(mrow, row_proj(b)) + proj_dist(mcol, col_proj(b))
                # ink+cc
                d_ink = abs(int(mids[si].sum()) - int(b.sum()))
                d_cc = abs(n_cc(mids[si]) - n_cc(b))
                score = d_mom + 0.3 * d_skel + 0.2 * d_proj + 0.1 * d_ink + 0.5 * d_cc
                if best is None or score < best[0]:
                    best = (score, n, d_mom, d_skel, d_proj)
            phases.append(best[1])
            p(f"  slot{si} n={best[1]} score={best[0]:.3f} mom={best[2]:.3f} sk={best[3]} pr={best[4]}")
        acts = phases_to_actions(phases)
        g, d = replay(sess, acts)
        lv = d.get("levels_completed")
        p(f"  [direct_feat] lv={lv}")
        g2, d2 = replay(sess, acts + [4] * 5)
        p(f"  [direct_feat+lap] lv={d2.get('levels_completed')}")
        out["plans"]["direct_feat"] = {
            "phases": phases,
            "lv": lv,
            "lv_lap": d2.get("levels_completed"),
            "actions": acts,
        }

        # H25c: use mid ink as color5 (holes) instead of 10
        p("## mid holes(5) feats → alphabet")
        mids5 = []
        for x0 in (15, 22, 29, 36, 43):
            mids5.append(ink_bits_from_patch(g0[41:46, x0 : x0 + 5], 5).ravel())
        phases = []
        for si in range(5):
            mf = moments(mids5[si])
            best = None
            for n, sig in enumerate(cycles[si]):
                b = sig_to_bits(sig)
                score = feat_dist(mf, moments(b))
                if best is None or score < best[0]:
                    best = (score, n)
            phases.append(best[1])
            p(f"  slot{si} n={best[1]} d={best[0]:.3f}")
        acts = phases_to_actions(phases)
        g, d = replay(sess, acts)
        p(f"  [holes_feat] lv={d.get('levels_completed')}")
        out["plans"]["holes_feat"] = {"phases": phases, "lv": d.get("levels_completed"), "actions": acts}

        # Validate dictionary consistency: does feat_dist(A,S) small within pairs vs across?
        p("## pair A↔S feat distances (same pair vs cross)")
        same, cross = [], []
        for i, pi in enumerate(pairs):
            same.append(feat_dist(pi["fA"], pi["fS"]))
            for j, pj in enumerate(pairs):
                if i != j:
                    cross.append(feat_dist(pi["fA"], pj["fS"]))
        p(f"  same mean={np.mean(same):.3f} cross mean={np.mean(cross):.3f}")
        out["pair_feat"] = {"same": same, "cross_mean": float(np.mean(cross)), "same_mean": float(np.mean(same))}

        # H26: trajectory — structured long sequences watching levels
        p("## H26 trajectory samples")
        trajs = {
            "slot_round_flip": [],  # visit 0..4, flip1 each, repeat 3
            "count_to_y63_half": [1] * 64,  # half step bar
            "alt_12_on_walk": [],
            "sweep_all_phases": [],  # each slot full period
        }
        # build slot_round_flip
        seq = []
        cur = 0
        for _rep in range(3):
            for si in range(5):
                df, db = (si - cur) % 5, (cur - si) % 5
                seq.extend([4] * df if df <= db else [3] * db)
                cur = si
                seq.append(1)
        trajs["slot_round_flip"] = seq
        # alt 12 on walk
        seq = []
        cur = 0
        for i in range(20):
            si = i % 5
            df, db = (si - cur) % 5, (cur - si) % 5
            seq.extend([4] * df if df <= db else [3] * db)
            cur = si
            seq.append(1 if i % 2 == 0 else 2)
        trajs["alt_12_on_walk"] = seq
        # sweep
        seq = []
        cur = 0
        for si in range(5):
            df, db = (si - cur) % 5, (cur - si) % 5
            seq.extend([4] * df if df <= db else [3] * db)
            cur = si
            seq.extend([1] * 7)
        trajs["sweep_all_phases"] = seq

        traj_res = []
        for name, seq in trajs.items():
            g, d = replay(sess, seq)
            lv = d.get("levels_completed")
            # y63 colored count
            g = plane(d["frame"])
            n4 = int(np.sum(g[63, :] == 4))
            p(f"  traj {name}: lv={lv} y63_c4={n4} nact={len(seq)}")
            traj_res.append({"name": name, "lv": lv, "y63_c4": n4, "nact": len(seq)})
            if int(lv or 0) > 0:
                (ROOT / "tests/fixtures/tr87_l1_clear_frame.json").write_text(
                    json.dumps({"frame": d["frame"], "levels": lv, "name": name, "actions": seq}, indent=2),
                    encoding="utf-8",
                )
        out["traj"] = traj_res

        cleared = any(
            int(v.get("lv") or 0) > 0 or int(v.get("lv_lap") or 0) > 0
            for v in out["plans"].values()
        ) or any(int(t["lv"] or 0) > 0 for t in traj_res)
        out["reading"] = "L1_CLEAR" if cleared else "FEAT_PARTIAL"
        # dictionary signal?
        out["dict_signal"] = out["pair_feat"]["same_mean"] < out["pair_feat"]["cross_mean"]
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        p("READING:", out["reading"], "dict_signal", out["dict_signal"])
        p("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
