"""tr87 L1: H27 mid as checksum/combine of bottom glyphs; solve phases offline.

Also H28: mid[i] == bottom[i] XOR bottom[j] relations; scan.

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

OUT = ROOT / "tests/fixtures/tr87_l1_checksum.json"
SLOTS = (15, 22, 29, 36, 43)


def p(*a, **k):
    print(*a, **k, flush=True)


def bg(g, si):
    return tuple(int(v) for v in g[52:57, SLOTS[si] : SLOTS[si] + 5].ravel())


def sel(g):
    xs = [int(x) for y, x in np.argwhere(g == 0)]
    return int(np.argmin([abs(min(xs) - s) for s in SLOTS])) if xs else None


def move(sess, g, ti):
    for _ in range(8):
        cur = sel(g)
        if cur == ti:
            return g
        a = 4 if (ti - cur) % 5 <= (cur - ti) % 5 else 3
        d = sess.action(f"ACTION{a}")
        g = plane(d["frame"])
    return g


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


def sig_bits(sig):
    return (np.array(sig).reshape(5, 5) == 7).astype(np.uint8).ravel()


def main():
    g0 = np.asarray(
        json.loads((ROOT / "tests/fixtures/tr87_l1_frame_live.json").read_text(encoding="utf-8"))["frame"]
    )
    if g0.ndim == 3:
        g0 = g0[0]
    mids = []
    for x0 in (15, 22, 29, 36, 43):
        mids.append((g0[41:46, x0 : x0 + 5] == 10).astype(np.uint8).ravel())
    mid_all = np.concatenate(mids)  # 125

    sess = Sess(_api_key())
    out = {}
    try:
        sess.open()
        cycles = []
        bit_cycles = []
        for si in range(5):
            d = sess.reset()
            g = plane(d["frame"])
            g = move(sess, g, si)
            start = bg(g, si)
            cyc = [start]
            for _ in range(6):
                g, d = go(sess, g, 1)
                sig = bg(g, si)
                if sig == start:
                    break
                cyc.append(sig)
            cycles.append(cyc)
            bit_cycles.append([sig_bits(s) for s in cyc])

        # H27a: XOR of all 5 bottom == concat mid? or XOR of mids?
        p("## H27 XOR-all-bottom vs mid")
        best = None
        # sample: can't enum 16807 with heavy ops slowly — enum offline
        for ph in np.ndindex(7, 7, 7, 7, 7):
            acc = np.zeros(25, dtype=np.uint8)
            for si in range(5):
                acc ^= bit_cycles[si][ph[si]]
            # compare to each mid and to xor of mids
            mx = np.zeros(25, dtype=np.uint8)
            for m in mids:
                mx ^= m
            h_mx = int(np.sum(acc != mx))
            h_each = [int(np.sum(acc != m)) for m in mids]
            h_min = min(h_each)
            score = (h_mx, h_min)
            if best is None or score < best[0]:
                best = (score, ph, h_each)
        p(f"  best XOR-all vs xor(mids) ham={best[0][0]} vs-each-min={best[0][1]} ph={best[1]}")
        out["xor_all"] = {"ham_mx": best[0][0], "ham_each_min": best[0][1], "ph": list(best[1])}

        # H27b: per-slot mid[i] == bottom[i] XOR bottom[(i+1)%5]
        p("## H27b mid[i] == b[i] XOR b[i+1]")
        best2 = None
        hits = 0
        for ph in np.ndindex(7, 7, 7, 7, 7):
            ok = 0
            for i in range(5):
                pred = bit_cycles[i][ph[i]] ^ bit_cycles[(i + 1) % 5][ph[(i + 1) % 5]]
                if np.array_equal(pred, mids[i]):
                    ok += 1
            if best2 is None or ok > best2[0]:
                best2 = (ok, ph)
            if ok == 5:
                hits += 1
                break
        p(f"  best slots_matched={best2[0]}/5 ph={best2[1]} exact5={hits>0}")
        out["xor_adj"] = {"best_ok": best2[0], "ph": list(best2[1]), "exact5": hits > 0}

        # H27c: mid[i] == OR/AND of all bottoms projected? too weak
        # mid[i] == bottom[i] XOR constant_mask learned from... skip

        # H27d: strip XOR: concat 5 bottoms XOR equals mid concat
        p("## H27d concat XOR / equality")
        best3 = None
        for ph in np.ndindex(7, 7, 7, 7, 7):
            cat = np.concatenate([bit_cycles[si][ph[si]] for si in range(5)])
            h = int(np.sum(cat != mid_all))
            if best3 is None or h < best3[0]:
                best3 = (h, ph)
        p(f"  best concat ham={best3[0]}/125 ph={best3[1]}")  # should be 42 from H24
        out["concat"] = {"ham": best3[0], "ph": list(best3[1])}

        # H27e: mid[i] == bottom[pi] for some permutation — assignment
        # already know exact mid not in alphabets

        # If xor_adj exact or xor_all ham0, dial
        to_try = []
        if out["xor_adj"]["exact5"]:
            to_try.append(("xor_adj", out["xor_adj"]["ph"]))
        if out["xor_all"]["ham_mx"] == 0:
            to_try.append(("xor_all", out["xor_all"]["ph"]))
        # also dial best xor_adj even if partial
        to_try.append(("xor_adj_best", out["xor_adj"]["ph"]))
        to_try.append(("xor_all_best", out["xor_all"]["ph"]))

        p("## dial candidates")
        results = []
        seen = set()
        for name, ph in to_try:
            tph = tuple(ph)
            if tph in seen:
                continue
            seen.add(tph)
            acts = phases_to_actions(ph)
            g, d = replay(sess, acts)
            lv = d.get("levels_completed")
            p(f"  {name} ph={ph} lv={lv}")
            results.append({"name": name, "ph": list(ph), "lv": lv, "actions": acts})
            if int(lv or 0) > 0:
                (ROOT / "tests/fixtures/tr87_l1_clear_frame.json").write_text(
                    json.dumps({"frame": d["frame"], "levels": lv, "name": name, "actions": acts}, indent=2),
                    encoding="utf-8",
                )
        out["dial"] = results

        # H28: maybe bottom should match TOP A icons' moments on slots, ignore mid
        # quick: set each slot to glyph minimizing feat dist to assigned topA
        from tools.tr87_l1_feat_dict import moments, feat_dist, sig_to_bits  # type: ignore

        topA = []
        for y0 in (4, 13, 22):
            for x0 in (12, 36):
                b = (g0[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6] == 10).astype(np.uint8).ravel()
                topA.append(moments(b))
        # assign topA[0..4] to slots (drop last)
        phases = []
        for si in range(5):
            best = None
            for n, sig in enumerate(cycles[si]):
                d = feat_dist(topA[si], moments(sig_to_bits(sig)))
                if best is None or d < best[0]:
                    best = (d, n)
            phases.append(best[1])
        acts = phases_to_actions(phases)
        g, d = replay(sess, acts)
        p(f"## H28 topA0..4 feats lv={d.get('levels_completed')} ph={phases}")
        out["topA_feat"] = {"ph": phases, "lv": d.get("levels_completed"), "actions": acts}

        cleared = any(int(r["lv"] or 0) > 0 for r in results) or int(out["topA_feat"]["lv"] or 0) > 0
        out["reading"] = "L1_CLEAR" if cleared else "CHECKSUM_PARTIAL"
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        p("READING:", out["reading"])
        p("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
