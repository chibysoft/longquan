"""tr87 L1: sample phase tuples near mid-ham minima; also random; watch levels.

tags=["tr87_recon"]
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.tr87_recon_probe import Sess, plane  # noqa: E402

OUT = ROOT / "tests/fixtures/tr87_l1_phase_sample.json"
SLOTS = (15, 22, 29, 36, 43)


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


def ham(a, b):
    return int(np.sum(np.array(a) != np.array(b)))


def replay(sess, actions):
    d = sess.reset()
    g = plane(d["frame"])
    for a in actions:
        g, d = go(sess, g, a)
    return g, d


def phases_to_actions(phases):
    actions = []
    cur = 0
    for si, ph in enumerate(phases):
        df = (si - cur) % 5
        db = (cur - si) % 5
        actions.extend([4] * df if df <= db else [3] * db)
        cur = si
        actions.extend([1] * ph)
    return actions


def main():
    random.seed(87)
    g0 = np.asarray(
        json.loads((ROOT / "tests/fixtures/tr87_l1_frame_live.json").read_text(encoding="utf-8"))["frame"]
    )
    if g0.ndim == 3:
        g0 = g0[0]
    mids = []
    for x0 in (15, 22, 29, 36, 43):
        p5 = np.where(g0[41:46, x0 : x0 + 5] == 10, 7, g0[41:46, x0 : x0 + 5])
        mids.append(tuple(int(v) for v in p5.ravel()))

    sess = Sess(_api_key())
    out = {"tried": []}
    try:
        sess.open()
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

        # enumerate ALL 7^5 is 16807 — too many API calls.
        # Offline score all, take top-30 lowest mid-ham, plus 20 random, test online.
        scored = []
        for phases in np.ndindex(7, 7, 7, 7, 7):
            bots = [cycles[si][phases[si]] for si in range(5)]
            sc = sum(ham(bots[i], mids[i]) for i in range(5))
            scored.append((sc, phases))
        scored.sort()
        p(f"offline min mid-ham={scored[0][0]} at {scored[0][1]}")
        p(f"offline max={scored[-1][0]}")
        out["offline_min"] = {"ham": scored[0][0], "phases": list(scored[0][1])}
        out["offline_p50"] = scored[len(scored) // 2][0]

        candidates = []
        for sc, ph in scored[:40]:
            candidates.append(("min", sc, ph))
        # also unique top7-cover maximizers
        top7 = []
        for y0 in (4, 13, 22):
            for x0 in (22, 46):
                top7.append(tuple(int(v) for v in g0[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6].ravel()))
        cover_scored = []
        for phases in np.ndindex(7, 7, 7, 7, 7):
            bots = [cycles[si][phases[si]] for si in range(5)]
            cover = sum(1 for t in top7 if t in bots)
            cover_scored.append((-cover, sum(ham(bots[i], mids[i]) for i in range(5)), phases))
        cover_scored.sort()
        p(f"max top7 cover={-cover_scored[0][0]} midham={cover_scored[0][1]} at {cover_scored[0][2]}")
        for item in cover_scored[:10]:
            candidates.append(("cover", -item[0], item[2]))

        # random 15
        for _ in range(15):
            ph = tuple(random.randrange(7) for _ in range(5))
            bots = [cycles[si][ph[si]] for si in range(5)]
            sc = sum(ham(bots[i], mids[i]) for i in range(5))
            candidates.append(("rnd", sc, ph))

        # dedupe phases
        seen = set()
        uniq = []
        for kind, sc, ph in candidates:
            if ph in seen:
                continue
            seen.add(ph)
            uniq.append((kind, sc, ph))
        p(f"test online n={len(uniq)}")

        cleared = False
        for i, (kind, sc, ph) in enumerate(uniq):
            acts = phases_to_actions(ph)
            g, d = replay(sess, acts)
            lv = d.get("levels_completed")
            if i < 5 or i % 10 == 0 or int(lv or 0) > 0:
                p(f"  [{i}] {kind} sc={sc} ph={ph} lv={lv}")
            out["tried"].append({"kind": kind, "sc": sc, "ph": list(ph), "lv": lv})
            if int(lv or 0) > 0:
                cleared = True
                out["clear"] = {"kind": kind, "ph": list(ph), "actions": acts}
                (ROOT / "tests/fixtures/tr87_l1_clear_frame.json").write_text(
                    json.dumps({"frame": d["frame"], "levels": lv, "ph": list(ph), "actions": acts}, indent=2),
                    encoding="utf-8",
                )
                p("*** CLEAR")
                break

        out["reading"] = "L1_CLEAR" if cleared else "SAMPLE_EMPTY"
        out["n_tried"] = len(out["tried"])
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        p("READING:", out["reading"], "tried", out["n_tried"])
        p("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
