"""tr87 L1: geometric transform from top pairs A→S; apply to mid → dial targets.

Also topology score: match CC count + ink + bounding-box aspect of mid.

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

OUT = ROOT / "tests/fixtures/tr87_l1_geom_xform.json"
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
    return tuple(int(v) for v in g[52:57, SLOTS[si] : SLOTS[si] + 5].ravel())


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


def bin7(p):
    return (p == 7).astype(np.int64)


def transforms(p):
    """Yield (name, transformed binary 5x5). p is 0/1."""
    yield "id", p
    yield "rot90", np.rot90(p, 1)
    yield "rot180", np.rot90(p, 2)
    yield "rot270", np.rot90(p, 3)
    yield "flip_ud", np.flipud(p)
    yield "flip_lr", np.fliplr(p)
    yield "transpose", p.T
    yield "flip_ud_lr", np.flipud(np.fliplr(p))
    # shift by 1
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            q = np.zeros_like(p)
            ys = slice(max(0, dy), min(5, 5 + dy))
            xs = slice(max(0, dx), min(5, 5 + dx))
            ysrc = slice(max(0, -dy), min(5, 5 - dy))
            xsrc = slice(max(0, -dx), min(5, 5 - dx))
            q[ys, xs] = p[ysrc, xsrc]
            yield f"shift_{dy}_{dx}", q


def ham_bin(a, b):
    return int(np.sum(a != b))


def cycles(sess):
    out = []
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
        out.append(seq)
    return out


def dial(sess, targets, label, out):
    d = sess.reset()
    g = plane(d["frame"])
    acts = []
    for si, tgt in enumerate(targets):
        g, m, _ = move(sess, g, si)
        acts.extend(m)
        for _ in range(8):
            if bg(g, si) == tgt:
                break
            d = sess.action("ACTION1")
            g = plane(d["frame"])
            acts.append(1)
    d = sess.action("ACTION4")
    acts.append(4)
    lv = d.get("levels_completed", 0)
    out["trials"].append({"label": label, "levels": lv, "n": len(acts)})
    print(f"  {label}: lv={lv}")
    if lv and lv > 0:
        out["cleared"] = True
        CLEAR.write_text(
            json.dumps({"label": label, "seq": acts, "levels_completed": lv, "frame": d["frame"]}, indent=2),
            encoding="utf-8",
        )
        print("*** L1_CLEAR ***", label)
        return True
    return False


def main():
    sess = Sess(_api_key())
    out = {"pair_xform": [], "trials": [], "cleared": False}
    try:
        sess.open()
        d = sess.reset()
        g = plane(d["frame"])

        # Analyze which transform best explains each pair A→S
        for i, (ax, sx, y0) in enumerate(PAIRS):
            A = np.where(g[y0 + 1 : y0 + 6, ax + 1 : ax + 6] == 10, 7, g[y0 + 1 : y0 + 6, ax + 1 : ax + 6])
            S = g[y0 + 1 : y0 + 6, sx + 1 : sx + 6]
            Ab, Sb = bin7(A), bin7(S)
            ranked = sorted(((ham_bin(t, Sb), name) for name, t in transforms(Ab)), key=lambda x: x[0])
            out["pair_xform"].append({"i": i, "best": ranked[:5]})
            print(f"pair{i} best xforms", ranked[:5])

        # Global: pick transform that minimizes sum ham over 6 pairs
        scores = {}
        for name, _ in transforms(np.zeros((5, 5), dtype=np.int64)):
            scores[name] = 0
        for ax, sx, y0 in PAIRS:
            A = np.where(g[y0 + 1 : y0 + 6, ax + 1 : ax + 6] == 10, 7, g[y0 + 1 : y0 + 6, ax + 1 : ax + 6])
            S = g[y0 + 1 : y0 + 6, sx + 1 : sx + 6]
            Ab, Sb = bin7(A), bin7(S)
            for name, t in transforms(Ab):
                scores[name] += ham_bin(t, Sb)
        ranked_g = sorted(scores.items(), key=lambda x: x[1])
        out["global_xform"] = ranked_g[:10]
        print("global best", ranked_g[:10])

        cy = cycles(sess)
        mids_bin = []
        for x0 in MID_X:
            p = g[41:46, x0 + 1 : x0 + 6]
            mids_bin.append(bin7(np.where(p == 10, 7, p)))

        # Apply best few global transforms to mid → target binary → map to 5/7 glyph → best cycle
        for xname, xscore in ranked_g[:6]:
            # get transform fn by re-running on mid
            targets = []
            hams = []
            for si in range(5):
                # find transformed mid
                tmap = dict(transforms(mids_bin[si]))
                tb = tmap[xname]
                # as 5/7 sig
                tgt = tuple(int(7 if v else 5) for v in tb.ravel())
                best = min(cy[si], key=lambda s: int(np.sum(np.array(s) != np.array(tgt))))
                hams.append(int(np.sum(np.array(best) != np.array(tgt))))
                targets.append(best)
            print(f"apply {xname} (pair_ham_sum={xscore}) mid hams={hams}")
            out["trials"].append({"label": f"geom_{xname}_hams", "hams": hams, "pair_sum": xscore})
            if dial(sess, targets, f"H19_geom_{xname}", out):
                break

        # Per-slot: use that slot's "corresponding" pair's best transform on mid[si]
        if not out["cleared"]:
            targets = []
            hams = []
            for si in range(5):
                best_name = out["pair_xform"][si]["best"][0][1]
                tmap = dict(transforms(mids_bin[si]))
                tb = tmap[best_name]
                tgt = tuple(int(7 if v else 5) for v in tb.ravel())
                best = min(cy[si], key=lambda s: int(np.sum(np.array(s) != np.array(tgt))))
                hams.append(int(np.sum(np.array(best) != np.array(tgt))))
                targets.append(best)
            print("per-pair-xform mid hams", hams)
            dial(sess, targets, "H19_per_pair_xform", out)

        # Topology: match (ink, cc) of mid exactly if possible else closest
        if not out["cleared"]:
            targets = []
            for si in range(5):
                want_ink = int(mids_bin[si].sum())
                p = mids_bin[si]
                seen = np.zeros_like(p, dtype=bool)
                want_cc = 0
                for y in range(5):
                    for x in range(5):
                        if seen[y, x] or p[y, x] == 0:
                            continue
                        want_cc += 1
                        st = [(x, y)]
                        seen[y, x] = True
                        while st:
                            cx, cy_ = st.pop()
                            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                                nx, ny = cx + dx, cy_ + dy
                                if 0 <= nx < 5 and 0 <= ny < 5 and not seen[ny, nx] and p[ny, nx]:
                                    seen[ny, nx] = True
                                    st.append((nx, ny))

                def score(sig, wi=want_ink, wc=want_cc):
                    a = np.array(sig).reshape(5, 5)
                    b = (a == 7).astype(np.int64)
                    ink = int(b.sum())
                    seen2 = np.zeros_like(b, dtype=bool)
                    c2 = 0
                    for yy in range(5):
                        for xx in range(5):
                            if seen2[yy, xx] or b[yy, xx] == 0:
                                continue
                            c2 += 1
                            st2 = [(xx, yy)]
                            seen2[yy, xx] = True
                            while st2:
                                cx, cy2 = st2.pop()
                                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                                    nx, ny = cx + dx, cy2 + dy
                                    if 0 <= nx < 5 and 0 <= ny < 5 and not seen2[ny, nx] and b[ny, nx]:
                                        seen2[ny, nx] = True
                                        st2.append((nx, ny))
                    return abs(ink - wi) * 10 + abs(c2 - wc)

                targets.append(min(cy[si], key=score))
            dial(sess, targets, "H20_topo_ink_cc", out)

        out["best_lv"] = max((t.get("levels") or 0 for t in out["trials"]), default=0)
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print("DONE", out["best_lv"], out["cleared"])
    finally:
        sess.close()


if __name__ == "__main__":
    main()
