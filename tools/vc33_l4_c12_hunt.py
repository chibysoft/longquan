"""L4: after 2 downs (c1→12), dump + climb/env hunt + click c12."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_ndiff, body_changes  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import (  # noqa: E402
    components,
    enter_l4,
    gap11,
    sprite,
    summarize,
)

CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 7: "U", 9: "P", 11: "A", 12: "C"}


def dump(g, y0=28, y1=56, x0=0, x1=50):
    lines = []
    for y in range(y0, y1 + 1):
        row = "".join(CHARS.get(int(g[y, x]), str(int(g[y, x]))[-1]) for x in range(x0, x1 + 1))
        lines.append(f"{y:02d}|{row}")
        print(lines[-1])
    return lines


def click_x(sess, d, g, x0):
    pad = next(p for p in pads_sorted(g) if p["x0"] == x0)
    xy = (int(round(pad["cx"])), int(round(pad["cy"])))
    g0 = g
    s0 = sprite(g0)
    d = sess.click(*xy)
    g = plane(d["frame"])
    s1 = sprite(g)
    ddx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
    ddy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
    ch = body_changes(g0, g)
    diff = np.argwhere(g0[1:] != g[1:])
    bbox = None
    if len(diff):
        ys = diff[:, 0] + 1
        xs = diff[:, 1]
        bbox = (int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()))
    print(
        f"  pad{x0} body={body_ndiff(g0,g)} Δ=({ddx},{ddy}) bbox={bbox} "
        f"ch={ch} lv={d.get('levels_completed')} hist1={int((g==1).sum())} hist12={int((g==12).sum())}"
    )
    return d, g, ddx, ddy


def main():
    key = _api_key()
    sess = Sess(key)
    out = {}
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        print("START")
        dump(g)
        print("c1", components(g, 1, 4, 80))
        print("c12", components(g, 12, 1, 80))

        for i in range(2):
            d, g, _, _ = click_x(sess, d, g, 15)
        print("\nAFTER 2 DOWN")
        dump(g)
        print("c1", components(g, 1, 4, 80))
        print("c12", components(g, 12, 1, 80))
        print("sum", summarize(g))
        out["after_2_down"] = {
            "sum": summarize(g),
            "c1": components(g, 1, 4, 80),
            "c12": components(g, 12, 1, 80),
        }

        # click color12 center
        c12 = components(g, 12, 1, 80)
        if c12:
            c = c12[0]
            xy = (int(round(c["cx"])), int(round(c["cy"])))
            g0 = g
            d = sess.click(*xy)
            g2 = plane(d["frame"])
            print(f"\nclick c12 {xy} body={body_ndiff(g0,g2)} ch={body_changes(g0,g2)} lv={d.get('levels_completed')}")
            g = g2

        # env spam at bottom
        print("\nENV at bottom")
        for x0 in (39, 45, 51, 57, 39, 45, 51, 57):
            d, g, dx, dy = click_x(sess, d, g, x0)
            if abs(dx) + abs(dy) > 0.1:
                print("  MOVE!")
        print("c1", components(g, 1, 4, 80))
        print("c12", components(g, 12, 1, 80))
        dump(g, 40, 56, 0, 50)

        # climb with env alternate
        print("\nCLIMB with env")
        for i in range(20):
            s0 = sprite(g)
            d, g, dx, dy = click_x(sess, d, g, 9)
            s1 = sprite(g)
            if abs(dy) < 0.1:
                print(f" stuck at step {i}, try envs")
                moved = False
                for e in (39, 45, 51, 57, 15):
                    d, g, _, _ = click_x(sess, d, g, e)
                    d, g, dx2, dy2 = click_x(sess, d, g, 9)
                    if abs(dy2) > 0.1:
                        print("  unblocked via", e)
                        moved = True
                        break
                if not moved:
                    print(" still stuck", summarize(g)["sprite"])
                    dump(g, 28, 55, 0, 50)
                    break
            if int(d.get("levels_completed") or 0) >= 4:
                print("CLEAR")
                break
            if summarize(g)["aligned"]:
                print("ALIGNED", summarize(g))
                break

        out["final"] = summarize(g)
        (ROOT / "tests/fixtures/vc33_l4_c12_hunt.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2, default=float), encoding="utf-8"
        )
    finally:
        sess.close()


if __name__ == "__main__":
    main()
