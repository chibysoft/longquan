"""g50t L3: after pierce, top-east, descend right col — explore & clear hunt.

tags=["g50t_recon"]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import BASE, _api_key  # noqa: E402
from tools.g50t_l3_recon_probe import (  # noqa: E402
    L1_SEQ,
    TO_2840,
    L2_ROUTE,
    H,
    plane,
    actor,
    e8,
)

OUT = ROOT / "tests/fixtures/g50t_l3_rightcol_deep.json"
CLEAR = ROOT / "tests/fixtures/g50t_l3_clear_attempt.json"
FRAME = ROOT / "tests/fixtures/g50t_l3_rightcol_open_frame.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
# pierce + UU + top east + down to (52,22)
TO_RIGHT_OPEN = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2]


def p(*a, **k):
    print(*a, **k, flush=True)


def c11info(g):
    ys, xs = np.where(g == 11)
    if len(xs) == 0:
        return {"n": 0}
    return {
        "n": int(len(xs)),
        "xmin": int(xs.min()),
        "xmax": int(xs.max()),
        "ymin": int(ys.min()),
        "ymax": int(ys.max()),
    }


def right_blk(g):
    return int(np.sum(g[20:25, 50:55] == 11))


def show(tag, prev, g, d=None):
    p(
        f"  {tag}",
        (prev["cx"], prev["cy"]) if prev else None,
        "e8",
        e8(g)["n"],
        "c11",
        c11info(g),
        "blkN",
        right_blk(g),
        "lv",
        None if d is None else d.get("levels_completed"),
    )


def main():
    key = _api_key()
    s = requests.Session()
    card = s.post(
        f"{BASE}/api/scorecard/open",
        headers=H(key, True),
        json={"tags": ["g50t_recon"]},
        timeout=30,
    ).json()["card_id"]
    gid = s.get(f"{BASE}/api/games/g50t", headers=H(key), timeout=20).json()["game_id"]
    p("opened", gid)

    def reset():
        return s.post(
            f"{BASE}/api/cmd/RESET",
            headers=H(key, True),
            json={"card_id": card, "game_id": gid},
            timeout=30,
        ).json()

    def act(guid, aid):
        d = s.post(
            f"{BASE}/api/cmd/ACTION{aid}",
            headers=H(key, True),
            json={"game_id": gid, "guid": guid},
            timeout=30,
        ).json()
        if "guid" not in d:
            raise RuntimeError(str({k: d.get(k) for k in d if k != "frame"}))
        return d

    def enter_l3():
        d = reset()
        guid = d["guid"]
        g = plane(d)
        prev = None
        for a_ in L1_SEQ + [2] * 4 + [4] * 8:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) >= 1:
                break
        d = act(guid, 3)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        for a_ in TO_2840 + L2_ROUTE:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) >= 2:
                break
        d = act(guid, 3)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        return guid, g, prev

    def play(guid, g, prev, seq):
        log = []
        for a_ in seq:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            log.append(
                {
                    "a": a_,
                    "pos": (prev["cx"], prev["cy"]) if prev else None,
                    "c11": c11info(g),
                    "e8": e8(g)["n"],
                    "lv": d.get("levels_completed"),
                }
            )
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, d, log, True
        return guid, g, prev, d, log, False

    def latch(guid, g, prev):
        guid, g, prev, d, log, ok = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if ok:
            return guid, g, prev, d, log, True
        return play(guid, g, prev, TO_3434 + [4, 4, 3, 3])

    def open_right(guid, g, prev):
        return play(guid, g, prev, TO_RIGHT_OPEN)

    def path_of(log):
        path = []
        for r in log:
            if r["pos"] and (not path or path[-1] != r["pos"]):
                path.append(r["pos"])
        return path

    out = {"cleared": False}
    cleared = False

    # --- star from (52,22): each dir ---
    p("## star@5222")
    star = {}
    for aid in (1, 2, 3, 4, 5):
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, ok = latch(guid, g, prev)
        if ok:
            cleared = True
            break
        guid, g, prev, d, log, ok = open_right(guid, g, prev)
        if ok:
            cleared = True
            CLEAR.write_text(
                json.dumps({"cleared": True, "method": "TO_RIGHT_OPEN"}, indent=2, default=str),
                encoding="utf-8",
            )
            break
        show("at5222", prev, g, d)
        before = (prev["cx"], prev["cy"])
        for tap in (aid, aid):
            d = act(guid, tap)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                break
        after = (prev["cx"], prev["cy"]) if prev else None
        star[aid] = {
            "before": before,
            "after": after,
            "moved": before != after,
            "c11": c11info(g),
            "e8": e8(g)["n"],
            "lv": d.get("levels_completed"),
        }
        p(f"  A{aid}", before, "->", after, "c11", c11info(g), "e8", e8(g)["n"])
        if cleared:
            break
        # dump frame once
        if aid == 2 and before != after:
            FRAME.write_text(json.dumps(d, default=str), encoding="utf-8")
    out["star5222"] = star
    if cleared:
        out["cleared"] = True
        out["reading"] = "L3_CLEAR"
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        p("READING: L3_CLEAR")
        s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)
        return

    # --- deep descents / west runs ---
    trials = {
        # continue down right col
        "down_deep": TO_RIGHT_OPEN + [2] * 12,
        # west along y28
        "west_y28": TO_RIGHT_OPEN + [2, 2, 3] + [3] * 10,
        # west along y22 (maybe after drain)
        "west_y22": TO_RIGHT_OPEN + [3] * 12,
        # down to y34 then west (toward tip1 / tip2)
        "down_y34_west": TO_RIGHT_OPEN + [2, 2, 2, 3] + [3] * 8,
        # down toward tip2 (40,40)/(40,46) via bottom?
        "down_y40_west": TO_RIGHT_OPEN + [2] * 5 + [3] * 6,
        "down_y46_west": TO_RIGHT_OPEN + [2] * 6 + [3] * 6,
        "down_y52_west": TO_RIGHT_OPEN + [2] * 8 + [3] * 8,
        # from 5222 up then? 
        "from5222_L_then_D": TO_RIGHT_OPEN + [3, 3, 2, 2, 3, 3],
        # A5 at various depths
        "A5_at5222": TO_RIGHT_OPEN + [5, 5],
        "A5_at5228": TO_RIGHT_OPEN + [2, 2, 5, 5],
        "A5_at5234": TO_RIGHT_OPEN + [2, 2, 2, 2, 5, 5],
    }

    for name, seq in trials.items():
        p(f"## {name}")
        guid, g, prev = enter_l3()
        guid, g, prev, d, _, ok = latch(guid, g, prev)
        if ok:
            cleared = True
            break
        guid, g, prev, d, log, ok = play(guid, g, prev, seq)
        path = path_of(log)
        p("  path", path)
        show("final", prev, g, d)
        out[name] = {
            "path": path,
            "final": log[-1] if log else None,
            "e8": e8(g)["n"],
            "c11": c11info(g),
        }
        if ok or (d.get("levels_completed") or 0) > 2:
            cleared = True
            CLEAR.write_text(
                json.dumps({"cleared": True, "method": name, "path": path, "log": log}, indent=2, default=str),
                encoding="utf-8",
            )
            break
        # greedy hunt to (22,22) if anywhere near mid/bottom
        if prev and (prev["cx"] < 52 or prev["cy"] >= 28):
            stuck = 0
            hunt_log = []
            for _ in range(30):
                cx, cy = prev["cx"], prev["cy"]
                dx, dy = 22 - cx, 22 - cy
                if abs(dx) < 0.1 and abs(dy) < 0.1:
                    # on goal cell — try A5?
                    aid = 5
                else:
                    aid = (4 if dx > 0 else 3) if abs(dx) >= abs(dy) else (2 if dy > 0 else 1)
                b = (cx, cy)
                for a_ in (aid, aid):
                    d = act(guid, a_)
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                    hunt_log.append({"a": a_, "pos": (prev["cx"], prev["cy"]) if prev else None, "lv": d.get("levels_completed")})
                    if (d.get("levels_completed") or 0) > 2:
                        cleared = True
                        break
                show("h", prev, g, d)
                if cleared:
                    break
                if prev and (prev["cx"], prev["cy"]) == b:
                    stuck += 1
                    if stuck >= 2:
                        # try alternate axis
                        aid2 = (2 if dy > 0 else 1) if abs(dx) >= abs(dy) else (4 if dx > 0 else 3)
                        for a_ in (aid2, aid2):
                            d = act(guid, a_)
                            guid = d["guid"]
                            g = plane(d)
                            prev = actor(g, prev)
                        if prev and (prev["cx"], prev["cy"]) == b:
                            break
                        stuck = 0
                else:
                    stuck = 0
            out[name]["hunt_path"] = path_of(hunt_log)
            if cleared:
                CLEAR.write_text(
                    json.dumps(
                        {"cleared": True, "method": name + "+hunt", "path": path, "hunt": hunt_log},
                        indent=2,
                        default=str,
                    ),
                    encoding="utf-8",
                )
                break

    out["cleared"] = cleared
    out["reading"] = "L3_CLEAR" if cleared else "L3_RIGHTCOL_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
