"""L4: at ceiling, poke beam under mid and cell (26,45); check 4/8 adj to mid."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_changes, body_ndiff  # noqa: E402
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
    g2 = plane(d2["frame"])
    print(tag, "cy", sprite(g2)["body"]["cy"], "h12", int((g2 == 12).sum()))
    return d2, g2


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g = pad(sess, d, g, 15, "s")
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        d, g = pad(sess, d, g, 39, "hz")
        for _ in range(5):
            d, g = pad(sess, d, g, 15, "up")
            if sprite(g)["body"]["cy"] <= 42.5:
                # check if stuck
                g0 = g
                d, g = pad(sess, d, g, 15, "probe")
                if sprite(g)["body"]["cy"] == sprite(g0)["body"]["cy"]:
                    break

        print("at", sprite(g))
        # print neighborhood around mid bottom-left corner
        for y in range(43, 48):
            row = [int(g[y, x]) for x in range(23, 31)]
            print(f"y{y} x23-30: {row}")

        for x, y in [(26, 45), (27, 46), (28, 46), (26, 46), (25, 45), (27, 45)]:
            g0 = g
            d2 = click(sess, x, y)
            if d2 is None:
                break
            g2 = plane(d2["frame"])
            nd = body_ndiff(g0, g2)
            print(f"click({x},{y}) valwas={int(g0[y,x])} nd={nd} ch={body_changes(g0,g2)} "
                  f"h12={int((g2==12).sum())} lv={d2.get('levels_completed')}")
            if nd:
                g = g2; d = d2
                if any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                    print("MID CONVERTED")
                    break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
