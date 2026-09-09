"""L4: pixel neighborhood compare left-convert vs mid-nonconvert."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_convert_cmp.json"


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad(sess, d, g, x0):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g
    return d2, plane(d2["frame"])


def neighborhood(g, x0, x1, y0, y1):
    return g[y0 : y1 + 1, x0 : x1 + 1].tolist()


def window_info(g, win):
    # cells around window: left 3 cols, right 1, full y+/-1
    x0 = max(0, win["x0"] - 4)
    x1 = min(63, win["x1"] + 2)
    y0 = max(0, win["y0"] - 1)
    y1 = min(63, win["y1"] + 1)
    patch = g[y0 : y1 + 1, x0 : x1 + 1]
    return {
        "win": win,
        "bbox": [x0, x1, y0, y1],
        "hist": {int(k): int(v) for k, v in zip(*np.unique(patch, return_counts=True))},
        "left_col_colors": [int(x) for x in g[win["y0"] : win["y1"] + 1, win["x0"] - 1]],
        "below": [int(x) for x in g[win["y1"] + 1, win["x0"] : win["x1"] + 1]] if win["y1"] + 1 < 64 else [],
        "sprite": sprite(g),
    }


def main():
    key = _api_key()
    sess = Sess(key)
    out = {}
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        # first down
        d, g = pad(sess, d, g, 15)
        left = [c for c in components(g, 1, 4, 80) if c["cx"] < 20][0]
        out["before_left_convert"] = window_info(g, left)
        print("BEFORE left convert", out["before_left_convert"])
        d, g = pad(sess, d, g, 15)  # convert
        left12 = components(g, 12, 1, 80)[0]
        out["after_left_convert"] = window_info(g, {**left12, "color": 12})
        print("AFTER left convert", out["after_left_convert"])

        # gate + hz + climb to mid adjacency
        d2 = click(sess, round(left12["cx"]), round(left12["cy"]))
        g = plane(d2["frame"]); d = d2
        d, g = pad(sess, d, g, 39)
        # climb to cy=42
        for _ in range(5):
            sp = sprite(g)
            if sp and sp["body"]["cy"] <= 42.5:
                break
            d, g = pad(sess, d, g, 15)
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]
        out["at_mid_adjacent"] = window_info(g, mid)
        print("AT mid adjacent", out["at_mid_adjacent"])
        # one more attempted up (noop) and down-up
        d, g = pad(sess, d, g, 15)
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]
        out["after_extra_up"] = window_info(g, mid)
        d, g = pad(sess, d, g, 9)
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]
        out["after_down"] = window_info(g, mid)
        print("AFTER down", out["after_down"])

        # also check: from cy=45 (one below) info
        OUT.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
