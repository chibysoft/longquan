"""m0r0 seated clearer: hazard-aware mate (flush + compress).

Usage:
  python tools/m0r0_seated_clear.py
  python tools/m0r0_seated_clear.py --max-levels 6
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import m0r0
from tools.ls20_online_validate import BASE, OnlineSession, _api_key


def reset(sess: OnlineSession):
    body = {"card_id": sess.card_id, "game_id": sess.game_id}
    if sess.guid:
        body["guid"] = sess.guid
    data = sess.s.post(
        f"{BASE}/api/cmd/RESET", headers=sess._headers(True), json=body, timeout=60
    ).json()
    sess.guid = data["guid"]
    return data


def act(sess: OnlineSession, aid: int):
    data = sess.s.post(
        f"{BASE}/api/cmd/ACTION{aid}",
        headers=sess._headers(True),
        json={"game_id": sess.game_id, "guid": sess.guid},
        timeout=60,
    ).json()
    sess.guid = data.get("guid", sess.guid)
    return data


def ensure_twins(sess: OnlineSession, data):
    """After a clear, leftover single block — try nudges until twins + mate path."""
    if len(m0r0.locate_pieces(data["frame"])) == 2:
        if m0r0.find_mate_path(data["frame"]) is not None:
            return data
    # Prefer recording the leftover; try each enter aid.
    leftover = data
    for nudge in (4, 1, 2, 3):
        data = act(sess, nudge)
        pcs = m0r0.locate_pieces(data["frame"])
        print(f"  interstitial A{nudge} -> pcs={pcs}")
        if len(pcs) == 2 and m0r0.find_mate_path(data["frame"]) is not None:
            return data
        if len(pcs) == 2:
            # twins but no flush-mate path yet (e.g. L3) — still return for caller
            leftover = data
    if len(m0r0.locate_pieces(leftover["frame"])) == 2:
        return leftover
    raise RuntimeError("could not enter twin layout")


def clear_one_level(sess: OnlineSession, data) -> tuple:
    lv0 = data.get("levels_completed") or 0
    data = ensure_twins(sess, data)
    params = m0r0.infer_params(data["frame"])
    path = m0r0.find_mate_path(data["frame"], params)
    if not path:
        raise RuntimeError(
            f"no mate path; pcs={m0r0.locate_pieces(data['frame'])} params={params}"
        )
    print(f"  plan len={len(path)} params={params} path={path}")

    g0 = np.asarray(data["frame"][0]).copy()
    pred = tuple(m0r0.locate_pieces(data["frame"]))
    for i, a in enumerate(path):
        g = m0r0.synthesize_grid(g0, pred) if len(pred) == 2 else g0
        nxt = m0r0.apply_action(g, pred, a, params) if len(pred) == 2 else None
        data = act(sess, a)
        lv = data.get("levels_completed") or 0
        live = tuple(m0r0.locate_pieces(data["frame"]))
        if lv > lv0:
            print(f"  cleared -> levels={lv} after step {i} A{a}")
            return data, path
        if len(live) == 1:
            # merged — try compress aids if path's remaining action isn't enough
            print(f"  merged at step {i}: {live}")
            for ca in m0r0.mate_compress_actions(data["frame"], params) or [4, 1, 2]:
                data = act(sess, ca)
                lv = data.get("levels_completed") or 0
                print(f"  compress A{ca} -> lv={lv} pcs={m0r0.locate_pieces(data['frame'])}")
                if lv > lv0:
                    return data, path[: i + 1] + [ca]
            raise RuntimeError("merged but compress did not clear")
        if nxt is not None and nxt != live:
            raise RuntimeError(f"kinematics mismatch step {i} A{a}: pred={nxt} live={live}")
        pred = live

    lv = data.get("levels_completed") or 0
    if lv <= lv0:
        raise RuntimeError(
            f"path exhausted without clear; pcs={m0r0.locate_pieces(data['frame'])} "
            f"n10={int((np.asarray(data['frame'][0])==10).sum())}"
        )
    return data, path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-levels", type=int, default=6)
    args = ap.parse_args()

    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["m0r0_clear"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    meta = sess.s.get(f"{BASE}/api/games/m0r0", headers=sess._headers(), timeout=60).json()
    sess.game_id = meta["game_id"]
    print("game", sess.game_id, "win_levels", meta.get("win_levels"))

    data = reset(sess)
    paths = []
    while (data.get("levels_completed") or 0) < args.max_levels:
        if data.get("state") == "WIN":
            break
        lv = data.get("levels_completed") or 0
        print(f"=== level {lv} -> {lv + 1} ===")
        try:
            data, path = clear_one_level(sess, data)
            paths.append(path)
        except Exception as e:
            print("FAIL", e)
            out = ROOT / "tests" / "fixtures" / f"m0r0_fail_lv{lv}.json"
            out.write_text(
                json.dumps(
                    {
                        "frame": data["frame"],
                        "levels_completed": lv,
                        "pcs": m0r0.locate_pieces(data["frame"]),
                        "error": str(e),
                    }
                ),
                encoding="utf-8",
            )
            print("saved", out)
            sess.close()
            return 1
        print(f"  now levels={data.get('levels_completed')} state={data.get('state')}")

    print("DONE levels", data.get("levels_completed"), "state", data.get("state"))
    print("paths", paths)
    sess.close()
    ok = (data.get("levels_completed") or 0) >= args.max_levels or data.get("state") == "WIN"
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
