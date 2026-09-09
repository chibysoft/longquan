"""L4: track sprite after each gate click; maybe pulls into window."""
from __future__ import annotations

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_changes, body_ndiff  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, sprite, summarize  # noqa: E402

CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 11: "A", 12: "C"}


def dump(g, y0=40, y1=56, x0=0, x1=35):
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
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g
    return d2, plane(d2["frame"])


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g = pad(sess, d, g, 15, "s")
        print("start c12", sprite(g))
        dump(g)
        c = components(g, 12, 1, 80)[0]
        for i in range(5):
            g0 = g
            s0 = sprite(g0)
            d2 = click(sess, round(c["cx"]), round(c["cy"]))
            if d2 is None:
                break
            g = plane(d2["frame"]); d = d2
            s1 = sprite(g)
            dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
            dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
            print(f"gate{i} nd={body_ndiff(g0,g)} Δ=({dx},{dy}) sp={s1} ch={body_changes(g0,g)} lv={d.get('levels_completed')}")
            dump(g)
            if abs(dx) + abs(dy) > 0.1:
                print("SPRITE MOVED ON GATE CLICK")
            # refresh c in case
            c12 = components(g, 12, 1, 80)
            if not c12:
                print("c12 gone")
                break
            c = c12[0]
        # after toggles, try hop
        d, g = pad(sess, d, g, 39, "hz")
        print("after hz", sprite(g), summarize(g)["c1"])
        dump(g)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
