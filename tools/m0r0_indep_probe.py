"""m0r0: verify independent kinematics live + search mate signals.

Usage:
  python tools/m0r0_indep_probe.py
  python tools/m0r0_indep_probe.py --explore 80
"""
from __future__ import annotations

import argparse
import sys
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import m0r0  # noqa: E402
from tools.ls20_online_validate import BASE, OnlineSession, _api_key  # noqa: E402


def reset(sess: OnlineSession):
    body = {"card_id": sess.card_id, "game_id": sess.game_id}
    if sess.guid:
        body["guid"] = sess.guid
    data = sess.s.post(
        f"{BASE}/api/cmd/RESET", headers=sess._headers(True), json=body, timeout=60
    ).json()
    sess.guid = data["guid"]
    return data


def act(sess: OnlineSession, aid: int, x: int | None = None, y: int | None = None):
    body = {"game_id": sess.game_id, "guid": sess.guid}
    if x is not None and y is not None:
        body["x"] = x
        body["y"] = y
    data = sess.s.post(
        f"{BASE}/api/cmd/ACTION{aid}", headers=sess._headers(True), json=body, timeout=60
    ).json()
    sess.guid = data.get("guid", sess.guid)
    return data


def pair_key(frame) -> tuple:
    return tuple(m0r0.locate_pieces(frame))


def summarize(data) -> dict:
    g = np.asarray(data["frame"][0])
    pcs = m0r0.locate_pieces(data["frame"])
    return {
        "levels": data.get("levels_completed") or 0,
        "state": data.get("state"),
        "n10": int((g == 10).sum()),
        "n11": int((g == 11).sum()),
        "n12": int((g == 12).sum()),
        "pcs": pcs,
        "uniq": sorted(int(c) for c in np.unique(g)),
    }


def verify_sequences(sess: OnlineSession) -> bool:
    seqs = [
        [1],
        [1, 1],
        [1, 1, 1],
        [4],
        [4, 4],
        [3],
        [1, 4],
        [1, 3, 1],
        [1, 1, 4],
        [1, 1, 3, 1],
    ]
    ok = True
    for seq in seqs:
        d = reset(sess)
        g0 = np.asarray(d["frame"][0])
        pred = pair_key(d["frame"])
        for a in seq:
            g = m0r0.synthesize_grid(g0, pred)
            nxt = m0r0.apply_action(g, pred, a)
            d = act(sess, a)
            live = pair_key(d["frame"])
            # None = both blocked → engine no-op (stay).
            expect = pred if nxt is None else nxt
            if expect != live:
                print("MISMATCH", seq, "pred", nxt, "live", live)
                ok = False
                break
            pred = live
        else:
            print("OK", seq, "->", pred)
    return ok


def offline_reach_stats(frame) -> int:
    reach = m0r0.reachable(frame)
    print("offline reachable", len(reach), "maxpath", max(len(p) for p in reach.values()))
    # sample asymmetric states (different y)
    asym = [bbs for bbs in reach if bbs[0][1] != bbs[1][1]]
    print("asymmetric_y", len(asym), "eg", asym[:3])
    return len(reach)


def _goto(sess: OnlineSession, path: list[int]):
    d = reset(sess)
    for a in path:
        d = act(sess, a)
    return d


def explore_online(sess: OnlineSession, budget: int) -> None:
    """Online BFS with reset-replay; watch levels / n10 / paint / piece count."""
    d = reset(sess)
    start = pair_key(d["frame"])
    q = deque([start])
    seen: dict = {start: []}
    hits = []
    steps = 0
    while q and steps < budget:
        bbs = q.popleft()
        path = seen[bbs]
        d = _goto(sess, path)
        live = pair_key(d["frame"])
        if live != bbs:
            print("NAV_MISMATCH", path, "want", bbs, "live", live)
            continue
        g = np.asarray(d["frame"][0])
        for aid in (1, 2, 3, 4):
            if steps >= budget:
                break
            pred = m0r0.apply_action(g, bbs, aid)
            d2 = act(sess, aid)
            steps += 1
            live2 = pair_key(d2["frame"])
            sm = summarize(d2)
            if pred != live2:
                print("STEP_MISMATCH", path + [aid], "pred", pred, "live", live2)
            if sm["levels"] > 0 or sm["n10"] != 50 or len(sm["pcs"]) != 2:
                hits.append((path + [aid], sm))
                print("SIGNAL", path + [aid], sm)
            if live2 not in seen:
                seen[live2] = path + [aid]
                q.append(live2)
            d = _goto(sess, path)
            g = np.asarray(d["frame"][0])
            bbs = pair_key(d["frame"])
        # A5/A6 at piece centers + mid-gap
        if len(bbs) == 2 and steps < budget:
            lx0, ly0, lx1, ly1 = bbs[0]
            rx0, ry0, rx1, ry1 = bbs[1]
            clicks = [
                ((lx0 + lx1) // 2, (ly0 + ly1) // 2),
                ((rx0 + rx1) // 2, (ry0 + ry1) // 2),
                ((lx1 + rx0) // 2, (min(ly0, ry0) + max(ly1, ry1)) // 2),
            ]
            for cx, cy in clicks:
                for aid in (5, 6):
                    if steps >= budget:
                        break
                    d2 = act(sess, aid, cx, cy)
                    steps += 1
                    sm = summarize(d2)
                    ch = int(np.sum(np.asarray(d2["frame"][0]) != g))
                    if sm["levels"] > 0 or sm["n10"] != 50 or len(sm["pcs"]) != 2 or ch > 4:
                        hits.append((path + [f"A{aid}@{cx},{cy}"], sm | {"ch": ch}))
                        print("CLICK_SIGNAL", path, f"A{aid}@({cx},{cy})", sm, "ch", ch)
                    d = _goto(sess, path)
                    g = np.asarray(d["frame"][0])
                    bbs = pair_key(d["frame"])
    print("explore done steps", steps, "states", len(seen), "hits", len(hits))
    for h in hits[:20]:
        print(" hit", h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--explore", type=int, default=40, help="online BFS step budget")
    ap.add_argument("--skip-verify", action="store_true")
    args = ap.parse_args()

    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["m0r0_indep"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = sess.s.get(
        f"{BASE}/api/games/m0r0", headers=sess._headers(), timeout=60
    ).json()["game_id"]
    print("game", sess.game_id)

    d0 = reset(sess)
    offline_reach_stats(d0["frame"])
    if not args.skip_verify:
        ok = verify_sequences(sess)
        print("verify", "PASS" if ok else "FAIL")
        if not ok:
            sess.close()
            return 1
    explore_online(sess, args.explore)
    sess.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
