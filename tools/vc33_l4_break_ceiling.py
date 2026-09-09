"""L4: at bay1 ceiling, click color0 cells / try to lock platform / break ceiling."""
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
from tools.vc33_l4_pad_map import components, enter_l4, sprite, summarize  # noqa: E402


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad(sess, d, g, x0, tag=""):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    s0 = sprite(g)
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g, 0, 0
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
    print(f"{tag}x{x0} Δ=({dx},{dy}) cy={s1['body']['cy'] if s1 else None}")
    return d2, g2, dx, dy


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g, _, _ = pad(sess, d, g, 15, "s")
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        d, g, _, _ = pad(sess, d, g, 39, "hz")
        for i in range(5):
            d, g, _, dy = pad(sess, d, g, 15, f"up{i}")
            if abs(dy) < 0.1:
                break
        print("ceiling", sprite(g))
        # list color0 near sprite
        zeros = [(int(x), int(y)) for y, x in np.argwhere(g == 0) if 15 <= x <= 30 and 40 <= y <= 50]
        print("color0 near", zeros[:40], "n=", len(zeros))
        for x, y in zeros[:12]:
            g0 = g
            d2 = click(sess, x, y)
            if d2 is None:
                break
            g2 = plane(d2["frame"])
            nd = body_ndiff(g0, g2)
            if nd:
                print(f"click0({x},{y}) nd={nd} ch={body_changes(g0,g2)}")
                g = g2; d = d2
        # after clicking zeros, try up again
        d, g, dx, dy = pad(sess, d, g, 15, "retry")
        print("after retry", sprite(g), "mid12", [c for c in components(g, 12, 1, 80) if c["cx"] > 20])
        # try pad9 then env then up — scaffold
        for round_i in range(5):
            d, g, _, _ = pad(sess, d, g, 9, f"dn{round_i}")
            for e in (39, 45):
                d, g, _, _ = pad(sess, d, g, e, f"e{round_i}")
            d, g, dx, dy = pad(sess, d, g, 15, f"u{round_i}")
            d, g, dx, dy = pad(sess, d, g, 15, f"u{round_i}b")
            print(f"round{round_i} cy={sprite(g)['body']['cy']} dy={dy}")
            if sprite(g)["body"]["cy"] < 41.5:
                print("BROKE CEILING")
                break
            if any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("MID12")
                break
        print("final", summarize(g))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
