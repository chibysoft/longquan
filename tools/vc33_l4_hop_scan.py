"""L4: compare color0 vs mid after each hop type; try convert on down-into-overlap."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_changes  # noqa: E402
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
    g0 = g
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g, 0, 0
    g2 = plane(d2["frame"])
    s0, s1 = sprite(g0), sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
    print(f"{tag}x{x0} Δ=({dx},{dy}) cy={s1['body']['cy'] if s1 else None} h12={int((g2==12).sum())}")
    return d2, g2, dx, dy


def mid_gap_scan(g, label):
    mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
    mid12 = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
    m = (mid or mid12 or [None])[0]
    print(f"== {label} mid={m} converted={bool(mid12)}")
    if not m:
        return
    for y in range(m["y0"], min(63, m["y1"] + 3)):
        cells = [int(g[y, x]) for x in range(m["x0"] - 4, m["x1"] + 3)]
        print(f"  y{y}: {cells}  # x{m['x0']-4}..")
    # exact cells of interest
    for x, y in [(24, 45), (25, 45), (26, 45), (26, 46), (27, 45), (27, 46)]:
        print(f"  ({x},{y})={int(g[y, x])}")


def to_armed(sess):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        d, g, _, _ = pad(sess, d, g, 15, "s ")
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    return d2, plane(d2["frame"]), c


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        for hop_pad in (39, 15, 9):
            print(f"\n##### HOP {hop_pad}")
            d, g, c = to_armed(sess)
            d, g, _, _ = pad(sess, d, g, hop_pad, "hop ")
            mid_gap_scan(g, f"after hop{hop_pad}")
            # climb until ceiling, scan each step
            for i in range(6):
                d, g, dx, dy = pad(sess, d, g, 15, f"up{i} ")
                mid_gap_scan(g, f"hop{hop_pad} up{i}")
                if any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                    print("MID CONVERTED during climb")
                    break
                if abs(dy) < 0.1:
                    # one down and scan (catch-up theory)
                    d, g, _, _ = pad(sess, d, g, 9, "dn ")
                    mid_gap_scan(g, "after dn from ceiling")
                    break

        # Special: left convert moment — scan left window with same printer
        print("\n##### LEFT CONVERT REF")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        d, g, _, _ = pad(sess, d, g, 15, "d1 ")
        left = [c for c in components(g, 1, 4, 80) if c["cx"] < 20][0]
        print("before left", left)
        for y in range(left["y0"], left["y1"] + 1):
            cells = [int(g[y, x]) for x in range(left["x0"] - 4, left["x1"] + 3)]
            print(f"  y{y}: {cells}")
        d, g, _, _ = pad(sess, d, g, 15, "d2 ")
        print("after convert h12", int((g == 12).sum()), sprite(g))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
