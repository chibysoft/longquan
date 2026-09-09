"""L4: can gap11 become 12 / other morph? exhaustive short seq at ceil for levels."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_ndiff  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, gap11, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_gap_morph.json"


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


def gap_colors(g):
    gp = gap11(g)
    if not gp:
        # search any 11/12/14/15 in right beam area
        cells = []
        for y in range(25, 35):
            for x in range(40, 50):
                c = int(g[y, x])
                if c not in (0, 3, 5):
                    cells.append((x, y, c))
        return {"gap11": None, "odd": cells}
    cols = {}
    for y in range(gp["y0"], gp["y1"] + 1):
        for x in range(gp["x0"], gp["x1"] + 1):
            cols[(x, y)] = int(g[y, x])
    return {"gap11": gp, "cells": cols, "n12_near": int(np.sum(g[25:35, 40:50] == 12))}


def setup_ceil(sess):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        d, g = pad(sess, d, g, 15)
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"]); d = d2
    d, g = pad(sess, d, g, 39)
    for _ in range(5):
        g0 = g
        d, g = pad(sess, d, g, 15)
        if abs(sprite(g)["body"]["cy"] - sprite(g0)["body"]["cy"]) < 0.1:
            break
    return d, g


def main():
    key = _api_key()
    sess = Sess(key)
    log = []
    try:
        sess.open()
        d, g = setup_ceil(sess)
        print("ceil gap", gap_colors(g), "lv", d.get("levels_completed"))
        log.append({"tag": "ceil", **gap_colors(g), "lv": d.get("levels_completed")})

        # A: env then recheck gap
        for e in (39, 45, 51, 57) * 3:
            d, g = pad(sess, d, g, e)
        print("after env", gap_colors(g))
        log.append({"tag": "env", **gap_colors(g)})

        # B: click every gap cell + neighbors
        gp = gap11(g)
        if gp:
            for y in range(gp["y0"] - 2, gp["y1"] + 3):
                for x in range(gp["x0"] - 2, gp["x1"] + 3):
                    if not (0 <= x < 64 and 0 <= y < 64):
                        continue
                    g0 = g
                    d2 = click(sess, x, y)
                    if d2 is None:
                        break
                    g2 = plane(d2["frame"])
                    nd = body_ndiff(g0, g2)
                    gc = gap_colors(g2)
                    if nd or gc.get("n12_near") or d2.get("levels_completed") != d.get("levels_completed"):
                        print(f"gapclick({x},{y}) nd={nd} gap={gc} lv={d2.get('levels_completed')}")
                        log.append({"click": (x, y), "nd": nd, "gap": gc, "lv": d2.get("levels_completed")})
                    g = g2; d = d2
                    if int(d.get("levels_completed") or 0) >= 4:
                        print("CLEAR")
                        (ROOT / "tests/fixtures/vc33_l4_clear_frame.json").write_text(
                            json.dumps({"frame": d["frame"], "levels": d.get("levels_completed")}, indent=2),
                            encoding="utf-8",
                        )
                        return

        # C: short program search from ceil — sequences of length 3 from {9,15,39,45,mid,gap}
        print("\n==== C seq search len3")
        def mid_xy(g):
            m = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
            return (round(m[0]["cx"]), round(m[0]["cy"])) if m else None

        def gap_xy(g):
            gp = gap11(g)
            return (round(gp["cx"]), round(gp["cy"])) if gp else None

        ops = ["9", "15", "39", "45", "mid", "gap"]
        # fresh ceil each batch of 8 to limit enters
        tested = 0
        for a in ops:
            for b in ops:
                for c in ops:
                    if tested % 20 == 0:
                        d, g = setup_ceil(sess)
                    def do(op):
                        nonlocal d, g
                        if op in ("9", "15", "39", "45", "51", "57"):
                            d, g = pad(sess, d, g, int(op))
                        elif op == "mid":
                            xy = mid_xy(g)
                            if xy:
                                d2 = click(sess, *xy)
                                if d2:
                                    g = plane(d2["frame"]); d = d2
                        elif op == "gap":
                            xy = gap_xy(g)
                            if xy:
                                d2 = click(sess, *xy)
                                if d2:
                                    g = plane(d2["frame"]); d = d2
                        return d.get("levels_completed"), bool([x for x in components(g, 12, 1, 80) if x["cx"] > 20])
                    for op in (a, b, c):
                        lv, mid12 = do(op)
                        if int(lv or 0) >= 4 or mid12:
                            print("HIT seq", a, b, c, "lv", lv, "mid12", mid12)
                            log.append({"hit": (a, b, c), "lv": lv, "mid12": mid12})
                            if int(lv or 0) >= 4:
                                return
                    tested += 1
                    # restore toward ceil cheaply
                    sp = sprite(g)
                    if sp and sp["body"]["cy"] > 43:
                        d, g = pad(sess, d, g, 15)
                    if sp and sp["body"]["cx"] < 15:
                        # hopped west — need reenter soon
                        if tested % 5 == 0:
                            d, g = setup_ceil(sess)

        OUT.write_text(json.dumps({"log": log[-50:], "tested": tested, "final_lv": d.get("levels_completed")}, indent=2, default=str), encoding="utf-8")
        print("done tested", tested, "lv", d.get("levels_completed"), "hits", [x for x in log if "hit" in x])
    finally:
        sess.close()


if __name__ == "__main__":
    main()
