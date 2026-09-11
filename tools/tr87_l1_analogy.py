"""tr87 L1: analogy map — mid≈topA => target=paired top7; dial and test levels.

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

OUT = ROOT / "tests/fixtures/tr87_l1_analogy.json"
SLOTS = (15, 22, 29, 36, 43)
PAIRS = [  # (A_x0, seven_x0, y0)
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


def ham(a, b):
    return int(np.sum(np.array(a) != np.array(b)))


def asc(sig):
    a = np.array(sig).reshape(5, 5)
    return ["".join(str(int(v)) for v in r) for r in a]


def main():
    sess = Sess(_api_key())
    out = {}
    try:
        sess.open()
        d = sess.reset()
        g = plane(d["frame"])

        mids = []
        for x0 in (14, 21, 28, 35, 42):
            p = np.where(g[41:46, x0 + 1 : x0 + 6] == 10, 7, g[41:46, x0 + 1 : x0 + 6])
            mids.append(tuple(int(v) for v in p.ravel()))

        pairs = []
        for ax, sx, y0 in PAIRS:
            A = np.where(g[y0 + 1 : y0 + 6, ax + 1 : ax + 6] == 10, 7, g[y0 + 1 : y0 + 6, ax + 1 : ax + 6])
            S = g[y0 + 1 : y0 + 6, sx + 1 : sx + 6]
            pairs.append(
                {
                    "A": tuple(int(v) for v in A.ravel()),
                    "S": tuple(int(v) for v in S.ravel()),
                    "posA": (ax, y0),
                    "posS": (sx, y0),
                }
            )

        # For each mid, nearest A -> paired S
        targets = []
        for mi, m in enumerate(mids):
            best = min(((ham(m, p["A"]), pi, p) for pi, p in enumerate(pairs)), key=lambda x: x[0])
            print(f"M{mi} nearest A{best[2]['posA']} ham={best[0]} -> S{best[2]['posS']}")
            print("  target S:")
            for line in asc(best[2]["S"]):
                print("   ", line)
            targets.append(best[2]["S"])
        out["targets_ascii"] = [asc(t) for t in targets]
        out["assign"] = [
            {
                "mid": i,
                "hamA": ham(mids[i], pairs[min(range(6), key=lambda pi: ham(mids[i], pairs[pi]["A"]))]["A"]),
            }
            for i in range(5)
        ]

        # Can each slot reach its target?
        reach = []
        for si, tgt in enumerate(targets):
            d = sess.reset()
            g = plane(d["frame"])
            g, _, _ = move(sess, g, si)
            found = None
            start = bg(g, si)
            for fl in (1, 2):
                d = sess.reset()
                g = plane(d["frame"])
                g, _, _ = move(sess, g, si)
                sig = bg(g, si)
                for n in range(0, 8):
                    if n:
                        d = sess.action(f"ACTION{fl}")
                        g = plane(d["frame"])
                        sig = bg(g, si)
                    if sig == tgt:
                        found = {"flip": fl, "n": n}
                        break
                    if n and sig == start:
                        break
                if found:
                    break
            # best ham if not exact
            d = sess.reset()
            g = plane(d["frame"])
            g, _, _ = move(sess, g, si)
            best_h = 25
            best_n = None
            sig = bg(g, si)
            for n in range(0, 8):
                if n:
                    d = sess.action("ACTION1")
                    g = plane(d["frame"])
                    sig = bg(g, si)
                h = ham(sig, tgt)
                if h < best_h:
                    best_h, best_n = h, n
                if n and sig == start and n > 0:
                    break
            print(f"  slot{si} exact={found} best_ham={best_h}@{best_n}")
            reach.append({"exact": found, "best_ham": best_h, "best_n": best_n})
        out["reach"] = reach

        # Execute exact where possible; fuzzy best_ham elsewhere
        d = sess.reset()
        g = plane(d["frame"])
        lv0 = d.get("levels_completed")
        actions = []
        for si in range(5):
            d = sess.reset()
            g = plane(d["frame"])
            for a in actions:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            g, nav, _ = move(sess, g, si)
            trial = actions + nav
            plan = reach[si]["exact"]
            if plan:
                fl, n = plan["flip"], plan["n"]
            else:
                fl, n = 1, reach[si]["best_n"] or 0
            for _ in range(n):
                trial.append(fl)
            # verify
            d = sess.reset()
            g = plane(d["frame"])
            for a in trial:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            print(f"  applied slot{si} ham_now={ham(bg(g, si), targets[si])}")
            actions = trial
        d = sess.reset()
        g = plane(d["frame"])
        for a in actions:
            d = sess.action(f"ACTION{a}")
            g = plane(d["frame"])
        lv1 = d.get("levels_completed")
        print(f"analogy exec lv {lv0}->{lv1} nact={len(actions)}")
        out["combined"] = {
            "lv0": lv0,
            "lv1": lv1,
            "actions": actions,
            "final_ham": [ham(bg(g, i), targets[i]) for i in range(5)],
        }
        if int(lv1 or 0) > int(lv0 or 0):
            (ROOT / "tests/fixtures/tr87_l1_clear_frame.json").write_text(
                json.dumps({"frame": d["frame"], "levels": lv1, "actions": actions}, indent=2),
                encoding="utf-8",
            )
        out["reading"] = "L1_CLEAR" if int(lv1 or 0) > int(lv0 or 0) else "ANALOGY_PARTIAL"
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("READING:", out["reading"])
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
