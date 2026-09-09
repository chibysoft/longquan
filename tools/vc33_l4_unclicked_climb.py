"""L4: with c12 active but NOT clicked, climb in left bay; also multi-click gate."""
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


def dump(g, y0=28, y1=56, x0=0, x1=50):
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
        f"{tag}x{x0} Δ=({dx},{dy}) cx={s1['body']['cx'] if s1 else None} "
        f"cy={s1['body']['cy'] if s1 else None} h12={int((g2==12).sum())} "
        f"ch={body_changes(g0,g2)} lv={d2.get('levels_completed')}"
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
        print("c12 on, NO click yet")
        dump(g)
        # climb with pad9 (up) while c12 lit
        for i in range(8):
            d, g, dx, dy = pad(sess, d, g, 9, tag=f"up{i} ")
            if int((g == 12).sum()) == 0:
                print("c12 died")
            if abs(dy) < 0.1 and abs(dx) < 0.1:
                print("stuck climb")
                break
            if abs(dx) > 0.1:
                print("unexpected hz while unclicked")
                dump(g)
                break
        print("after climb attempt", sprite(g), "h12", int((g == 12).sum()))
        dump(g)

        # if c12 still or re-sink
        if int((g == 12).sum()) == 0:
            while int((g == 12).sum()) == 0:
                d, g, _, dy = pad(sess, d, g, 15, tag="resink ")
                if abs(dy) < 0.1:
                    d, g, _, _ = pad(sess, d, g, 9, tag="alt ")
                    break

        if int((g == 12).sum()):
            c = components(g, 12, 1, 80)[0]
            # multi click gate
            for i in range(3):
                g0 = g
                d2 = click(sess, round(c["cx"]), round(c["cy"]))
                if d2 is None:
                    break
                g = plane(d2["frame"]); d = d2
                print(f"gate click{i} nd={body_ndiff(g0,g)} ch={body_changes(g0,g)}")
            # now hop with pad15 (high) 
            d, g, dx, dy = pad(sess, d, g, 15, tag="hihop ")
            dump(g)
            print("final", summarize(g))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
