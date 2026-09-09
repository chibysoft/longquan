"""L4: before left-convert, log cols around window; try plant 0 into mid via env order."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, sprite  # noqa: E402


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad(sess, d, g, x0, tag=""):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g
    print(tag, "cy", sprite(plane(d2["frame"]))["body"]["cy"], "h12", int((plane(d2["frame"]) == 12).sum()))
    return d2, plane(d2["frame"])


def show_win(g, label, win):
    print(label, "win", win)
    for x in range(win["x0"] - 3, win["x1"] + 4):
        cells = [(y, int(g[y, x])) for y in range(win["y0"], win["y1"] + 1)]
        zeros = [y for y, c in cells if c == 0]
        print(f"  x{x} zeros_in_win_y={zeros} top3={[c for _,c in cells[:3]]} bot3={[c for _,c in cells[-3:]]}")


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        d, g = pad(sess, d, g, 15, "d1")
        left = [c for c in components(g, 1, 4, 80) if c["cx"] < 20][0]
        show_win(g, "BEFORE", left)
        print("accent", sprite(g)["accent"])
        d, g = pad(sess, d, g, 15, "d2")
        left12 = components(g, 12, 1, 80)[0]
        show_win(g, "AFTER", left12)
        print("accent", sprite(g)["accent"])

        # Now: can env before hop create lasting color0 near mid?
        # Reset path: gate, env spam on LEFT side before hop?, hop, check x26
        # Actually still in session — gate and try
        d2 = click(sess, round(left12["cx"]), round(left12["cy"]))
        g = plane(d2["frame"]); d = d2
        # env BEFORE hop
        for e in (39, 45, 39, 45):
            d, g = pad(sess, d, g, e, f"pre{e}")
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]
        show_win(g, "pre-hop mid", mid)
        d, g = pad(sess, d, g, 39, "hop")
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]
        show_win(g, "post-hop mid", mid)
        # climb one and show
        for i in range(3):
            d, g = pad(sess, d, g, 15, f"up{i}")
            mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]
            show_win(g, f"up{i} mid", mid)
            print("accent", sprite(g)["accent"], "cy", sprite(g)["body"]["cy"])
            if int((g == 12).sum()) and any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("MID CONVERTED")
                break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
