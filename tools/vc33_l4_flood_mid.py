"""L4: gate then vert pads; also +x at height; flood touch mid."""
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
    print(
        f"{tag}x{x0} nd={body_ndiff(g0,g2)} Δ=({dx},{dy}) "
        f"cx={s1['body']['cx'] if s1 else None} cy={s1['body']['cy'] if s1 else None} "
        f"h12={int((g2==12).sum())} mid12={[c for c in components(g2,12,1,80) if c['cx']>20]} "
        f"ch={body_changes(g0,g2)} lv={d2.get('levels_completed')}"
    )
    return d2, g2, dx, dy


def arm_left(sess, d, g):
    while int((g == 12).sum()) == 0:
        d, g, _, _ = pad(sess, d, g, 15, tag="sink ")
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"])
    print("armed gate", c)
    return d2, g


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        # A: gate then vert from left floor
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        d, g = arm_left(sess, d, g)
        print("A gate+9")
        d, g, _, _ = pad(sess, d, g, 9, tag="A ")
        dump(g)
        # re-enter style: continue — if still c12 try gate+15
        if int((g == 12).sum()):
            c = components(g, 12, 1, 80)[0]
            d2 = click(sess, round(c["cx"]), round(c["cy"]))
            g = plane(d2["frame"]); d = d2
        d, g, _, _ = pad(sess, d, g, 15, tag="A15 ")

        # B: fresh — +x then climb to ceiling, watch flood vs mid on each step with full dump
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        d, g = arm_left(sess, d, g)
        d, g, dx, _ = pad(sess, d, g, 39, tag="Bhz ")
        print("B after hz")
        dump(g)
        for i in range(5):
            g0 = g
            d, g, _, dy = pad(sess, d, g, 15, tag=f"Bup{i} ")
            # show if any c1 cell touched by new color0
            to0 = np.argwhere((g0 == 3) & (g == 0))
            c1 = np.argwhere(g0 == 1)
            touch = 0
            c1set = set(map(tuple, c1))
            for y, x in to0:
                for dx_, dy_ in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                    if (y + dy_, x + dx_) in c1set or (y, x) in c1set:
                        touch += 1
            print(f"  new0={len(to0)} touch_c1_adj={touch}")
            dump(g, 40, 50, 10, 35)
            if any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("MID!")
                break
            if abs(dy) < 0.1:
                break

        # C: at ceiling, try pad39 WITHOUT gate (maybe height unlocks +x?)
        print("C pads at ceiling")
        for x0 in (39, 45, 51, 57, 9, 15):
            d, g, dx, dy = pad(sess, d, g, x0, tag="C ")
            if abs(dx) > 0.1 or any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                dump(g)
                break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
