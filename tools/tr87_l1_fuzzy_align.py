"""tr87 L1: fuzzy match top icons into slot alphabets; try sort/unique constraints.

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

OUT = ROOT / "tests/fixtures/tr87_l1_fuzzy_align.json"
SLOTS = (15, 22, 29, 36, 43)


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


def ham(a, b):
    return int(np.sum(np.array(a) != np.array(b)))


def asc(sig):
    a = np.array(sig).reshape(5, 5)
    return ["".join(str(int(v)) for v in r) for r in a]


def collect_alphabet(sess, si):
    d = sess.reset()
    g = plane(d["frame"])
    g, _, _ = move(sess, g, si)
    start = bg(g, si)
    # map sig -> (flip, n) minimal from reset-on-slot
    best = {start: (1, 0)}
    for flip in (1, 2):
        d = sess.reset()
        g = plane(d["frame"])
        g, _, _ = move(sess, g, si)
        for n in range(1, 8):
            d = sess.action(f"ACTION{flip}")
            g = plane(d["frame"])
            sig = bg(g, si)
            if sig not in best or n < best[sig][1] or (n == best[sig][1] and flip < best[sig][0]):
                # prefer fewer steps
                prev = best.get(sig)
                if prev is None or n < prev[1]:
                    best[sig] = (flip, n)
            if sig == start and n > 0:
                break
    return best


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
                sig = tuple(int(v) for v in g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6].ravel())
                top7.append({"pos": (x0, y0), "sig": sig, "ascii": asc(sig)})

        topA = []
        for y0 in (4, 13, 22):
            for x0 in (12, 36):
                patch = np.where(g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6] == 10, 7, g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6])
                sig = tuple(int(v) for v in patch.ravel())
                topA.append({"pos": (x0, y0), "sig": sig, "ascii": asc(sig)})

        print("## building alphabets")
        alphas = [collect_alphabet(sess, si) for si in range(5)]
        for si, a in enumerate(alphas):
            print(f"  slot{si} n={len(a)}")

        print("\n## best ham top7 -> each slot alphabet")
        assign = []
        for t in top7:
            row = []
            for si, alpha in enumerate(alphas):
                best = min((ham(t["sig"], s), s, steps) for s, steps in alpha.items())
                row.append({"slot": si, "ham": best[0], "steps": best[2]})
            row.sort(key=lambda x: x["ham"])
            print(f"  top7{t['pos']}: {row[:3]}")
            assign.append({"pos": t["pos"], "best": row[0], "top3": row[:3]})
        out["top7_assign"] = assign

        print("\n## best ham topA -> each slot")
        for t in topA:
            row = []
            for si, alpha in enumerate(alphas):
                best = min((ham(t["sig"], s), steps) for s, steps in alpha.items())
                row.append({"slot": si, "ham": best[0], "steps": best[1]})
            row.sort(key=lambda x: x["ham"])
            print(f"  topA{t['pos']}: {row[:2]}")

        # Hypothesis: 5 bottom slots should be 5 DISTINCT glyphs (all different)
        print("\n## make all 5 distinct (from slot0 alpha where possible)")
        # slot1 must use its own alpha; pick glyphs to maximize uniqueness
        d = sess.reset()
        g = plane(d["frame"])
        lv0 = d.get("levels_completed")
        # naive: leave reset (check distinct count)
        bots = [bg(g, i) for i in range(5)]
        print("  reset distinct", len(set(bots)))

        # try set slots 0,2,3,4 to 4 different from alpha0; slot1 to something
        alpha0_list = list(alphas[0].keys())
        alpha1_list = list(alphas[1].keys())
        # pick first 4 of alpha0 for slots 0,2,3,4 and first of alpha1 for slot1
        targets = {
            0: alpha0_list[0],
            1: alpha1_list[0],
            2: alpha0_list[1] if len(alpha0_list) > 1 else alpha0_list[0],
            3: alpha0_list[2] if len(alpha0_list) > 2 else alpha0_list[0],
            4: alpha0_list[3] if len(alpha0_list) > 3 else alpha0_list[0],
        }
        actions = []
        for si in range(5):
            d = sess.reset()
            g = plane(d["frame"])
            for a in actions:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            g, nav, _ = move(sess, g, si)
            trial = actions + nav
            tgt = targets[si]
            flip, n = alphas[si][tgt]
            # but alphas steps are from reset+on-slot, not from current — re-find from current
            found = None
            for fl in (1, 2):
                for nn in range(0, 8):
                    d = sess.reset()
                    g = plane(d["frame"])
                    for a in trial:
                        d = sess.action(f"ACTION{a}")
                        g = plane(d["frame"])
                    for _ in range(nn):
                        d = sess.action(f"ACTION{fl}")
                        g = plane(d["frame"])
                    if bg(g, si) == tgt:
                        found = (fl, nn)
                        break
                if found:
                    break
            actions = trial
            if found and found[1]:
                actions.extend([found[0]] * found[1])
            print(f"  slot{si} -> found={found}")
        d = sess.reset()
        g = plane(d["frame"])
        for a in actions:
            d = sess.action(f"ACTION{a}")
            g = plane(d["frame"])
        bots = [bg(g, i) for i in range(5)]
        lv1 = d.get("levels_completed")
        print(f"  distinct={len(set(bots))} lv {lv0}->{lv1}")
        out["distinct5"] = {"lv0": lv0, "lv1": lv1, "n_distinct": len(set(bots)), "actions": actions}

        # Hypothesis: match mid ink-count per slot
        print("\n## match mid ink counts")
        d = sess.reset()
        g = plane(d["frame"])
        mid_inks = []
        for x0 in (14, 21, 28, 35, 42):
            p = g[41:46, x0 + 1 : x0 + 6]
            mid_inks.append(int((p == 10).sum()))
        print("  mid inks", mid_inks)
        actions = []
        lv0 = d.get("levels_completed")
        for si in range(5):
            target_ink = mid_inks[si]
            # find glyph in alphabet with ink count == target, min steps from current
            cands = [(s, st) for s, st in alphas[si].items() if int(np.sum(np.array(s).reshape(5, 5) == 7)) == target_ink]
            print(f"  slot{si} cand_n={len(cands)} for ink={target_ink}")
            if not cands:
                continue
            # pick any cand, apply
            tgt = cands[0][0]
            d = sess.reset()
            g = plane(d["frame"])
            for a in actions:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            g, nav, _ = move(sess, g, si)
            trial = actions + nav
            found = None
            for fl in (1, 2):
                for nn in range(0, 8):
                    d = sess.reset()
                    g = plane(d["frame"])
                    for a in trial:
                        d = sess.action(f"ACTION{a}")
                        g = plane(d["frame"])
                    for _ in range(nn):
                        d = sess.action(f"ACTION{fl}")
                        g = plane(d["frame"])
                    if bg(g, si) == tgt:
                        found = (fl, nn)
                        break
                if found:
                    break
            actions = trial
            if found and found[1]:
                actions.extend([found[0]] * found[1])
            print(f"    applied {found}")
        d = sess.reset()
        g = plane(d["frame"])
        for a in actions:
            d = sess.action(f"ACTION{a}")
            g = plane(d["frame"])
        lv1 = d.get("levels_completed")
        got_inks = [int(np.sum(np.array(bg(g, i)).reshape(5, 5) == 7)) for i in range(5)]
        print(f"  got_inks={got_inks} lv {lv0}->{lv1}")
        out["ink_match"] = {"mid": mid_inks, "got": got_inks, "lv0": lv0, "lv1": lv1, "actions": actions}

        # Show slot2 alphabet ascii vs top7(22,22)
        print("\n## slot2 alphabet vs unreachable top7(22,22)")
        t22 = next(t for t in top7 if t["pos"] == (22, 22))
        print("target", t22["ascii"])
        ranked = sorted(((ham(t22["sig"], s), st, asc(s)) for s, st in alphas[2].items()), key=lambda x: x[0])
        for h, st, a in ranked[:3]:
            print(f"  ham={h} steps={st}")
            for line in a:
                print("   ", line)

        out["reading"] = (
            "L1_CLEAR"
            if int(out["distinct5"]["lv1"] or 0) > int(out["distinct5"]["lv0"] or 0)
            or int(out["ink_match"]["lv1"] or 0) > int(out["ink_match"]["lv0"] or 0)
            else "FUZZY_PARTIAL"
        )
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("READING:", out["reading"])
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
