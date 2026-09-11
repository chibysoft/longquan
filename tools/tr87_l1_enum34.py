"""tr87 L1: fix slot0/1 to left-col top7; enumerate slot3×slot4 (and slot2 phases).

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

OUT = ROOT / "tests/fixtures/tr87_l1_enum34.json"
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


def apply(sess, actions):
    d = sess.reset()
    g = plane(d["frame"])
    lv0 = d.get("levels_completed")
    for a in actions:
        d = sess.action(f"ACTION{a}")
        g = plane(d["frame"])
    return g, d, lv0, d.get("levels_completed")


def steps_to(sess, si, tgt, prefix):
    """Find (flip,n) to reach tgt on si after prefix actions from reset."""
    for fl in (1, 2):
        for n in range(0, 8):
            d = sess.reset()
            g = plane(d["frame"])
            for a in prefix:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            g, nav, ok = move(sess, g, si)
            if not ok:
                continue
            for _ in range(n):
                d = sess.action(f"ACTION{fl}")
                g = plane(d["frame"])
            if bg(g, si) == tgt:
                return nav + ([fl] * n if n else [])
    return None


def main():
    sess = Sess(_api_key())
    out = {"hits": []}
    try:
        sess.open()
        d = sess.reset()
        g = plane(d["frame"])
        t04 = tuple(int(v) for v in g[5:10, 23:28].ravel())
        t13 = tuple(int(v) for v in g[14:19, 23:28].ravel())
        t22 = tuple(int(v) for v in g[23:28, 23:28].ravel())

        # alphabet of slot0 via ACT1
        d = sess.reset()
        g = plane(d["frame"])
        start = bg(g, 0)
        alpha = [start]
        for _ in range(6):
            d = sess.action("ACTION1")
            g = plane(d["frame"])
            sig = bg(g, 0)
            if sig == start:
                break
            alpha.append(sig)
        print("alpha0", len(alpha))

        # slot2 alphabet
        d = sess.reset()
        g = plane(d["frame"])
        g, _, _ = move(sess, g, 2)
        start2 = bg(g, 2)
        alpha2 = [start2]
        for _ in range(6):
            d = sess.action("ACTION1")
            g = plane(d["frame"])
            sig = bg(g, 2)
            if sig == start2:
                break
            alpha2.append(sig)
        print("alpha2", len(alpha2))

        # Base: set slot0=t04, slot1=t13
        base = []
        # slot0
        path = steps_to(sess, 0, t04, base)
        print("path0", path)
        assert path is not None
        base += path
        path = steps_to(sess, 1, t13, base)
        print("path1", path)
        assert path is not None
        base += path

        g, d, lv0, lv1 = apply(sess, base)
        print("base only lv", lv0, lv1, "match01", bg(g, 0) == t04, bg(g, 1) == t13)

        # Enumerate slot2 phase (7) x slot3 (7) x slot4 (7) = 343 — bit heavy.
        # First: slot2 best for t22 (ham2 at n=0) fixed; enum 3x4 = 49.
        print("\n## enum slot3 x slot4 with slot2 fixed at reset-best")
        best_s2 = min(alpha2, key=lambda s: int(np.sum(np.array(s) != np.array(t22))))
        print("best_s2 ham", int(np.sum(np.array(best_s2) != np.array(t22))))
        path2 = steps_to(sess, 2, best_s2, base)
        base2 = base + (path2 or [])
        print("path2", path2)

        n_try = 0
        cleared = False
        for i3, tgt3 in enumerate(alpha):
            for i4, tgt4 in enumerate(alpha):
                n_try += 1
                path3 = steps_to(sess, 3, tgt3, base2)
                if path3 is None:
                    continue
                pref = base2 + path3
                path4 = steps_to(sess, 4, tgt4, pref)
                if path4 is None:
                    continue
                actions = pref + path4
                g, d, lv0, lv1 = apply(sess, actions)
                if int(lv1 or 0) > int(lv0 or 0):
                    print("*** CLEAR", i3, i4, "lv", lv0, lv1, "nact", len(actions))
                    out["hits"].append({"i3": i3, "i4": i4, "actions": actions, "lv1": lv1})
                    (ROOT / "tests/fixtures/tr87_l1_clear_frame.json").write_text(
                        json.dumps({"frame": d["frame"], "levels": lv1, "actions": actions}, indent=2),
                        encoding="utf-8",
                    )
                    cleared = True
                    break
                if n_try % 10 == 0:
                    print(f"  tried {n_try} lv still {lv1}")
            if cleared:
                break

        # Also try: all five slots show the SAME top7(22,4) where possible; slot1 can't
        # Skip if cleared

        # Second wave: don't fix slot0/1; instead set each slot to min-ham vs mid
        # already done.

        # Third: enum only aligning to left column + mid M3,M4 best from alpha
        d = sess.reset()
        g = plane(d["frame"])
        mids = []
        for x0 in (14, 21, 28, 35, 42):
            p = np.where(g[41:46, x0 + 1 : x0 + 6] == 10, 7, g[41:46, x0 + 1 : x0 + 6])
            mids.append(tuple(int(v) for v in p.ravel()))
        best3 = min(alpha, key=lambda s: int(np.sum(np.array(s) != np.array(mids[3]))))
        best4 = min(alpha, key=lambda s: int(np.sum(np.array(s) != np.array(mids[4]))))
        print(
            "mid best ham3",
            int(np.sum(np.array(best3) != np.array(mids[3]))),
            "ham4",
            int(np.sum(np.array(best4) != np.array(mids[4]))),
        )
        if not cleared:
            pref = base2
            path3 = steps_to(sess, 3, best3, pref)
            pref = pref + (path3 or [])
            path4 = steps_to(sess, 4, best4, pref)
            actions = pref + (path4 or [])
            g, d, lv0, lv1 = apply(sess, actions)
            print("mid-best 3/4 lv", lv0, lv1)
            out["mid_best34"] = {"lv0": lv0, "lv1": lv1, "actions": actions}

        out["n_try"] = n_try
        out["cleared"] = cleared
        out["reading"] = "L1_CLEAR" if cleared else "ENUM34_EMPTY"
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("READING:", out["reading"], "tried", n_try)
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
