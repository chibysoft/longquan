"""L4: where do env pads flip 0/3 at bay1 ceiling? try gate-lock before climb."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_ndiff  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, sprite, summarize  # noqa: E402

CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 11: "A", 12: "C"}


def dump(g, y0=34, y1=55, x0=0, x1=50):
    for y in range(y0, y1 + 1):
        row = "".join(CHARS.get(int(g[y, x]), str(int(g[y, x]))[-1]) for x in range(x0, x1 + 1))
        print(f"{y:02d}|{row}")


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad(sess, d, g, x0, tag=""):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    g0, s0 = g, sprite(g)
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g, 0, 0
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
    # change cells
    to0 = np.argwhere((g0 == 3) & (g2 == 0))
    to3 = np.argwhere((g0 == 0) & (g2 == 3))
    def bb(arr):
        if len(arr) == 0:
            return None
        return (int(arr[:, 1].min()), int(arr[:, 1].max()), int(arr[:, 0].min()), int(arr[:, 0].max()))
    print(
        f"{tag}x{x0} nd={body_ndiff(g0,g2)} Δ=({dx},{dy}) cy={s1['body']['cy'] if s1 else None} "
        f"h12={int((g2==12).sum())} 3→0bb={bb(to0)} 0→3bb={bb(to3)} lv={d2.get('levels_completed')}"
    )
    return d2, g2, dx, dy


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g, _, _ = pad(sess, d, g, 15, tag="sink ")
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        print("after gate")
        dump(g)
        d, g, dx, _ = pad(sess, d, g, 39, tag="hz ")
        assert abs(dx) > 1
        print("after hz h12", int((g == 12).sum()))
        dump(g)

        # STRATEGY: before climb, spam env while c12 active on floor
        print("\nENV on bay1 floor with c12")
        for x0 in (45, 51, 57, 39, 45, 51):
            d, g, dx, dy = pad(sess, d, g, x0, tag="fenv ")
            if abs(dx) > 0.1:
                print("hz!", dx)
        dump(g)

        # climb one, env, climb one, env — keep trying to plant color0 beside mid
        print("\nInterleaved climb+env")
        for i in range(4):
            d, g, _, dy = pad(sess, d, g, 15, tag=f"up{i} ")
            if abs(dy) < 0.1:
                print("blocked")
                break
            dump(g, 38, 52, 10, 35)
            for e in (39, 45):
                d, g, _, _ = pad(sess, d, g, e, tag=f"e{i} ")
            # check mid convert
            if any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("MID12!", components(g, 12, 1, 80))
                break
            # check color0 near mid
            near = np.argwhere((g[34:46, 23:28] == 0))
            print(f"  color0 near mid band: {len(near)} cells")

        print("\nFINAL")
        dump(g)
        print(summarize(g))
        print("c12", components(g, 12, 1, 80))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
