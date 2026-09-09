"""L4: at ceiling, alternate pad9/15 (noop?) with env; try fill-pit then up; soft overlap levels."""
from __future__ import annotations

import json
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

OUT = ROOT / "tests/fixtures/vc33_l4_ceil_wiggle.json"


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
        f"{tag}x{x0} nd={body_ndiff(g0,g2)} Δ=({dx},{dy}) cy={s1['body']['cy'] if s1 else None} "
        f"ch={body_changes(g0,g2)} lv={d2.get('levels_completed')}"
    )
    return d2, g2, dx, dy


def cell(g, x, y):
    return int(g[y, x])


def main():
    key = _api_key()
    sess = Sess(key)
    out = {}
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
        for _ in range(5):
            d, g, _, dy = pad(sess, d, g, 15, "up ")
            if abs(dy) < 0.1:
                break
        print("ceiling", sprite(g))
        print("crit", {(x, y): cell(g, x, y) for x in range(24, 31) for y in range(44, 47)})

        # wiggle: dn one, env, up, env — try to desync pit vs accent by 1
        for round_i in range(4):
            d, g, _, _ = pad(sess, d, g, 9, f"w{round_i}dn ")
            print("  after dn crit", {(x, y): cell(g, x, y) for x in (26, 30) for y in range(44, 50)})
            for e in (39, 45):
                d, g, _, _ = pad(sess, d, g, e, f"w{round_i}e{e} ")
                print("  after env", e, {(x, y): cell(g, x, y) for x in (26, 30) for y in range(44, 50)})
            d, g, _, dy = pad(sess, d, g, 15, f"w{round_i}up ")
            print("  after up cy", sprite(g)["body"]["cy"], "crit",
                  {(x, y): cell(g, x, y) for x in (26, 30) for y in range(44, 50)},
                  "mid12", [c for c in components(g, 12, 1, 80) if c["cx"] > 20],
                  "lv", d.get("levels_completed"))
            if any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("MID!")
                break
            if int(d.get("levels_completed") or 0) >= 4:
                print("CLEAR")
                break
            # return to ceiling if dropped
            for _ in range(3):
                if sprite(g)["body"]["cy"] <= 42.5:
                    break
                d, g, _, dy = pad(sess, d, g, 15, "reclimb ")
                if abs(dy) < 0.1:
                    break

        # From ceiling: one dn to cy45 where BODY overlaps mid; check convert on body-overlap
        print("\nbody-overlap at cy45")
        d, g, _, _ = pad(sess, d, g, 9, "to45 ")
        print(sprite(g), "c1", components(g, 1, 4, 80), "c12", components(g, 12, 1, 80))
        # click mid while body overlaps
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
        if mid:
            g0 = g
            d2 = click(sess, round(mid[0]["cx"]), round(mid[0]["cy"]))
            g = plane(d2["frame"]); d = d2
            print("click mid@45", body_ndiff(g0, g), body_changes(g0, g), d.get("levels_completed"))

        out["final"] = summarize(g)
        out["levels"] = d.get("levels_completed")
        OUT.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
        print("done lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
