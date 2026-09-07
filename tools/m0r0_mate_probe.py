"""Drive to candidate mate configs online; try A5/A6; report signals."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import m0r0
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.m0r0_indep_probe import act, pair_key, reset, summarize


def goto(sess, path):
    d = reset(sess)
    for a in path:
        d = act(sess, a)
    return d


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["m0r0_mate"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = sess.s.get(
        f"{BASE}/api/games/m0r0", headers=sess._headers(), timeout=60
    ).json()["game_id"]

    d0 = reset(sess)
    g0 = np.asarray(d0["frame"][0])
    reach = m0r0.reachable(d0["frame"])

    def gap(bbs):
        L, R = bbs
        return R[0] - L[2] - 1

    def v_adj(bbs):
        a, b = bbs
        if a[0] != b[0] or a[2] != b[2]:
            return False
        return a[3] + 1 == b[1] or b[3] + 1 == a[1]

    def h_adj(bbs):
        a, b = bbs
        if a[1] != b[1] or a[3] != b[3]:
            return False
        return a[2] + 1 == b[0] or b[2] + 1 == a[0]

    candidates = []
    for bbs, path in reach.items():
        if v_adj(bbs) or h_adj(bbs) or gap(bbs) == 0:
            candidates.append((path, bbs, "adj"))
    # also closest stacks
    stacks = [b for b in reach if gap(b) < 0]
    stacks = sorted(stacks, key=lambda b: (len(reach[b]), gap(b)))[:8]
    for b in stacks:
        candidates.append((reach[b], b, "stack"))

    # dedupe by path tuple
    seen_p = set()
    uniq = []
    for path, bbs, tag in sorted(candidates, key=lambda t: len(t[0])):
        pt = tuple(path)
        if pt in seen_p:
            continue
        seen_p.add(pt)
        uniq.append((path, bbs, tag))
    print("candidates", len(uniq), "of which adj/stack sampled")

    for path, bbs, tag in uniq[:15]:
        d = goto(sess, path)
        live = pair_key(d["frame"])
        sm = summarize(d)
        ok = live == bbs
        print(f"\n=== {tag} pathlen={len(path)} model_ok={ok}")
        print(" path", path)
        print(" want", bbs, "live", live)
        print(" sm", sm)
        if not ok:
            # still try clicks on live
            bbs = live
        if len(bbs) != 2:
            continue
        g = np.asarray(d["frame"][0])
        lx0, ly0, lx1, ly1 = bbs[0]
        rx0, ry0, rx1, ry1 = bbs[1]
        clicks = [
            ((lx0 + lx1) // 2, (ly0 + ly1) // 2),
            ((rx0 + rx1) // 2, (ry0 + ry1) // 2),
            ((min(lx0, rx0) + max(lx1, rx1)) // 2, (min(ly0, ry0) + max(ly1, ry1)) // 2),
            ((lx1 + rx0) // 2, (ly0 + ly1) // 2),
        ]
        for cx, cy in clicks:
            for aid in (5, 6):
                d2 = act(sess, aid, cx, cy)
                sm2 = summarize(d2)
                ch = int(np.sum(np.asarray(d2["frame"][0]) != g))
                interesting = (
                    sm2["levels"] > 0
                    or sm2["n10"] != sm["n10"]
                    or len(sm2["pcs"]) != 2
                    or ch > 4
                    or sm2["n11"] != sm["n11"]
                    or sm2["n12"] != sm["n12"]
                )
                if interesting:
                    print(f"  CLICK A{aid}@({cx},{cy}) ch={ch}", sm2)
                d = goto(sess, path)
                g = np.asarray(d["frame"][0])
                sm = summarize(d)

    # Also: auto-check if ANY reachable state on live arrival already clears
    print("\n=== scan short paths for auto-clear (len<=12) ===")
    short = sorted(reach.items(), key=lambda kv: len(kv[1]))[:40]
    for bbs, path in short:
        d = goto(sess, path)
        sm = summarize(d)
        live = pair_key(d["frame"])
        if sm["levels"] > 0 or sm["n10"] != 50 or len(sm["pcs"]) != 2:
            print("AUTO", path, sm, "live", live)
        elif live != bbs:
            print("MISMATCH", path, "want", bbs, "live", live)

    sess.close()
    print("done")


if __name__ == "__main__":
    main()
