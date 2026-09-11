"""tr87 L1: min Hamming from each slot cycle to mid/topA; try phase sync.

Also probe: match bottom[i] to topA left-col remapped via closest cycle state
even if not exact — no that's wrong.

New angle: mid band may be ONE glyph row whose cells use 7-wide including
separators; try matching full 35-wide strip binary.

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

OUT = ROOT / "tests/fixtures/tr87_l1_phase_sync.json"
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
    return g, acts, sel(g) == ti


def cycle(sess, g, si, flip=1):
    start = bg(g, si)
    seq = [start]
    seen = {start: 0}
    for step in range(1, 12):
        d = sess.action(f"ACTION{flip}")
        g = plane(d["frame"])
        sig = bg(g, si)
        if sig in seen:
            return g, seq, step - seen[sig]
        seen[sig] = step
        seq.append(sig)
    return g, seq, None


def ham(a, b):
    return int(np.sum(np.array(a) != np.array(b)))


def main():
    sess = Sess(_api_key())
    out = {}
    try:
        sess.open()
        d = sess.reset()
        g = plane(d["frame"])

        # mid targets 10→7
        mids = []
        for x0 in (14, 21, 28, 35, 42):
            patch = np.where(g[41:46, x0 + 1 : x0 + 6] == 10, 7, g[41:46, x0 + 1 : x0 + 6])
            mids.append(tuple(int(v) for v in patch.ravel()))

        # topA left column 10→7
        topA_left = []
        for y0 in (4, 13, 22):
            patch = np.where(g[y0 + 1 : y0 + 6, 13:18] == 10, 7, g[y0 + 1 : y0 + 6, 13:18])
            topA_left.append(tuple(int(v) for v in patch.ravel()))

        # Per slot min ham to own mid and to each topA
        rows = []
        for si in range(5):
            d = sess.reset()
            g = plane(d["frame"])
            g, _, _ = move(sess, g, si)
            _, seq, per = cycle(sess, g, si, 1)
            best_mid = min((ham(s, mids[si]), k) for k, s in enumerate(seq))
            best_As = [min((ham(s, t), k) for k, s in enumerate(seq)) for t in topA_left]
            # best to ANY mid
            best_any_mid = min(
                (ham(s, mids[mi]), k, mi) for mi in range(5) for k, s in enumerate(seq)
            )
            print(
                f"slot{si} per={per} best_own_mid={best_mid} best_any_mid={best_any_mid} "
                f"bestA={best_As}"
            )
            rows.append(
                {
                    "slot": si,
                    "best_own_mid": best_mid,
                    "best_any_mid": best_any_mid,
                    "bestA": best_As,
                }
            )
        out["ham_rows"] = rows

        # ---- NEW: is mid strip equal to concatenation of topA somehow? ----
        d = sess.reset()
        g = plane(d["frame"])
        mid_strip = g[41:46, 15:48]  # 5x33?
        print("mid strip shape", mid_strip.shape, "unique", np.unique(mid_strip))

        # Compare mid 5 cells to 5 of 6 top icons (A or 7)
        # Build list of all 12 icon interiors remapped to 5/7
        icons = []
        for y0 in (4, 13, 22):
            for x0, kind in ((12, "A"), (22, "7"), (36, "A"), (46, "7")):
                patch = g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6].copy()
                if kind == "A":
                    patch = np.where(patch == 10, 7, patch)
                icons.append({"y0": y0, "x0": x0, "kind": kind, "sig": tuple(int(v) for v in patch.ravel())})

        print("\n## mid cell vs all icons ham")
        for mi, m in enumerate(mids):
            scores = sorted((ham(m, ic["sig"]), ic["kind"], ic["x0"], ic["y0"]) for ic in icons)
            print(f"  M{mi} best3={scores[:3]}")

        # ---- Phase sync: set slot0,1 to their unique top7, then try ALL
        # combinations of steps on remaining slots (3^3 or 7^3 too big).
        # Instead: greedy minimize total ham to mid across slots.
        print("\n## greedy minimize sum ham to mid")
        d = sess.reset()
        g = plane(d["frame"])
        lv0 = d.get("levels_completed")
        actions = []
        for si in range(5):
            d = sess.reset() if si == 0 else None
            if si == 0:
                d = sess.reset()
                g = plane(d["frame"])
                actions = []
                lv0 = d.get("levels_completed")
            # from current g — actually need rebuild: do all in one pass
        # proper one-pass greedy from reset:
        d = sess.reset()
        g = plane(d["frame"])
        lv0 = d.get("levels_completed")
        actions = []
        for si in range(5):
            # explore cycle from current without losing other slots:
            # save by computing offline from slot_maps built via reset+nav each time
            d = sess.reset()
            g = plane(d["frame"])
            # replay actions so far
            for a in actions:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            g, nav, _ = move(sess, g, si)
            actions.extend(nav)
            # try 0..6 ACT1 from here, pick min ham to mids[si]
            # need fork — use reset+replay
            best = (99, 0, None)  # ham, n1, use_act2?
            base_actions = list(actions)
            for n in range(0, 7):
                d = sess.reset()
                g = plane(d["frame"])
                for a in base_actions:
                    d = sess.action(f"ACTION{a}")
                    g = plane(d["frame"])
                for _ in range(n):
                    d = sess.action("ACTION1")
                    g = plane(d["frame"])
                h = ham(bg(g, si), mids[si])
                if h < best[0]:
                    best = (h, n, 1)
            for n in range(1, 7):
                d = sess.reset()
                g = plane(d["frame"])
                for a in base_actions:
                    d = sess.action(f"ACTION{a}")
                    g = plane(d["frame"])
                for _ in range(n):
                    d = sess.action("ACTION2")
                    g = plane(d["frame"])
                h = ham(bg(g, si), mids[si])
                if h < best[0]:
                    best = (h, n, 2)
            # apply best
            d = sess.reset()
            g = plane(d["frame"])
            for a in base_actions:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            flip = best[2] if best[2] else 1
            for _ in range(best[1] if best[2] else 0):
                d = sess.action(f"ACTION{flip}")
                g = plane(d["frame"])
                actions.append(flip)
            print(f"  slot{si} best_ham={best[0]} n={best[1]} act={best[2]} now={ham(bg(g,si),mids[si])}")
            # fix actions list: base_actions already had nav; we need actions=current
            # rebuild actions properly
            actions = list(base_actions)
            if best[2] and best[1]:
                actions.extend([best[2]] * best[1])

        d = sess.reset()
        g = plane(d["frame"])
        for a in actions:
            d = sess.action(f"ACTION{a}")
            g = plane(d["frame"])
        lv1 = d.get("levels_completed")
        total_ham = sum(ham(bg(g, i), mids[i]) for i in range(5))
        print(f"greedy done lv {lv0}->{lv1} total_ham={total_ham} nact={len(actions)}")
        out["greedy_mid"] = {
            "lv0": lv0,
            "lv1": lv1,
            "total_ham": total_ham,
            "actions": actions,
            "per_ham": [ham(bg(g, i), mids[i]) for i in range(5)],
        }

        # ---- Last idea: copy left-col top7 into slots 0 and 1 (reachable),
        # and for slots 2,3,4 set to top7(22,4) which they can reach — all left-col-ish
        print("\n## slot0<-(22,4) slot1<-(22,13) slot234<-(22,4)")
        d = sess.reset()
        g = plane(d["frame"])
        t04 = tuple(int(v) for v in g[5:10, 23:28].ravel())
        t13 = tuple(int(v) for v in g[14:19, 23:28].ravel())
        lv0 = d.get("levels_completed")
        actions = []
        targets = {0: t04, 1: t13, 2: t04, 3: t04, 4: t04}
        for si in range(5):
            # find steps via reset probe
            d = sess.reset()
            g = plane(d["frame"])
            for a in actions:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            g, nav, _ = move(sess, g, si)
            trial = list(actions) + nav
            tgt = targets[si]
            found = None
            for flip in (1, 2):
                for n in range(0, 8):
                    d = sess.reset()
                    g = plane(d["frame"])
                    for a in trial:
                        d = sess.action(f"ACTION{a}")
                        g = plane(d["frame"])
                    for _ in range(n):
                        d = sess.action(f"ACTION{flip}")
                        g = plane(d["frame"])
                    if bg(g, si) == tgt:
                        found = (flip, n)
                        break
                if found:
                    break
            print(f"  slot{si} found={found}")
            actions = trial
            if found and found[1]:
                actions.extend([found[0]] * found[1])
            elif found is None:
                print("  FAILED")
        d = sess.reset()
        g = plane(d["frame"])
        for a in actions:
            d = sess.action(f"ACTION{a}")
            g = plane(d["frame"])
        lv1 = d.get("levels_completed")
        print(f"  lv {lv0}->{lv1}")
        out["left_col_fill"] = {"lv0": lv0, "lv1": lv1, "actions": actions}

        out["reading"] = (
            "L1_CLEAR"
            if int(out["greedy_mid"]["lv1"] or 0) > int(out["greedy_mid"]["lv0"] or 0)
            or int(lv1 or 0) > int(lv0 or 0)
            else "PHASE_PARTIAL"
        )
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("READING:", out["reading"])
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
