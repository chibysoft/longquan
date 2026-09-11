"""tr87 L1: which top7/topA/mid glyphs appear in each slot ACT1 cycle."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.tr87_recon_probe import Sess, plane  # noqa: E402

OUT = ROOT / "tests/fixtures/tr87_l1_cycle_catalog.json"
SLOTS = (15, 22, 29, 36, 43)


def bg(g, si):
    x0 = SLOTS[si]
    return tuple(int(v) for v in g[52:57, x0 : x0 + 5].ravel())


def move(sess, g, ti):
    for _ in range(8):
        xs = [int(x) for y, x in np.argwhere(g == 0)]
        cur = int(np.argmin([abs(min(xs) - s) for s in SLOTS])) if xs else None
        if cur == ti:
            return g, True
        df = (ti - cur) % 5
        db = (cur - ti) % 5
        a = 4 if df <= db else 3
        d = sess.action(f"ACTION{a}")
        g = plane(d["frame"])
    return g, False


def main():
    sess = Sess(_api_key())
    out = {}
    try:
        sess.open()
        d = sess.reset()
        g = plane(d["frame"])
        top7 = []
        for y0 in (4, 13, 22):
            for x0 in (22, 46):
                patch = g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6]
                top7.append({"pos": (x0, y0), "sig": tuple(int(v) for v in patch.ravel())})
        topA = []
        for y0 in (4, 13, 22):
            for x0 in (12, 36):
                patch = np.where(
                    g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6] == 10,
                    7,
                    g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6],
                )
                topA.append({"pos": (x0, y0), "sig": tuple(int(v) for v in patch.ravel())})
        mids = []
        for x0 in (14, 21, 28, 35, 42):
            patch = np.where(g[41:46, x0 + 1 : x0 + 6] == 10, 7, g[41:46, x0 + 1 : x0 + 6])
            mids.append(tuple(int(v) for v in patch.ravel()))

        print("catalog top7", len(top7), "topA", len(topA), "mid", len(mids))
        rows = []
        for si in range(5):
            d = sess.reset()
            g = plane(d["frame"])
            g, ok = move(sess, g, si)
            start = bg(g, si)
            seen = {start: 0}
            seq = [start]
            per = None
            for step in range(1, 12):
                d = sess.action("ACTION1")
                g = plane(d["frame"])
                sig = bg(g, si)
                if sig in seen:
                    per = step - seen[sig]
                    break
                seen[sig] = step
                seq.append(sig)
            setc = set(seq)
            h7 = [t["pos"] for t in top7 if t["sig"] in setc]
            hA = [t["pos"] for t in topA if t["sig"] in setc]
            hm = [i for i, s in enumerate(mids) if s in setc]
            # cross: reset bottoms in this cycle?
            d = sess.reset()
            g = plane(d["frame"])
            bots = [bg(g, i) for i in range(5)]
            hb = [i for i, s in enumerate(bots) if s in setc]
            print(f"slot{si} ok={ok} per={per} n={len(setc)} top7={h7} topA={hA} mid={hm} bots={hb}")
            rows.append(
                {
                    "slot": si,
                    "period": per,
                    "n": len(setc),
                    "top7": h7,
                    "topA": hA,
                    "mid": hm,
                    "bots_in_cycle": hb,
                }
            )
        out["rows"] = rows
        # Are all 5 slot cycles the SAME set of 7 glyphs?
        # Collect full sets
        sets = []
        for si in range(5):
            d = sess.reset()
            g = plane(d["frame"])
            g, _ = move(sess, g, si)
            start = bg(g, si)
            seen = {start}
            for _ in range(10):
                d = sess.action("ACTION1")
                g = plane(d["frame"])
                sig = bg(g, si)
                if sig in seen and sig == start and len(seen) > 1:
                    break
                seen.add(sig)
            sets.append(frozenset(seen))
        same = all(s == sets[0] for s in sets)
        print("all slots same glyph alphabet?", same)
        if not same:
            for i in range(5):
                for j in range(i + 1, 5):
                    inter = len(sets[i] & sets[j])
                    print(f"  |S{i}∩S{j}|={inter} |S{i}|={len(sets[i])} |S{j}|={len(sets[j])}")
        out["same_alphabet"] = same
        out["alphabet_sizes"] = [len(s) for s in sets]

        # Shared alphabet union vs top7 coverage
        union = set().union(*sets)
        print("union size", len(union))
        print("top7 covered", sum(1 for t in top7 if t["sig"] in union), "/", len(top7))
        print("topA covered", sum(1 for t in topA if t["sig"] in union), "/", len(topA))
        print("mid covered", sum(1 for s in mids if s in union), "/", len(mids))
        out["union_n"] = len(union)
        out["top7_covered"] = sum(1 for t in top7 if t["sig"] in union)
        out["topA_covered"] = sum(1 for t in topA if t["sig"] in union)
        out["mid_covered"] = sum(1 for s in mids if s in union)

        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
