"""tr87 L1: partial-geometry match (3x3 / fingerprint) + bottom-as-sequence-of-top reading.

H15: dial each slot so center 3x3 (or row2 / col2) best-matches mid remap
H16: bottoms should equal the 5 left-or-mixed top glyphs in reading order (best ham)
H17: sorted unique hashes of bottoms == sorted hashes of some top subset
H18: BFS depth≤6 from reset scoring (n_exact_dialable + -sum ham to assigned targets); check lv

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

OUT = ROOT / "tests/fixtures/tr87_l1_partial_match.json"
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


def as5(sig):
    return np.array(sig).reshape(5, 5)


def score_c33(sig, tgt5):
    a, b = as5(sig)[1:4, 1:4], tgt5[1:4, 1:4]
    return int(np.sum(a != b))


def score_row2(sig, tgt5):
    return int(np.sum(as5(sig)[2, :] != tgt5[2, :]))


def score_col2(sig, tgt5):
    return int(np.sum(as5(sig)[:, 2] != tgt5[:, 2]))


def dial_targets(sess, targets, label, out):
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
    out["trials"].append({"label": label, "seq": acts, "levels": lv})
    print(f"  {label}: lv={lv} n={len(acts)}")
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
    out = {"trials": [], "cleared": False, "notes": []}
    try:
        sess.open()
        d = sess.reset()
        g0 = plane(d["frame"])
        cy = cycles(sess)
        print("cycles", [len(c) for c in cy])

        mids = []
        for x0 in MID_X:
            p = g0[41:46, x0 + 1 : x0 + 6].copy()
            p7 = np.where(p == 10, 7, p)
            p7 = np.where(p7 == 10, 7, p7)
            # only 5/7/10 present; map 10→7 already; keep 5
            mids.append(p7)

        # H15 partial geometry
        for sname, sfn in (("c33", score_c33), ("row2", score_row2), ("col2", score_col2)):
            targets = []
            scores = []
            for si in range(5):
                best = min(cy[si], key=lambda s: sfn(s, mids[si]))
                scores.append(sfn(best, mids[si]))
                targets.append(best)
            out["notes"].append({f"H15_{sname}_scores": scores})
            print(f"H15_{sname} best scores", scores)
            if dial_targets(sess, targets, f"H15_{sname}", out):
                break

        if not out["cleared"]:
            # H16: assign top S glyphs to slots by reading order
            # left column S: pairs 0,2,4 → slots 0,1,2; right pairs 1,3 → slots 3,4 (pair5 unused)
            topS = []
            topA = []
            for ax, sx, y0 in PAIRS:
                S = g0[y0 + 1 : y0 + 6, sx + 1 : sx + 6]
                A = np.where(g0[y0 + 1 : y0 + 6, ax + 1 : ax + 6] == 10, 7, g0[y0 + 1 : y0 + 6, ax + 1 : ax + 6])
                topS.append(tuple(int(v) for v in S.ravel()))
                topA.append(tuple(int(v) for v in A.ravel()))

            layouts = {
                "left3_right2_S": [topS[0], topS[2], topS[4], topS[1], topS[3]],
                "row_major_S5": topS[:5],
                "left3_right2_A": [topA[0], topA[2], topA[4], topA[1], topA[3]],
                "row_major_A5": topA[:5],
            }
            for lname, goals in layouts.items():
                targets = []
                hams = []
                for si, goal in enumerate(goals):
                    best = min(cy[si], key=lambda s: int(np.sum(np.array(s) != np.array(goal))))
                    hams.append(int(np.sum(np.array(best) != np.array(goal))))
                    targets.append(best)
                out["notes"].append({f"H16_{lname}_hams": hams})
                print(f"H16_{lname} hams", hams)
                if dial_targets(sess, targets, f"H16_{lname}", out):
                    break

        if not out["cleared"]:
            # H18: short BFS — all sequences of length ≤5 over {1,2,3,4}, check lv
            # 4^5=1024 too many; do length ≤4 = 256, or length 5 with pruning
            print("H18 BFS len<=4")
            from itertools import product

            found = False
            for L in (1, 2, 3, 4):
                for seq in product((1, 2, 3, 4), repeat=L):
                    d = sess.reset()
                    for a in seq:
                        d = sess.action(f"ACTION{a}")
                    lv = d.get("levels_completed", 0)
                    if lv and lv > 0:
                        out["cleared"] = True
                        out["trials"].append({"label": f"H18_bfs_{seq}", "seq": list(seq), "levels": lv})
                        CLEAR.write_text(
                            json.dumps({"label": "H18_bfs", "seq": list(seq), "levels_completed": lv, "frame": d["frame"]}, indent=2),
                            encoding="utf-8",
                        )
                        print("*** L1_CLEAR ***", seq)
                        found = True
                        break
                if found:
                    break
                print(f"  BFS L={L} empty")
            if not found:
                out["trials"].append({"label": "H18_bfs_le4", "levels": 0, "note": "4+16+64+256 empty"})

        # H18b: targeted longer — for each slot, try all 7 phases alone (others reset)
        if not out["cleared"]:
            print("H18b single-slot phases")
            for si in range(5):
                for ph in range(7):
                    d = sess.reset()
                    g = plane(d["frame"])
                    acts = []
                    g, m, _ = move(sess, g, si)
                    acts.extend(m)
                    for _ in range(ph):
                        d = sess.action("ACTION1")
                        g = plane(d["frame"])
                        acts.append(1)
                    d = sess.action("ACTION4")
                    acts.append(4)
                    lv = d.get("levels_completed", 0)
                    if lv and lv > 0:
                        out["cleared"] = True
                        CLEAR.write_text(
                            json.dumps({"label": f"slot{si}_ph{ph}", "seq": acts, "levels_completed": lv, "frame": d["frame"]}, indent=2),
                            encoding="utf-8",
                        )
                        print("*** L1_CLEAR ***", si, ph)
                        break
                if out["cleared"]:
                    break
            if not out["cleared"]:
                out["trials"].append({"label": "H18b_single_slot", "levels": 0})
                print("  single-slot all empty")

        out["best_lv"] = max((t.get("levels") or 0 for t in out["trials"]), default=0)
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print("DONE", out["best_lv"], out["cleared"])
    finally:
        sess.close()


if __name__ == "__main__":
    main()
