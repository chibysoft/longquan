"""L4: why ceiling? dump above-sprite cells; try nudge away then up; staircase env."""
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
    g0, s0 = g, sprite(g)
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g, 0, 0
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
    print(f"{tag}x{x0} Δ=({dx},{dy}) cy={s1['body']['cy'] if s1 else None} nd={body_ndiff(g0,g2)}")
    return d2, g2, dx, dy


def above_map(g, label):
    sp = sprite(g)
    b = sp["body"]
    print(f"-- {label} body={b} acc={sp['accent']}")
    for y in range(max(1, b["y0"] - 8), b["y0"] + 1):
        row = [int(g[y, x]) for x in range(b["x0"] - 2, b["x1"] + 3)]
        print(f"  y{y}: {row}")


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g, _, _ = pad(sess, d, g, 15, "s ")
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        d, g, _, _ = pad(sess, d, g, 39, "hz ")

        for i in range(5):
            above_map(g, f"pre-up{i}")
            d, g, dx, dy = pad(sess, d, g, 15, f"up{i} ")
            if abs(dy) < 0.1:
                above_map(g, "AT CEILING")
                # occupancy of would-be landing
                b = sprite(g)["body"]
                print("would-be body cells after -3y:")
                for y in range(b["y0"] - 3, b["y0"]):
                    for x in range(b["x0"], b["x1"] + 1):
                        print(f"  ({x},{y})={int(g[y,x])}", end="")
                    print()
                break

        # Hypothesis: mid window blocks via row occupancy — temporarily
        # go down, env to change something, climb with different floor phase
        print("\nPhase env at cy45 then climb")
        d, g, _, _ = pad(sess, d, g, 9, "dn ")
        for e in (39, 45, 51, 57):
            d, g, _, _ = pad(sess, d, g, e, f"e{e} ")
            # check if any cell in x18-26 y37-45 became 0
            zeros = [(x, y) for y in range(37, 46) for x in range(18, 27) if int(g[y, x]) == 0]
            print(f"  after env{e} zeros in climb box: {zeros[:20]} n={len(zeros)}")
        for i in range(4):
            d, g, dx, dy = pad(sess, d, g, 15, f"climb{i} ")
            if abs(dy) < 0.1:
                print("still ceiling", sprite(g))
                break
            if sprite(g)["body"]["cy"] < 41.5:
                print("BROKE", sprite(g))
                break

        # Try: from bay1 floor with c12, do NOT climb — instead click cells
        # between sprite and mid at y51-54 to extend color0 up? 
        print("\nFresh: hop keep c12, paint toward mid at floor")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g, _, _ = pad(sess, d, g, 15, "s2 ")
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        d, g, _, _ = pad(sess, d, g, 39, "hz2 ")
        print("floor map y45-54 x20-32")
        for y in range(45, 55):
            print(y, [int(g[y, x]) for x in range(20, 33)])
        # click right edge of color0 toward mid
        for x, y in [(24, 52), (25, 52), (26, 52), (26, 51), (26, 50), (26, 49)]:
            if 0 <= x < 64 and int(g[y, x]) == 0:
                g0 = g
                d2 = click(sess, x, y)
                if d2:
                    g2 = plane(d2["frame"])
                    if body_ndiff(g0, g2):
                        print(f"click({x},{y}) ch={body_changes(g0,g2)}")
                        g = g2; d = d2
    finally:
        sess.close()


if __name__ == "__main__":
    main()
