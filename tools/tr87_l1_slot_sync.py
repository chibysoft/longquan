"""tr87 L1: lean phase-sync + assign5 + stagger (unbuffered).

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

OUT = ROOT / "tests/fixtures/tr87_l1_slot_sync.json"
SLOTS = (15, 22, 29, 36, 43)


def p(*a, **k):
    print(*a, **k, flush=True)


def bg(g, si):
    x0 = SLOTS[si]
    return tuple(int(v) for v in g[52:57, x0 : x0 + 5].ravel())


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


def set_slot_phase(sess, prefix, si, n_act1):
    g, d = replay(sess, prefix)
    g, nav = move(sess, g, si)
    acts = list(prefix) + nav + [1] * n_act1
    g, d = replay(sess, acts)
    return acts, g, d


def main():
    sess = Sess(_api_key())
    out = {}
    try:
        sess.open()
        d = sess.reset()
        g = plane(d["frame"])
        left = [tuple(int(v) for v in g[y0 + 1 : y0 + 6, 23:28].ravel()) for y0 in (4, 13, 22)]
        right = [tuple(int(v) for v in g[y0 + 1 : y0 + 6, 47:52].ravel()) for y0 in (4, 13, 22)]
        assign5 = [left[0], left[1], left[2], right[0], right[1]]
        top7 = left + right
        p("targets loaded", len(top7))

        # cycle lengths / phases to hit assign5 best
        p("## per-slot best phase vs assign5")
        best_phase = []
        for si in range(5):
            g, d = replay(sess, [])
            g, _ = move(sess, g, si)
            best = (99, 0, bg(g, si))
            start = bg(g, si)
            sig = start
            for n in range(0, 7):
                if n:
                    g, d = go(sess, g, 1)
                    sig = bg(g, si)
                h = ham(sig, assign5[si])
                if h < best[0]:
                    best = (h, n, sig)
            best_phase.append(best)
            p(f"  slot{si} ham={best[0]} n={best[1]}")

        # execute best phases
        actions = []
        for si in range(5):
            actions, g, d = set_slot_phase(sess, actions, si, best_phase[si][1])
            p(f"  set{si} ham_now={ham(bg(g,si), assign5[si])}")
        lv0, lv1 = 0, d.get("levels_completed")
        # re-get lv0
        g0, d0 = replay(sess, [])
        lv0 = d0.get("levels_completed")
        g, d = replay(sess, actions)
        lv1 = d.get("levels_completed")
        per = [ham(bg(g, i), assign5[i]) for i in range(5)]
        p(f"assign5 lv {lv0}->{lv1} per_ham={per}")
        out["assign5"] = {"lv0": lv0, "lv1": lv1, "per_ham": per, "actions": actions}

        # global sync k
        p("## sync k")
        sync = []
        for k in range(7):
            actions = []
            for si in range(5):
                actions, g, d = set_slot_phase(sess, actions, si, k)
            g, d = replay(sess, actions)
            lv1 = d.get("levels_completed")
            p(f"  k={k} lv={lv1}")
            sync.append({"k": k, "lv1": lv1, "nact": len(actions)})
            if int(lv1 or 0) > 0:
                out["clear"] = {"kind": "sync", "k": k, "actions": actions}
                break
        out["sync"] = sync

        # stagger
        p("## stagger")
        stag = []
        for off in (1, 2, 3, 4):
            actions = []
            for si in range(5):
                actions, g, d = set_slot_phase(sess, actions, si, (si * off) % 7)
            g, d = replay(sess, actions)
            lv1 = d.get("levels_completed")
            p(f"  off={off} lv={lv1}")
            stag.append({"off": off, "lv1": lv1})
            if int(lv1 or 0) > 0:
                out["clear"] = {"kind": "stag", "off": off, "actions": actions}
                break
        out["stag"] = stag

        # opposite: slot i phase (6-i) or reverse order visit with flips
        p("## reverse stagger")
        actions = []
        for si in range(5):
            actions, g, d = set_slot_phase(sess, actions, si, (4 - si) % 7)
        g, d = replay(sess, actions)
        p(f"  rev lv={d.get('levels_completed')}")
        out["rev"] = {"lv1": d.get("levels_completed"), "actions": actions}

        # Match only left3 on slots 0,1,2 exactly where possible; leave 3,4 at reset
        p("## left3 exact-ish on 0,1,2")
        actions = []
        for si in range(3):
            # find n for exact or best
            g, d = replay(sess, actions)
            g, nav = move(sess, g, si)
            prefix = actions + nav
            best = (99, 0)
            g, d = replay(sess, prefix)
            start = bg(g, si)
            sig = start
            for n in range(0, 7):
                if n:
                    g, d = go(sess, g, 1)
                    sig = bg(g, si)
                h = ham(sig, left[si])
                if h < best[0]:
                    best = (h, n)
                if h == 0:
                    break
            actions = prefix + [1] * best[1]
            p(f"  slot{si} ham={best[0]} n={best[1]}")
        g, d = replay(sess, actions)
        p(f"  left3 lv={d.get('levels_completed')} hams={[ham(bg(g,i), left[i]) for i in range(3)]}")
        out["left3"] = {"lv1": d.get("levels_completed"), "actions": actions}

        cleared = int(out["assign5"]["lv1"] or 0) > 0 or any(
            int(x.get("lv1") or 0) > 0 for x in sync + stag
        ) or int(out["rev"]["lv1"] or 0) > 0 or int(out["left3"]["lv1"] or 0) > 0
        out["reading"] = "L1_CLEAR" if cleared else "SYNC_EMPTY"
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        p("READING:", out["reading"])
        p("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
