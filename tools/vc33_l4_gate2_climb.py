"""L4: bay1 with c12 — click gate then climb (no env); also try gap click; pad15 land+climb flood."""
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


def dump(g, y0=28, y1=56, x0=0, x1=63):
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
        f"lv={d2.get('levels_completed')}"
    )
    return d2, g2, dx, dy


def arm_and_hz(sess, hop_pad=39):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        d, g, _, _ = pad(sess, d, g, 15, tag="sink ")
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"]); d = d2
    d, g, dx, _ = pad(sess, d, g, hop_pad, tag="hz ")
    return d, g


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        # 1) pad39 hop keep c12, click gate again, climb with 15
        print("==== gate2 then climb")
        d, g = arm_and_hz(sess, 39)
        print("before gate2", sprite(g), "h12", int((g == 12).sum()))
        c = [c for c in components(g, 12, 1, 80) if c["cx"] < 20]
        if c:
            d2 = click(sess, round(c[0]["cx"]), round(c[0]["cy"]))
            g = plane(d2["frame"]); d = d2
            print("gate2 ch done", sprite(g), "h12", int((g == 12).sum()))
        # climb WITHOUT env pads
        for i in range(6):
            d, g, dx, dy = pad(sess, d, g, 15, tag=f"climb{i} ")
            if abs(dx) > 0.1:
                print("climbed with hz!", dx); dump(g)
            if any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("MID"); dump(g); break
            if abs(dy) < 0.1 and abs(dx) < 0.1:
                print("ceiling"); dump(g); break

        # 2) fresh: hop with pad15 (high), climb, dump full width
        print("\n==== high hop climb")
        d, g = arm_and_hz(sess, 15)
        dump(g)
        for i in range(5):
            d, g, dx, dy = pad(sess, d, g, 15, tag=f"hup{i} ")
            dump(g, 34, 52, 10, 50)
            if any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("MID"); break
            if abs(dy) < 0.1:
                break
        # click gap
        gp = summarize(g)["gap"]
        if gp:
            d2 = click(sess, round(gp["cx"]), round(gp["cy"]))
            if d2:
                g2 = plane(d2["frame"])
                print("gap click", body_ndiff(g, g2), body_changes(g, g2), d2.get("levels_completed"))
                g = g2; d = d2
        # click mid c1 while adjacent
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
        if mid:
            for y in range(mid[0]["y0"], mid[0]["y1"] + 1):
                d2 = click(sess, mid[0]["x0"] - 1, y)
                if d2:
                    g2 = plane(d2["frame"])
                    if body_ndiff(g, g2):
                        print(f"edge click ({mid[0]['x0']-1},{y})", body_changes(g, g2))
                        g = g2; d = d2
                        break

        print("final", summarize(g), "lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
