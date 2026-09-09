"""L4: env staircase on x>=30 — how high can color0 climb toward gap y29?"""
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
from tools.vc33_l4_pad_map import components, enter_l4, gap11, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_env_stair.json"
CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 11: "A", 12: "C"}


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


def east_profile(g):
    out = {}
    for x in range(30, 48):
        ys = [int(y) for y in range(20, 56) if int(g[y, x]) == 0]
        if ys:
            out[x] = {"ymin": min(ys), "ymax": max(ys), "n": len(ys)}
    return out


def dump_east(g, y0=25, y1=55):
    for y in range(y0, y1 + 1):
        row = "".join(CHARS.get(int(g[y, x]), str(int(g[y, x]))[-1]) for x in range(26, 50))
        print(f"{y:02d}|{row}")


def main():
    key = _api_key()
    sess = Sess(key)
    log = []
    try:
        sess.open()
        # A: from enter, env spam without hop — east profile
        print("\n==== A enter env stair")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        print("enter", east_profile(g))
        dump_east(g)
        for i, e in enumerate([39, 45, 51, 57] * 6):
            d, g = pad(sess, d, g, e)
            ep = east_profile(g)
            ymin = min((v["ymin"] for v in ep.values()), default=None)
            if i % 4 == 3 or (ymin is not None and ymin < 45):
                print(f"after {i} env ymin={ymin} ep={ {k:v for k,v in ep.items() if v['ymin']<50} }")
                log.append({"i": i, "ymin": ymin, "ep": ep})
        print("A final")
        dump_east(g, 28, 52)
        gp = gap11(g)
        print("gap", gp, "lv", d.get("levels_completed"))

        # B: bay1 floor + ceil env
        print("\n==== B bay1 env stair")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g = pad(sess, d, g, 15)
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        d, g = pad(sess, d, g, 39)
        for i, e in enumerate([39, 45, 51, 57] * 5):
            d, g = pad(sess, d, g, e)
        ep = east_profile(g)
        ymin = min((v["ymin"] for v in ep.values()), default=None)
        print("bay1 floor ymin", ymin, ep)
        dump_east(g, 28, 55)
        # climb + env
        for _ in range(4):
            d, g = pad(sess, d, g, 15)
            if sprite(g)["body"]["cy"] <= 42.5:
                # check if blocked
                g0 = g
                d, g = pad(sess, d, g, 15)
                if abs(sprite(g)["body"]["cy"] - sprite(g0)["body"]["cy"]) < 0.1:
                    break
            for e in (39, 45, 51):
                d, g = pad(sess, d, g, e)
        ep = east_profile(g)
        ymin = min((v["ymin"] for v in ep.values()), default=None)
        print("bay1 ceil ymin", ymin)
        dump_east(g, 25, 50)
        print("gap", gap11(g), "sprite", sprite(g), "lv", d.get("levels_completed"))

        # try click gap and any color0 near gap
        gp = gap11(g)
        if gp:
            d2 = click(sess, round(gp["cx"]), round(gp["cy"]))
            if d2:
                print("gap click lv", d2.get("levels_completed"))
                g = plane(d2["frame"]); d = d2
        # color0 cells with y<40 x>=30
        highs = [(int(x), int(y)) for y, x in np.argwhere(g == 0) if y < 40 and x >= 30]
        print("high zeros", highs[:20], "n", len(highs))
        for x, y in highs[:5]:
            d2 = click(sess, x, y)
            if d2 and d2.get("levels_completed", 0) >= 4:
                print("CLEAR via high0")
                break

        OUT.write_text(json.dumps({"log": log, "final_lv": d.get("levels_completed"),
                                    "final_ymin": ymin, "high_zeros_n": len(highs)}, indent=2), encoding="utf-8")
        print("done lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
