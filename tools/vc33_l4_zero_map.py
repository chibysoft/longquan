"""L4: exact color0 cells at y<=45 after hop / each climb step in bay1."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_zero_map.json"
CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 11: "A", 12: "C"}


def dump(g, y0=40, y1=55, x0=0, x1=45):
    for y in range(y0, y1 + 1):
        row = "".join(CHARS.get(int(g[y, x]), str(int(g[y, x]))[-1]) for x in range(x0, x1 + 1))
        print(f"{y:02d}|{row}")


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad(sess, d, g, x0):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g
    return d2, plane(d2["frame"])


def zeros_le(g, ymax=45):
    cells = [(int(x), int(y)) for y, x in np.argwhere(g == 0) if y <= ymax]
    cells.sort(key=lambda t: (t[1], t[0]))
    return cells


def report(tag, g):
    z = zeros_le(g, 45)
    z46 = [(int(x), int(y)) for y, x in np.argwhere(g == 0) if y == 46]
    mid12 = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
    sp = sprite(g)
    print(f"\n[{tag}] cy={sp['body']['cy'] if sp else None} h12={int((g==12).sum())} mid12={bool(mid12)}")
    print(f"  zeros y<=45 (n={len(z)}): {z}")
    print(f"  zeros y==46: {z46}")
    print(f"  x24-26 @44-46: { {(x,y): int(g[y,x]) for x in (24,25,26) for y in (44,45,46)} }")
    return {
        "tag": tag,
        "cy": sp["body"]["cy"] if sp else None,
        "zeros_le45": z,
        "zeros_y46": z46,
        "crit": {(f"{x},{y}"): int(g[y, x]) for x in (24, 25, 26) for y in (44, 45, 46)},
        "mid12": bool(mid12),
        "lv": None,
    }


def main():
    key = _api_key()
    sess = Sess(key)
    out = {"steps": []}
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        out["steps"].append(report("enter", g))

        while int((g == 12).sum()) == 0:
            d, g = pad(sess, d, g, 15)
        out["steps"].append(report("left_converted", g))
        dump(g, 43, 55, 0, 30)

        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        out["steps"].append(report("armed", g))

        d, g = pad(sess, d, g, 39)
        out["steps"].append(report("after_hop39", g))
        dump(g, 43, 55, 0, 45)
        out["steps"][-1]["lv"] = d.get("levels_completed")

        # also try: from fresh — hop then immediately check before any climb
        # climb step by step
        for i in range(5):
            g0 = g
            d, g = pad(sess, d, g, 15)
            # which new zeros at y<=45?
            old = set(zeros_le(g0, 45))
            new = set(zeros_le(g, 45))
            gained = sorted(new - old)
            lost = sorted(old - new)
            step = report(f"up{i}", g)
            step["gained_le45"] = gained
            step["lost_le45"] = lost
            step["lv"] = d.get("levels_completed")
            out["steps"].append(step)
            if gained or lost:
                print(f"  gained={gained} lost={lost}")
            if abs((sprite(g)["body"]["cy"] or 0) - (sprite(g0)["body"]["cy"] or 0)) < 0.1:
                break
            if any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("MID12!")
                break

        dump(g, 40, 50, 15, 35)

        # Fresh path: hop9 (diagonal) and map zeros
        print("\n==== hop9 path ====")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g = pad(sess, d, g, 15)
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        d, g = pad(sess, d, g, 9)
        out["steps"].append(report("after_hop9", g))
        dump(g, 43, 58, 0, 45)
        for i in range(6):
            g0 = g
            d, g = pad(sess, d, g, 15)
            step = report(f"h9up{i}", g)
            old, new = set(zeros_le(g0, 45)), set(zeros_le(g, 45))
            step["gained_le45"] = sorted(new - old)
            out["steps"].append(step)
            if step["gained_le45"]:
                print("  gained", step["gained_le45"])
            if abs(sprite(g)["body"]["cy"] - sprite(g0)["body"]["cy"]) < 0.1:
                break

        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print("wrote", OUT, "final_lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
