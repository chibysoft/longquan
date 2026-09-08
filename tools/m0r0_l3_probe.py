"""m0r0 L3 probe: falsify mate hypotheses beyond flush-adjacent.

Usage:
  python tools/m0r0_l3_probe.py
"""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import m0r0
from tools.ls20_online_validate import BASE, OnlineSession, _api_key


def reset(sess):
    body = {"card_id": sess.card_id, "game_id": sess.game_id}
    if sess.guid:
        body["guid"] = sess.guid
    d = sess.s.post(
        f"{BASE}/api/cmd/RESET", headers=sess._headers(True), json=body, timeout=60
    ).json()
    sess.guid = d["guid"]
    return d


def act(sess, aid, x=None, y=None):
    body = {"game_id": sess.game_id, "guid": sess.guid}
    if x is not None:
        body["x"] = x
        body["y"] = y
    d = sess.s.post(
        f"{BASE}/api/cmd/ACTION{aid}", headers=sess._headers(True), json=body, timeout=60
    ).json()
    sess.guid = d.get("guid", sess.guid)
    return d


def clear_to_l2(sess):
    d = reset(sess)
    while (d.get("levels_completed") or 0) < 2:
        lv0 = d.get("levels_completed") or 0
        for _ in range(6):
            if len(m0r0.locate_pieces(d["frame"])) == 2:
                break
            d = act(sess, 4)
        if len(m0r0.locate_pieces(d["frame"])) == 1:
            for a in (1, 2, 3):
                d = act(sess, a)
                if len(m0r0.locate_pieces(d["frame"])) == 2:
                    break
        path = m0r0.find_mate_path(d["frame"])
        if not path:
            raise RuntimeError(f"no mate path at lv={lv0} pcs={m0r0.locate_pieces(d['frame'])}")
        params = m0r0.infer_params(d["frame"])
        g0 = np.asarray(d["frame"][0]).copy()
        pred = tuple(m0r0.locate_pieces(d["frame"]))
        for a in path:
            g = m0r0.synthesize_grid(g0, pred) if len(pred) == 2 else g0
            d = act(sess, a)
            live = tuple(m0r0.locate_pieces(d["frame"]))
            if (d.get("levels_completed") or 0) > lv0:
                break
            if len(live) == 1:
                d = act(sess, 4)
                break
            pred = live
    return d


def enter_l3(sess, enter_aid=4):
    d = clear_to_l2(sess)
    if len(m0r0.locate_pieces(d["frame"])) == 1:
        d = act(sess, enter_aid)
    return d


def summarize(d, label=""):
    g = np.asarray(d["frame"][0])
    pcs = m0r0.locate_pieces(d["frame"])
    return {
        "label": label,
        "lv": d.get("levels_completed") or 0,
        "state": d.get("state"),
        "pcs": pcs,
        "n10": int((g == 10).sum()),
        "n9": int((g == 9).sum()),
        "n8": int((g == 8).sum()),
        "n15": int((g == 15).sum()),
        "n6": int((g == 6).sum()),
        "uniq": sorted(int(c) for c in np.unique(g)),
    }


def interesting(before, after):
    keys = ("lv", "n10", "n9", "n8", "n15", "n6")
    if any(after[k] != before[k] for k in keys):
        return True
    if len(after["pcs"]) != len(before["pcs"]):
        return True
    return False


def offline_gap4_paths(frame):
    g0 = np.asarray(frame[0] if np.asarray(frame).ndim == 3 else frame)
    # handle list frame
    g0 = np.asarray(frame)
    if g0.ndim == 3:
        g0 = g0[0]
    params = m0r0.infer_params(frame)
    spawn = tuple(m0r0.locate_pieces(frame))
    q = deque([spawn])
    seen = {spawn: []}
    gap4 = []
    while q:
        bbs = q.popleft()
        path = seen[bbs]
        if len(bbs) == 2 and bbs[0][1] == bbs[1][1] and bbs[1][0] - bbs[0][2] - 1 == 4:
            gap4.append((path, bbs))
        g = m0r0.synthesize_grid(g0, bbs)
        for aid in (1, 2, 3, 4):
            nxt = m0r0.apply_action(g, bbs, aid, params)
            if nxt is None or nxt in seen:
                continue
            seen[nxt] = path + [aid]
            q.append(nxt)
    gap4.sort(key=lambda t: len(t[0]))
    return seen, gap4


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["m0r0_l3"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = sess.s.get(
        f"{BASE}/api/games/m0r0", headers=sess._headers(), timeout=60
    ).json()["game_id"]
    print("game", sess.game_id)

    hits = []
    for enter in (4, 1, 2, 3):
        d = enter_l3(sess, enter)
        sm0 = summarize(d, f"enter{enter}")
        print("ENTER", sm0)
        Path(f"tests/fixtures/m0r0_l3_enter_a{enter}.json").write_text(
            json.dumps({"frame": d["frame"], "enter": enter, "meta": sm0}),
            encoding="utf-8",
        )
        if len(sm0["pcs"]) != 2:
            continue

        g = np.asarray(d["frame"][0])
        c9 = list(zip(*np.where(g == 9)))  # (y,x)
        c9_pts = [(int(x), int(y)) for y, x in c9]
        print(" c9", sorted(set(c9_pts)))

        seen, gap4 = offline_gap4_paths(d["frame"])
        print(" reach", len(seen), "gap4", len(gap4))

        # H1: at each gap4 config, A5/A6 on mid-gap + piece centers + all c9
        for path, bbs in gap4[:6]:
            d = enter_l3(sess, enter)
            for a in path:
                d = act(sess, a)
            live = tuple(m0r0.locate_pieces(d["frame"]))
            if live != bbs and len(live) == 2:
                # accept if same gap geometry
                pass
            before = summarize(d)
            L, R = m0r0.locate_pieces(d["frame"])
            if len(m0r0.locate_pieces(d["frame"])) != 2:
                continue
            clicks = [
                ((L[2] + R[0]) // 2, (L[1] + L[3]) // 2),
                ((L[0] + L[2]) // 2, (L[1] + L[3]) // 2),
                ((R[0] + R[2]) // 2, (R[1] + R[3]) // 2),
                (31, 15),
                (11, 19),
                (39, 31),
            ] + c9_pts[:4]
            for cx, cy in clicks:
                for ca in (5, 6):
                    d = enter_l3(sess, enter)
                    for a in path:
                        d = act(sess, a)
                    b = summarize(d)
                    d2 = act(sess, ca, cx, cy)
                    a = summarize(d2, f"gap4+A{ca}@{cx},{cy}")
                    ch = int(
                        np.sum(np.asarray(d2["frame"][0]) != np.asarray(d["frame"][0]))
                    )
                    if interesting(b, a) or ch > 4:
                        print(" HIT", path, a, "ch", ch)
                        hits.append((path, a, ch))

        # H2: walk toward each c9 cluster (nearest piece approach) then click c9
        # Use short greedy: from spawn, BFS path that minimizes dist of either piece to cluster
        clusters = [(31, 15), (11, 19), (39, 31)]
        for tx, ty in clusters:
            # find state minimizing manhattan from piece TL to (tx-1,ty-1) approx
            best = None
            for bbs, path in seen.items():
                for bb in bbs:
                    dist = abs(bb[0] - (tx - 1)) + abs(bb[1] - (ty - 1))
                    if best is None or dist < best[0]:
                        best = (dist, path, bbs, bb)
            if best is None:
                continue
            dist, path, bbs, bb = best
            print(f" near c9({tx},{ty}) dist={dist} pathlen={len(path)} at={bb}")
            d = enter_l3(sess, enter)
            for a in path:
                d = act(sess, a)
            b = summarize(d)
            for ca in (5, 6):
                d = enter_l3(sess, enter)
                for a in path:
                    d = act(sess, a)
                d2 = act(sess, ca, tx, ty)
                a = summarize(d2)
                ch = int(np.sum(np.asarray(d2["frame"][0]) != np.asarray(d["frame"][0])))
                if interesting(b, a) or ch > 4 or a["n9"] != b["n9"]:
                    print(" HIT near9", path[-6:], a, "ch", ch)
                    hits.append((path, a, ch))

        # H3: same-session online BFS 30 steps looking for any lv/n10/n9 signal
        d = enter_l3(sess, enter)
        start = tuple(m0r0.locate_pieces(d["frame"]))
        q = deque([(start, [])])
        vis = {start}
        steps = 0
        while q and steps < 40:
            bbs, path = q.popleft()
            d = enter_l3(sess, enter)
            for a in path:
                d = act(sess, a)
            if tuple(m0r0.locate_pieces(d["frame"])) != bbs:
                continue
            b = summarize(d)
            for aid in (1, 2, 3, 4):
                d = enter_l3(sess, enter)
                for a in path:
                    d = act(sess, a)
                d2 = act(sess, aid)
                steps += 1
                a = summarize(d2)
                st = tuple(a["pcs"])
                if interesting(b, a):
                    print(" LIVE_SIGNAL", path + [aid], b, "->", a)
                    hits.append((path + [aid], a, 0))
                if len(st) == 2 and st not in vis:
                    vis.add(st)
                    q.append((st, path + [aid]))
        print(f" online bfs enter{enter}: steps={steps} states={len(vis)}")

        # only fully probe enter=4 first for time
        if enter == 4:
            break

    print("TOTAL HITS", len(hits))
    for h in hits[:20]:
        print(" ", h)
    sess.close()
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
