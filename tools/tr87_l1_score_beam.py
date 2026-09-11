"""tr87 L1: score bottoms by sum-min-ham to top7 set; beam/greedy phases; slot-sync.

Also try: make bottom equal to left-col top7 on slots 0,1,2 (fuzzy) + right-col on 3,4 (fuzzy).

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

OUT = ROOT / "tests/fixtures/tr87_l1_score_beam.json"
SLOTS = (15, 22, 29, 36, 43)


def bg(g, si):
    x0 = SLOTS[si]
    return tuple(int(v) for v in g[52:57, x0 : x0 + 5].ravel())


def all_b(g):
    return [bg(g, i) for i in range(5)]


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


def go(sess, g, a):
    d = sess.action(f"ACTION{a}")
    return plane(d["frame"]), d


def collect_alpha(sess, si):
    d = sess.reset()
    g = plane(d["frame"])
    g, _, _ = move(sess, g, si)
    start = bg(g, si)
    seen = {start: (1, 0)}
    for fl in (1, 2):
        d = sess.reset()
        g = plane(d["frame"])
        g, _, _ = move(sess, g, si)
        for n in range(1, 8):
            d = sess.action(f"ACTION{fl}")
            g = plane(d["frame"])
            sig = bg(g, si)
            if sig not in seen or n < seen[sig][1]:
                seen[sig] = (fl, n)
            if sig == start:
                break
    return seen


def score_top7(bots, top7):
    return sum(min(ham(b, t) for t in top7) for b in bots)


def score_assigned(bots, targets):
    return sum(ham(bots[i], targets[i]) for i in range(5))


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
                top7.append(tuple(int(v) for v in g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6].ravel()))
        left = [
            tuple(int(v) for v in g[y0 + 1 : y0 + 6, 23:28].ravel()) for y0 in (4, 13, 22)
        ]
        right = [
            tuple(int(v) for v in g[y0 + 1 : y0 + 6, 47:52].ravel()) for y0 in (4, 13, 22)
        ]
        # 5 targets: left0,left1,left2,right0,right1
        assign5 = [left[0], left[1], left[2], right[0], right[1]]
        print("reset score_top7", score_top7(all_b(g), top7))
        print("reset score_assign5", score_assigned(all_b(g), assign5))

        alphas = [collect_alpha(sess, si) for si in range(5)]

        # Per slot: glyph in alpha minimizing ham to assign5[si]
        print("\n## dial assign5 (L0,L1,L2,R0,R1)")
        targets = []
        for si in range(5):
            best = min(
                ((ham(sig, assign5[si]), sig, st) for sig, st in alphas[si].items()),
                key=lambda x: (x[0], x[2][1]),
            )
            print(f"  slot{si} ham={best[0]} steps={best[2]}")
            targets.append(best[1])

        actions = []
        lv0 = None
        for si in range(5):
            d = sess.reset()
            g = plane(d["frame"])
            if lv0 is None:
                lv0 = d.get("levels_completed")
            for a in actions:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            g, nav, _ = move(sess, g, si)
            trial = actions + nav
            tgt = targets[si]
            found = None
            for fl in (1, 2):
                for n in range(0, 8):
                    d = sess.reset()
                    g = plane(d["frame"])
                    for a in trial:
                        d = sess.action(f"ACTION{a}")
                        g = plane(d["frame"])
                    for _ in range(n):
                        d = sess.action(f"ACTION{fl}")
                        g = plane(d["frame"])
                    if bg(g, si) == tgt:
                        found = (fl, n)
                        break
                if found:
                    break
            if found and found[1]:
                trial = trial + [found[0]] * found[1]
            actions = trial
            print(f"  applied {si} {found}")
        d = sess.reset()
        g = plane(d["frame"])
        for a in actions:
            d = sess.action(f"ACTION{a}")
            g = plane(d["frame"])
        lv1 = d.get("levels_completed")
        bots = all_b(g)
        print(
            f"  lv {lv0}->{lv1} score_a={score_assigned(bots, assign5)} score7={score_top7(bots, top7)}"
        )
        out["assign5"] = {
            "lv0": lv0,
            "lv1": lv1,
            "score_a": score_assigned(bots, assign5),
            "score7": score_top7(bots, top7),
            "per_ham": [ham(bots[i], assign5[i]) for i in range(5)],
            "actions": actions,
        }

        # Minimize sum min-ham to top7 set (greedy per slot independently)
        print("\n## dial min-ham to any top7")
        actions = []
        for si in range(5):
            best = min(
                (
                    (min(ham(sig, t) for t in top7), sig)
                    for sig in alphas[si]
                ),
                key=lambda x: x[0],
            )
            tgt = best[1]
            print(f"  slot{si} best_minham={best[0]}")
            d = sess.reset()
            g = plane(d["frame"])
            for a in actions:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            g, nav, _ = move(sess, g, si)
            trial = actions + nav
            found = None
            for fl in (1, 2):
                for n in range(0, 8):
                    d = sess.reset()
                    g = plane(d["frame"])
                    for a in trial:
                        d = sess.action(f"ACTION{a}")
                        g = plane(d["frame"])
                    for _ in range(n):
                        d = sess.action(f"ACTION{fl}")
                        g = plane(d["frame"])
                    if bg(g, si) == tgt:
                        found = (fl, n)
                        break
                if found:
                    break
            if found and found[1]:
                trial = trial + [found[0]] * found[1]
            actions = trial
        d = sess.reset()
        g = plane(d["frame"])
        lv0 = d.get("levels_completed")
        for a in actions:
            d = sess.action(f"ACTION{a}")
            g = plane(d["frame"])
        lv1 = d.get("levels_completed")
        print(f"  lv {lv0}->{lv1} score7={score_top7(all_b(g), top7)}")
        out["min_top7"] = {"lv0": lv0, "lv1": lv1, "score7": score_top7(all_b(g), top7), "actions": actions}

        # Phase sync: put ALL slots that share alphabet0 on SAME phase index k; slot1 on k; check levels for k=0..6
        print("\n## global phase sync k=0..6 (slots 0,2,3,4 use alpha0 index; slot1 own)")
        # Build ordered alpha cycles via ACT1 from reset-on-slot
        cycles = []
        for si in range(5):
            d = sess.reset()
            g = plane(d["frame"])
            g, _, _ = move(sess, g, si)
            start = bg(g, si)
            cyc = [start]
            for _ in range(6):
                d = sess.action("ACTION1")
                g = plane(d["frame"])
                sig = bg(g, si)
                if sig == start:
                    break
                cyc.append(sig)
            cycles.append(cyc)
            print(f"  slot{si} cycle_len={len(cyc)}")

        sync_hits = []
        for k in range(7):
            d = sess.reset()
            g = plane(d["frame"])
            lv0 = d.get("levels_completed")
            actions = []
            for si in range(5):
                # advance si to phase k (from its reset phase = 0)
                n = k % len(cycles[si])
                d = sess.reset()
                g = plane(d["frame"])
                for a in actions:
                    d = sess.action(f"ACTION{a}")
                    g = plane(d["frame"])
                g, nav, _ = move(sess, g, si)
                trial = actions + nav + [1] * n
                actions = trial
            d = sess.reset()
            g = plane(d["frame"])
            for a in actions:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            lv1 = d.get("levels_completed")
            print(f"  k={k} lv {lv0}->{lv1}")
            sync_hits.append({"k": k, "lv0": lv0, "lv1": lv1, "nact": len(actions)})
            if int(lv1 or 0) > int(lv0 or 0):
                (ROOT / "tests/fixtures/tr87_l1_clear_frame.json").write_text(
                    json.dumps({"frame": d["frame"], "levels": lv1, "k": k, "actions": actions}, indent=2),
                    encoding="utf-8",
                )
                break
        out["phase_sync"] = sync_hits

        # Relative phase: slot i at phase (i*offset) % 7
        print("\n## staggered phase offset=1..3")
        stag = []
        for off in (1, 2, 3):
            d = sess.reset()
            g = plane(d["frame"])
            lv0 = d.get("levels_completed")
            actions = []
            for si in range(5):
                n = (si * off) % 7
                d = sess.reset()
                g = plane(d["frame"])
                for a in actions:
                    d = sess.action(f"ACTION{a}")
                    g = plane(d["frame"])
                g, nav, _ = move(sess, g, si)
                actions = actions + nav + [1] * n
            d = sess.reset()
            g = plane(d["frame"])
            for a in actions:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            lv1 = d.get("levels_completed")
            print(f"  off={off} lv {lv0}->{lv1}")
            stag.append({"off": off, "lv0": lv0, "lv1": lv1})
            if int(lv1 or 0) > int(lv0 or 0):
                break
        out["stagger"] = stag

        # Online local beam from reset: depth-limited, score=score_top7, also watch levels
        print("\n## shallow online walk score watch (budget 80)")
        d = sess.reset()
        g = plane(d["frame"])
        lv0 = d.get("levels_completed")
        best = (score_top7(all_b(g), top7), 0, all_b(g))
        trail = []
        # alternate: for each slot, try all 7 phases pick best score improvement
        for round_i in range(3):
            improved = False
            for si in range(5):
                d = sess.reset()
                g = plane(d["frame"])
                for a in trail:
                    g, d = go(sess, g, a)
                # explore 7 ACT1 from here on si
                g, nav, _ = move(sess, g, si)
                base_trail = trail + nav
                local_best = None
                g_probe = g
                # need forks via reset
                for n in range(0, 7):
                    d = sess.reset()
                    g = plane(d["frame"])
                    for a in base_trail:
                        g, d = go(sess, g, a)
                    for _ in range(n):
                        g, d = go(sess, g, 1)
                    sc = score_top7(all_b(g), top7)
                    lv = d.get("levels_completed")
                    if int(lv or 0) > int(lv0 or 0):
                        print("*** CLEAR during beam", sc, n, si)
                        out["reading"] = "L1_CLEAR"
                        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
                        return
                    if local_best is None or sc < local_best[0]:
                        local_best = (sc, n, list(base_trail) + [1] * n)
                if local_best and local_best[0] < best[0]:
                    best = (local_best[0], best[1] + 1, None)
                    trail = local_best[2]
                    improved = True
                    print(f"  round{round_i} slot{si} -> score {local_best[0]}")
            if not improved:
                break
        d = sess.reset()
        g = plane(d["frame"])
        for a in trail:
            g, d = go(sess, g, a)
        lv1 = d.get("levels_completed")
        print(f"  beam done score={score_top7(all_b(g), top7)} lv {lv0}->{lv1}")
        out["beam"] = {"score": score_top7(all_b(g), top7), "lv0": lv0, "lv1": lv1, "trail": trail}

        cleared = any(
            int(x.get("lv1") or 0) > int(x.get("lv0") or 0)
            for x in [out["assign5"], out["min_top7"], out["beam"]] + sync_hits + stag
        )
        out["reading"] = "L1_CLEAR" if cleared else "SCORE_PARTIAL"
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("READING:", out["reading"])
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
