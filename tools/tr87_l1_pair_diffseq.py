"""tr87 L1: offline A→S diff structure → action seq; online execute candidates.

Also: treat each pair's diff mask as 4-bit nibbles → acts; or count flips per quadrant.

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

OUT = ROOT / "tests/fixtures/tr87_l1_pair_diffseq.json"
CLEAR = ROOT / "tests/fixtures/tr87_l1_clear_frame.json"
FIX = ROOT / "tests/fixtures/tr87_l1_frame_live.json"
PAIRS = [
    (12, 22, 4),
    (36, 46, 4),
    (12, 22, 13),
    (36, 46, 13),
    (12, 22, 22),
    (36, 46, 22),
]
SLOTS = (15, 22, 29, 36, 43)


def load_g():
    data = json.loads(FIX.read_text(encoding="utf-8"))
    # fixture may be summary+frame or raw
    if "frame" in data:
        fr = data["frame"]
    elif "summary" in data and "frame" not in data:
        # try alternate
        fr = data.get("raw_frame") or data.get("grid")
        if fr is None:
            raise SystemExit("no frame in fixture; need live RESET")
    else:
        fr = data
    a = np.asarray(fr, dtype=np.int64)
    return a[0] if a.ndim == 3 else a


def analyze(g):
    rows = []
    for i, (ax, sx, y0) in enumerate(PAIRS):
        Araw = g[y0 + 1 : y0 + 6, ax + 1 : ax + 6]
        S = g[y0 + 1 : y0 + 6, sx + 1 : sx + 6]
        A = np.where(Araw == 10, 7, Araw)
        # also keep raw
        diff = A != S
        # where A has 7 and S has 5 = erase; A 5 S 7 = paint
        erase = (A == 7) & (S == 5)
        paint = (A == 5) & (S == 7)
        both = (A == 7) & (S == 7)
        none = (A == 5) & (S == 5)
        # quadrant ink of S
        quads = []
        for qy in (0, 3):
            for qx in (0, 3):
                # 2x2 top-leftish; center cell separate
                block = S[qy : qy + 2, qx : qx + 2]
                quads.append(int((block == 7).sum()))
        center = int(S[2, 2] == 7)
        rows.append(
            {
                "i": i,
                "y": y0,
                "inkA": int((A == 7).sum()),
                "inkS": int((S == 7).sum()),
                "n_erase": int(erase.sum()),
                "n_paint": int(paint.sum()),
                "n_diff": int(diff.sum()),
                "quads": quads,
                "center": center,
                "erase_rows": [int(erase[r].sum()) for r in range(5)],
                "paint_rows": [int(paint[r].sum()) for r in range(5)],
                "diff_rows": [int(diff[r].sum()) for r in range(5)],
                "A_asc": ["".join(str(int(v)) for v in r) for r in A],
                "S_asc": ["".join(str(int(v)) for v in r) for r in S],
                "diff_asc": ["".join("1" if v else "0" for v in r) for r in diff],
            }
        )
    return rows


def seqs_from(rows):
    """Generate candidate action sequences from pair diffs."""
    cands = {}

    # erase/paint counts → mod4 acts
    cands["erase_mod4"] = [(r["n_erase"] % 4) + 1 for r in rows]
    cands["paint_mod4"] = [(r["n_paint"] % 4) + 1 for r in rows]
    cands["diff_mod4"] = [(r["n_diff"] % 4) + 1 for r in rows]
    cands["erase_minus_paint_mod4"] = [((r["n_erase"] - r["n_paint"]) % 4) + 1 for r in rows]

    # per pair: if paint>erase → ACT1 else ACT2; then nav by column
    seq = []
    for r in rows:
        seq.append(1 if r["n_paint"] >= r["n_erase"] else 2)
        seq.append(4 if r["i"] % 2 == 0 else 3)
    cands["paint_ge_erase_nav"] = seq

    # row-diff profile: for each pair, take argmax row of diffs → act (1..4 clamp, row0→1)
    cands["argmax_diffrow"] = [min(4, max(1, int(np.argmax(r["diff_rows"]) + 1))) for r in rows]

    # center bit + quad signature → act
    cands["center_quad0"] = [((r["center"] + r["quads"][0]) % 4) + 1 for r in rows]

    # interleaved: for each pair emit erase_mod4 then paint_mod4
    seq = []
    for r in rows:
        seq.append((r["n_erase"] % 4) + 1)
        seq.append((r["n_paint"] % 4) + 1)
    cands["erase_then_paint"] = seq
    cands["erase_then_paint_x2"] = seq * 2

    # binary from center: 1 if center else 2, walk with 4
    cands["center_walk"] = sum([[1 if r["center"] else 2, 4] for r in rows], [])

    # 5-slot program from first 5 pairs only: phase = n_diff % 7 — handled online separately
    cands["diff_mod7_as_ones"] = []
    for r in rows[:5]:
        cands["diff_mod7_as_ones"].extend([1] * (r["n_diff"] % 7) + [4])

    # long: repeat erase_mod4 to ~30
    cands["erase_mod4_x5"] = cands["erase_mod4"] * 5

    # shape: compare ink delta sign
    cands["ink_delta_sign"] = [1 if r["inkS"] >= r["inkA"] else 2 for r in rows]
    cands["ink_delta_sign_nav"] = sum([[1 if r["inkS"] >= r["inkA"] else 2, 4] for r in rows], [])

    return cands


def dial_diff_phases(sess, rows):
    """Dial each slot to phase = n_diff % 7 for pairs 0..4."""
    d = sess.reset()
    g = plane(d["frame"])
    acts = []
    for si in range(5):
        ph = rows[si]["n_diff"] % 7
        # move
        for _ in range(8):
            xs = [int(x) for y, x in np.argwhere(g == 0)]
            cur = int(np.argmin([abs(min(xs) - s) for s in SLOTS])) if xs else None
            if cur == si:
                break
            a = 4 if (si - cur) % 5 <= (cur - si) % 5 else 3
            d = sess.action(f"ACTION{a}")
            g = plane(d["frame"])
            acts.append(a)
        for _ in range(ph):
            d = sess.action("ACTION1")
            g = plane(d["frame"])
            acts.append(1)
    d = sess.action("ACTION4")
    acts.append(4)
    return acts, d


def main():
    # offline from fixture if possible
    try:
        g = load_g()
        print("loaded fixture frame", g.shape)
    except Exception as e:
        print("fixture fail", e, "— will RESET live")
        g = None

    sess = Sess(_api_key())
    out = {"rows": [], "trials": [], "cleared": False}
    try:
        sess.open()
        if g is None:
            d = sess.reset()
            g = plane(d["frame"])
        else:
            # still open session for online
            d = sess.reset()
            g = plane(d["frame"])

        rows = analyze(g)
        out["rows"] = [{k: v for k, v in r.items() if k not in ("A_asc", "S_asc", "diff_asc")} for r in rows]
        for r in rows:
            print(
                f"pair{r['i']} erase={r['n_erase']} paint={r['n_paint']} diff={r['n_diff']} "
                f"inkA={r['inkA']} inkS={r['inkS']} center={r['center']} quads={r['quads']}"
            )
            print("  A", r["A_asc"])
            print("  S", r["S_asc"])
            print("  D", r["diff_asc"])

        cands = seqs_from(rows)
        out["candidates"] = cands

        for name, seq in cands.items():
            d = sess.reset()
            for a in seq:
                d = sess.action(f"ACTION{a}")
            lv = d.get("levels_completed", 0)
            out["trials"].append({"label": name, "seq": seq, "levels": lv})
            print(f"  {name}: lv={lv} len={len(seq)} seq={seq}")
            if lv and lv > 0:
                out["cleared"] = True
                CLEAR.write_text(
                    json.dumps({"label": name, "seq": seq, "levels_completed": lv, "frame": d["frame"]}, indent=2),
                    encoding="utf-8",
                )
                print("*** L1_CLEAR ***", name)
                break

        if not out["cleared"]:
            # phase dial from diff%7
            for lab, key in (
                ("phase_diff_mod7", "n_diff"),
                ("phase_erase_mod7", "n_erase"),
                ("phase_paint_mod7", "n_paint"),
            ):
                d = sess.reset()
                g = plane(d["frame"])
                acts = []
                for si in range(5):
                    ph = rows[si][key] % 7
                    for _ in range(8):
                        xs = [int(x) for y, x in np.argwhere(g == 0)]
                        cur = int(np.argmin([abs(min(xs) - s) for s in SLOTS])) if xs else None
                        if cur == si:
                            break
                        a = 4 if (si - cur) % 5 <= (cur - si) % 5 else 3
                        d = sess.action(f"ACTION{a}")
                        g = plane(d["frame"])
                        acts.append(a)
                    for _ in range(ph):
                        d = sess.action("ACTION1")
                        g = plane(d["frame"])
                        acts.append(1)
                d = sess.action("ACTION4")
                acts.append(4)
                lv = d.get("levels_completed", 0)
                out["trials"].append({"label": lab, "seq": acts, "levels": lv})
                print(f"  {lab}: lv={lv} n={len(acts)}")
                if lv and lv > 0:
                    out["cleared"] = True
                    CLEAR.write_text(
                        json.dumps({"label": lab, "seq": acts, "levels_completed": lv, "frame": d["frame"]}, indent=2),
                        encoding="utf-8",
                    )
                    break

        # bonus: pair-structure — for left col pairs (0,2,4) dial slots 0,1,2 to best ham vs S;
        # for right (1,3,5) use as "check only" — already weak. Try dial slot i to best vs pair i S for i<5
        if not out["cleared"]:
            d = sess.reset()
            g = plane(d["frame"])
            # build cycles quickly
            cycles = []
            for si in range(5):
                d = sess.reset()
                g = plane(d["frame"])
                for _ in range(8):
                    xs = [int(x) for y, x in np.argwhere(g == 0)]
                    cur = int(np.argmin([abs(min(xs) - s) for s in SLOTS])) if xs else None
                    if cur == si:
                        break
                    a = 4 if (si - cur) % 5 <= (cur - si) % 5 else 3
                    d = sess.action(f"ACTION{a}")
                    g = plane(d["frame"])
                start = tuple(int(v) for v in g[52:57, SLOTS[si] : SLOTS[si] + 5].ravel())
                seq = [start]
                for _ in range(8):
                    d = sess.action("ACTION1")
                    g = plane(d["frame"])
                    sig = tuple(int(v) for v in g[52:57, SLOTS[si] : SLOTS[si] + 5].ravel())
                    if sig == start:
                        break
                    seq.append(sig)
                cycles.append(seq)

            for target_kind in ("S", "A"):
                d = sess.reset()
                g = plane(d["frame"])
                acts = []
                hams = []
                for si in range(5):
                    ax, sx, y0 = PAIRS[si]
                    if target_kind == "S":
                        T = g[y0 + 1 : y0 + 6, sx + 1 : sx + 6]
                    else:
                        T = np.where(g[y0 + 1 : y0 + 6, ax + 1 : ax + 6] == 10, 7, g[y0 + 1 : y0 + 6, ax + 1 : ax + 6])
                    tsig = tuple(int(v) for v in T.ravel())
                    best = min(cycles[si], key=lambda s: int(np.sum(np.array(s) != np.array(tsig))))
                    hams.append(int(np.sum(np.array(best) != np.array(tsig))))
                    for _ in range(8):
                        xs = [int(x) for y, x in np.argwhere(g == 0)]
                        cur = int(np.argmin([abs(min(xs) - s) for s in SLOTS])) if xs else None
                        if cur == si:
                            break
                        a = 4 if (si - cur) % 5 <= (cur - si) % 5 else 3
                        d = sess.action(f"ACTION{a}")
                        g = plane(d["frame"])
                        acts.append(a)
                    for _ in range(8):
                        curbg = tuple(int(v) for v in g[52:57, SLOTS[si] : SLOTS[si] + 5].ravel())
                        if curbg == best:
                            break
                        d = sess.action("ACTION1")
                        g = plane(d["frame"])
                        acts.append(1)
                d = sess.action("ACTION4")
                acts.append(4)
                lv = d.get("levels_completed", 0)
                out["trials"].append({"label": f"pair_best_{target_kind}", "hams": hams, "seq": acts, "levels": lv})
                print(f"  pair_best_{target_kind}: hams={hams} lv={lv}")
                if lv and lv > 0:
                    out["cleared"] = True
                    CLEAR.write_text(
                        json.dumps({"label": f"pair_best_{target_kind}", "seq": acts, "levels_completed": lv, "frame": d["frame"]}, indent=2),
                        encoding="utf-8",
                    )
                    break

        out["best_lv"] = max((t.get("levels") or 0 for t in out["trials"]), default=0)
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print("DONE", out["best_lv"], out["cleared"], "->", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
