"""r11l seated clearer: waypoint drag → ship centroid covers goal.

Usage:
  python tools/r11l_seated_clear.py
  python tools/r11l_seated_clear.py --max-levels 1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
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


def act6(sess: OnlineSession, x: int, y: int):
    data = sess.s.post(
        f"{BASE}/api/cmd/ACTION6",
        headers=sess._headers(True),
        json={"game_id": sess.game_id, "guid": sess.guid, "x": int(x), "y": int(y)},
        timeout=60,
    ).json()
    if "frame" not in data:
        raise RuntimeError(f"ACTION6 failed: {data}")
    sess.guid = data.get("guid", sess.guid)
    return data


def clear_l1(sess: OnlineSession, data) -> tuple:
    """Closed-loop L1: move selected wp to goal, select other, move again."""
    lv0 = data.get("levels_completed") or 0
    executed: list[tuple[int, int]] = []
    for round_i in range(6):
        frame = data["frame"]
        gs = r11l.goals(frame)
        wps = r11l.waypoints(frame)
        ship = r11l.ship_center(frame)
        print(
            f"  L1 round {round_i}: ship={ship} goals={[g['c'] for g in gs]} "
            f"wps={[ (w['c'], 'S' if w['selected'] else 'I') for w in wps ]}"
        )
        if not gs:
            raise RuntimeError("L1: no goal diamond")
        goal = gs[0]["c"]
        idle = [w for w in wps if not w["selected"]]
        selected = [w for w in wps if w["selected"]]

        # If nothing selected, select an idle cross first.
        if not selected and idle:
            c = idle[0]["c"]
            data = act6(sess, *c)
            executed.append(c)
            if (data.get("levels_completed") or 0) > lv0:
                return data, executed
            continue

        mt = r11l.move_target(frame, goal)
        for _ in range(2):
            data = act6(sess, *mt)
            executed.append(mt)
            print(
                f"    move {mt} -> ship={r11l.ship_center(data['frame'])} "
                f"lv={data.get('levels_completed')}"
            )
            if (data.get("levels_completed") or 0) > lv0:
                return data, executed

        # Select a still-far waypoint (prefer idle color-3).
        frame = data["frame"]
        wps = r11l.waypoints(frame)
        idle = [w for w in wps if not w["selected"]]
        far = sorted(
            wps,
            key=lambda w: abs(w["c"][0] - goal[0]) + abs(w["c"][1] - goal[1]),
            reverse=True,
        )
        pick = (idle[0] if idle else far[0])["c"]
        data = act6(sess, *pick)
        executed.append(pick)
        print(f"    select {pick} lv={data.get('levels_completed')}")
        if (data.get("levels_completed") or 0) > lv0:
            return data, executed

        mt = r11l.move_target(data["frame"], goal)
        for _ in range(2):
            data = act6(sess, *mt)
            executed.append(mt)
            print(
                f"    move2 {mt} -> ship={r11l.ship_center(data['frame'])} "
                f"lv={data.get('levels_completed')}"
            )
            if (data.get("levels_completed") or 0) > lv0:
                return data, executed

    raise RuntimeError(
        f"L1 clear failed; ship={r11l.ship_center(data['frame'])} "
        f"lv={data.get('levels_completed')}"
    )


def clear_one_level(sess: OnlineSession, data) -> tuple:
    lv0 = data.get("levels_completed") or 0
    if lv0 == 0:
        return clear_l1(sess, data)
    if lv0 == 1:
        from tools.r11l_l2_clear_probe import clear_l2

        return clear_l2(sess, data)
    if lv0 == 2:
        from tools.r11l_l3_sync_probe import clear_l3

        return clear_l3(sess, data)
    raise RuntimeError(
        f"r11l L{lv0 + 1} not seated yet; pcs ship={r11l.ship_center(data['frame'])} "
        f"goals={r11l.goals(data['frame'])} wps={r11l.waypoints(data['frame'])}"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-levels", type=int, default=2)
    args = ap.parse_args()

    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_clear"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    meta = sess.s.get(f"{BASE}/api/games/r11l", headers=sess._headers(), timeout=60).json()
    sess.game_id = meta["game_id"]
    print("game", sess.game_id, "baselines", meta.get("baseline_actions"))

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
            out = ROOT / "tests" / "fixtures" / f"r11l_fail_lv{lv}.json"
            out.write_text(
                json.dumps(
                    {
                        "frame": data["frame"],
                        "levels_completed": lv,
                        "ship": r11l.ship_center(data["frame"]),
                        "goals": r11l.goals(data["frame"]),
                        "waypoints": [
                            {k: v for k, v in w.items() if k != "cells"}
                            for w in r11l.waypoints(data["frame"])
                        ],
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
