"""L4: after pad39 hop (charge spent, c12 lit), click mid / climb one / etc."""
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
    print(f"{tag}x{x0} Δ=({dx},{dy}) cy={s1['body']['cy'] if s1 else None} h12={int((g2==12).sum())} lv={d2.get('levels_completed')}")
    return d2, g2, dx, dy


def try_click(sess, d, g, x, y, tag=""):
    g0, s0 = g, sprite(g)
    d2 = click(sess, x, y)
    if d2 is None:
        return d, g
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    nd = body_ndiff(g0, g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
    if nd or abs(dx) + abs(dy) > 0.1:
        print(f"{tag}({x},{y}) nd={nd} Δ=({dx},{dy}) ch={body_changes(g0,g2)} h12={int((g2==12).sum())}")
    else:
        print(f"{tag}({x},{y}) noop")
    return d2, g2


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
        print("post-pad-hop c12", components(g, 12, 1, 80), sprite(g))

        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]
        # click mid without rearm
        d, g = try_click(sess, d, g, round(mid["cx"]), round(mid["cy"]), "mid")
        # click various mid cells
        for y in (34, 40, 45):
            d, g = try_click(sess, d, g, mid["x0"], y, "midedge")
        # click color0 east of mid
        d, g = try_click(sess, d, g, 30, 53, "c0east")
        # env should NOT hop if charge spent
        d, g, dx, dy = pad(sess, d, g, 45, "env ")
        print("env dx", dx, "still", sprite(g))

        # Now: climb to ceiling with careful check if mid converts when
        # left c12 dies on same frame as arriving? 
        for i in range(5):
            d, g, _, dy = pad(sess, d, g, 15, f"up{i} ")
            mid12 = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
            print(f"  h12={int((g==12).sum())} mid12={mid12} cy={sprite(g)['body']['cy']}")
            if mid12:
                print("MID!")
                break
            if abs(dy) < 0.1:
                break

        # At ceiling: re-get c12 by going to 51, but use pad hop back?
        # Instead from ceiling go to 51, c12 on, DON'T click arm — just exist
        while sprite(g)["body"]["cy"] < 50.5:
            d, g, _, dy = pad(sess, d, g, 9, "to51 ")
            if abs(dy) < 0.1:
                break
        print("at51", sprite(g), "c12", components(g, 12, 1, 80))
        # click mid while c12 auto-on without arming
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
        if mid:
            d, g = try_click(sess, d, g, round(mid[0]["cx"]), round(mid[0]["cy"]), "mid@51")
        print("final", summarize(g), "lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
