"""L4: deep sink in bay1 then full climb; watch gap cols x24-26 for 0 in mid y."""
from __future__ import annotations

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
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
    return d2, g2, dx, dy


def gap0(g):
    # color0 in x24-26 within mid y 34-45
    cells = []
    for x in (24, 25, 26):
        for y in range(34, 46):
            if int(g[y, x]) == 0:
                cells.append((x, y))
    return cells


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
        # go deep
        for i in range(8):
            d, g, dx, dy = pad(sess, d, g, 9, "dn")
            print(f"dn{i} cy={sprite(g)['body']['cy']} dy={dy} gap0={gap0(g)}")
            if abs(dy) < 0.1:
                break
        # climb all the way watching gap0
        for i in range(20):
            d, g, dx, dy = pad(sess, d, g, 15, "up")
            sp = sprite(g)
            g0 = gap0(g)
            mid12 = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
            print(f"up{i} cy={sp['body']['cy']} acc={sp['accent']['y0']}-{sp['accent']['y1']} gap0={g0} mid12={bool(mid12)} lv={d.get('levels_completed')}")
            if mid12:
                print("MID!", mid12)
                d2 = click(sess, round(mid12[0]["cx"]), round(mid12[0]["cy"]))
                g = plane(d2["frame"]); d = d2
                for e in (39, 45, 51, 57, 9, 15):
                    d, g, dx, dy = pad(sess, d, g, e, "h2")
                    print(f"  h2 x{e} Δ=({dx},{dy}) {sprite(g)}")
                    if abs(dx) > 0.1:
                        break
                break
            if abs(dy) < 0.1:
                # at ceiling — try env interleaved once
                for e in (39, 45):
                    d, g, _, _ = pad(sess, d, g, e, "e")
                    print(f"  env{e} gap0={gap0(g)}")
                d, g, dx, dy = pad(sess, d, g, 15, "retry")
                if abs(dy) < 0.1:
                    print("hard ceiling", summarize(g))
                    break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
