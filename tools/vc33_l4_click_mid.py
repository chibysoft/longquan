"""L4: from bay1 via gate-hop, click mid/beam/gap cells; climb+click."""
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
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g, 0, 0
    g2 = plane(d2["frame"])
    s0, s1 = sprite(g), sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
    print(f"{tag}pad{x0} Δ=({dx},{dy}) cy={s1['body']['cy'] if s1 else None} h12={int((g2==12).sum())}")
    return d2, g2, dx, dy


def try_xy(sess, d, g, x, y, tag=""):
    g0, s0 = g, sprite(g)
    d2 = click(sess, x, y)
    if d2 is None:
        return d, g, False
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
    nd = body_ndiff(g0, g2)
    if nd or abs(dx) + abs(dy) > 0.1:
        print(f"{tag}({x},{y}) nd={nd} Δ=({dx},{dy}) ch={body_changes(g0,g2)} "
              f"h12={int((g2==12).sum())} lv={d2.get('levels_completed')}")
        return d2, g2, True
    return d2, g2, False


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
        # arm
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        # hop via second gate click
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        print("bay1 via gate-hop", sprite(g), "c12", components(g, 12, 1, 80))

        # click mid cells, beam, between
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]
        targets = []
        for y in range(mid["y0"], mid["y1"] + 1, 2):
            targets.append((mid["cx"], y, "mid"))
            targets.append((mid["x0"] - 1, y, "left"))
            targets.append((mid["x1"] + 1, y, "right"))
        targets += [(25, 42, "gap"), (25, 45, "gap"), (25, 46, "gap"), (43, 29, "goal"),
                    (28, 46, "beam"), (20, 42, "selfish")]
        for x, y, tag in targets:
            d, g, hit = try_xy(sess, d, g, int(x), int(y), tag=tag)
            if hit and abs((sprite(g) or {}).get("body", {}).get("cx", 0) - 20.5) > 1:
                print("moved away")
            if int(d.get("levels_completed") or 0) >= 4:
                print("CLEAR"); return

        # climb to ceiling clicking mid each step
        for i in range(5):
            d, g, dx, dy = pad(sess, d, g, 15, f"up{i}")
            mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
            if mid:
                d, g, hit = try_xy(sess, d, g, int(mid[0]["cx"]), int(mid[0]["cy"]), tag=f"m{i}")
            if any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("MID12"); break
            if abs(dy) < 0.1:
                break

        print("final", summarize(g), "lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
