"""L4: at bay1 climb ceiling, re-arm gate / click mid / hunt +x."""
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

CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 7: "U", 9: "P", 11: "A", 12: "C"}


def dump(g, y0=28, y1=56, x0=0, x1=55):
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
    xy = (int(round(p["cx"])), int(round(p["cy"])))
    g0, s0 = g, sprite(g)
    d2 = click(sess, *xy)
    if d2 is None:
        return d, g, 0.0, 0.0
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0.0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0.0
    print(
        f"{tag}x{x0} nd={body_ndiff(g0,g2)} Δ=({dx},{dy}) "
        f"cx={s1['body']['cx'] if s1 else None} cy={s1['body']['cy'] if s1 else None} "
        f"h1={int((g2==1).sum())} h12={int((g2==12).sum())} lv={d2.get('levels_completed')} al={summarize(g2)['aligned']}"
    )
    return d2, g2, dx, dy


def xy_click(sess, d, g, x, y, tag=""):
    g0 = g
    d2 = click(sess, x, y)
    if d2 is None:
        return d, g
    g2 = plane(d2["frame"])
    s0, s1 = sprite(g0), sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
    print(f"{tag}({x},{y}) nd={body_ndiff(g0,g2)} Δ=({dx},{dy}) ch={body_changes(g0,g2)} lv={d2.get('levels_completed')}")
    return d2, g2


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g, _, _ = pad(sess, d, g, 15, tag="sink ")
        # click left gate
        c = components(g, 12, 1, 80)[0]
        d, g = xy_click(sess, d, g, round(c["cx"]), round(c["cy"]), tag="Lgate")
        d, g, dx, _ = pad(sess, d, g, 39, tag="hz ")
        assert abs(dx) > 1

        # climb to ceiling with pad15
        for i in range(6):
            d, g, dx, dy = pad(sess, d, g, 15, tag=f"up{i} ")
            if abs(dy) < 0.1:
                print("ceiling")
                break

        print("\nAT CEILING")
        dump(g)
        print("c1", components(g, 1, 4, 80))
        print("c12", components(g, 12, 1, 80))

        # click mid c1
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]
        d, g = xy_click(sess, d, g, round(mid["cx"]), round(mid["cy"]), tag="mid1")
        # click between
        d, g = xy_click(sess, d, g, 25, 42, tag="between")
        d, g = xy_click(sess, d, g, 25, 44, tag="between2")

        # toggle for c12
        print("\nTOGGLE")
        d, g, _, _ = pad(sess, d, g, 9, tag="dn ")
        print("c12", components(g, 12, 1, 80))
        d, g, _, _ = pad(sess, d, g, 15, tag="up ")
        print("c12", components(g, 12, 1, 80))
        d, g, _, _ = pad(sess, d, g, 9, tag="dn2 ")
        print("c12", components(g, 12, 1, 80))
        # more downs to floor?
        for i in range(4):
            d, g, _, dy = pad(sess, d, g, 9, tag=f"dn{i} ")
            print("  c12", components(g, 12, 1, 80), "c1n", len(components(g, 1, 4, 80)))
            if abs(dy) < 0.1:
                break

        print("\nAT LOWER")
        dump(g)
        # if c12, click and try +x; also try click mid if c12 mid
        for c in components(g, 12, 1, 80):
            d, g = xy_click(sess, d, g, round(c["cx"]), round(c["cy"]), tag=f"gate{c['cx']:.0f}")
        for x0 in (39, 45, 51, 57, 9, 15):
            d, g, dx, dy = pad(sess, d, g, x0, tag="hunt ")
            if abs(dx) > 0.1:
                print("HZ!", dx)
                dump(g)
                break

        # climb again with gate armed if possible
        print("\nRECLIMB+ARM")
        # ensure at floor bay1 with left c12
        # if not c12, go to left bay and rearm?
        sp = sprite(g)
        if sp and sp["body"]["cx"] > 15 and int((g == 12).sum()) == 0:
            # try go left via reverse gate — click left c1? or pad after something
            left1 = [c for c in components(g, 1, 4, 80) if c["cx"] < 20]
            print("left1", left1)
            if left1:
                # sink/overlap to convert left again
                for i in range(3):
                    d, g, _, _ = pad(sess, d, g, 9, tag="sinkL ")
                    if int((g == 12).sum()):
                        break
                    d, g, _, _ = pad(sess, d, g, 15, tag="alt ")
                    if int((g == 12).sum()):
                        break

        print("state", summarize(g))
        print("c12", components(g, 12, 1, 80))
        dump(g)

        # From bay1 floor: click left c12 if any, but try climbing ONE step less and +x?
        # Fresh strategy in same session if still alive: 
        # go left (-x) by clicking left gate + pad39 reverse
        if any(c["cx"] < 20 for c in components(g, 12, 1, 80)):
            c = [c for c in components(g, 12, 1, 80) if c["cx"] < 20][0]
            d, g = xy_click(sess, d, g, round(c["cx"]), round(c["cy"]), tag="L2")
            d, g, dx, _ = pad(sess, d, g, 39, tag="maybe_back ")
            print("after maybe", sprite(g))

        # New: climb only 2 ups from bay1 floor with gate, then try +x with gate still?
        # Re-setup if on left
        sp = sprite(g)
        if sp and sp["body"]["cx"] < 12:
            while int((g == 12).sum()) == 0:
                d, g, _, _ = pad(sess, d, g, 15, tag="resink ")
            c = components(g, 12, 1, 80)[0]
            d, g = xy_click(sess, d, g, round(c["cx"]), round(c["cy"]), tag="L3")
            d, g, _, _ = pad(sess, d, g, 39, tag="hz2 ")
            print("bay1 again", sprite(g), "h12", int((g == 12).sum()))
            # only 2 ups
            d, g, _, _ = pad(sess, d, g, 15, tag="u1 ")
            print("after1up h12", int((g == 12).sum()), sprite(g))
            d, g, _, _ = pad(sess, d, g, 15, tag="u2 ")
            print("after2up h12", int((g == 12).sum()), sprite(g))
            # rearm if needed
            if int((g == 12).sum()) == 0:
                d, g, _, _ = pad(sess, d, g, 9, tag="bounce ")
                d, g, _, _ = pad(sess, d, g, 15, tag="rearm ")
                print("rearm h12", components(g, 12, 1, 80))
            for c in components(g, 12, 1, 80):
                d, g = xy_click(sess, d, g, round(c["cx"]), round(c["cy"]), tag="arm")
            for x0 in (39, 45, 51, 57):
                d, g, dx, dy = pad(sess, d, g, x0, tag="midhz ")
                if abs(dx) > 0.1:
                    print("MID HZ", dx)
                    dump(g)
                    break
            print("final", summarize(g))
            dump(g)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
