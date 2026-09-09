"""L4: at bay1 cy=51 with c12, gate then each env for +x direction."""
from __future__ import annotations

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_ndiff  # noqa: E402
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
        f"h12={int((g2==12).sum())} lv={d2.get('levels_completed')} al={summarize(g2)['aligned']}"
    )
    return d2, g2, dx, dy


def setup_bay1_c12(sess):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        d, g, _, _ = pad(sess, d, g, 15, tag="sink ")
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"])
    d = d2
    d, g, dx, _ = pad(sess, d, g, 39, tag="hz1 ")
    assert abs(dx) > 1
    # ensure cy=51 and c12 — if climb happened no; we stay at floor
    # if h12 lost, descend/ascend to rearm
    for _ in range(4):
        if int((g == 12).sum()) > 0 and abs(sprite(g)["body"]["cy"] - 51) < 1:
            break
        # adjust y toward 51
        cy = sprite(g)["body"]["cy"]
        if cy < 50:
            d, g, _, _ = pad(sess, d, g, 9, tag="to51 ")
        elif cy > 52:
            d, g, _, _ = pad(sess, d, g, 15, tag="to51 ")
        else:
            break
    print("setup", sprite(g), "h12", int((g == 12).sum()), "c12", components(g, 12, 1, 80))
    return d, g


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        for env in (45, 51, 57, 39):
            print(f"\n==== try gate + pad{env}")
            d, g = setup_bay1_c12(sess)
            if int((g == 12).sum()) == 0:
                print("no c12, skip")
                continue
            c = [c for c in components(g, 12, 1, 80) if c["cx"] < 20][0]
            d2 = click(sess, round(c["cx"]), round(c["cy"]))
            if d2 is None:
                break
            g = plane(d2["frame"])
            d = d2
            print("gated", int((g == 12).sum()))
            d, g, dx, dy = pad(sess, d, g, env, tag="try ")
            print("result cx", sprite(g)["body"]["cx"] if sprite(g) else None)
            if abs(dx) > 0.1:
                print("MOVE", dx)
                # continue toward gap if +x
                if dx > 0:
                    print("FORWARD success path")
                    for i in range(20):
                        sm = summarize(g)
                        print(f"go{i}", sm["sprite"], sm["aligned"], d.get("levels_completed"))
                        if sm["aligned"] or int(d.get("levels_completed") or 0) >= 4:
                            print("CLEAR", d.get("levels_completed"))
                            break
                        # climb with whichever goes up
                        moved = False
                        for x0 in (15, 9, 39, 45, 51, 57):
                            d, g, dx2, dy2 = pad(sess, d, g, x0, tag="nav ")
                            if abs(dx2) + abs(dy2) > 0.1:
                                moved = True
                                if sm["gap"] and sprite(g):
                                    pass
                                break
                        if not moved:
                            break
                    break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
