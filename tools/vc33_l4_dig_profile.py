"""L4: full color0 xmax by row after hop/climb; rare-color clicks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_ndiff, body_changes  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_dig_profile.json"


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


def profile(g, tag):
    rows = {}
    for y in range(34, 56):
        xs = [int(x) for x in np.where(g[y] == 0)[0]]
        if xs:
            rows[y] = {"xmin": min(xs), "xmax": max(xs), "n": len(xs), "xs": xs[:20] + (["..."] if len(xs) > 20 else [])}
    sp = sprite(g)
    print(f"\n[{tag}] cy={sp['body']['cy']} y0={sp['body']['y0']} acc={sp['accent']['y0']}-{sp['accent']['y1']}")
    for y in range(44, 52):
        if y in rows:
            print(f"  y{y}: xmax={rows[y]['xmax']} xmin={rows[y]['xmin']} n={rows[y]['n']} xs={rows[y]['xs']}")
        else:
            print(f"  y{y}: (no0)")
    return {"tag": tag, "cy": sp["body"]["cy"], "rows": {str(k): v for k, v in rows.items()}}


def main():
    key = _api_key()
    sess = Sess(key)
    out = {"profiles": [], "rare": []}
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        # hist
        u, c = np.unique(g, return_counts=True)
        print("hist", dict(zip(map(int, u), map(int, c))))

        while int((g == 12).sum()) == 0:
            d, g = pad(sess, d, g, 15)
        out["profiles"].append(profile(g, "converted"))

        c12 = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c12["cx"]), round(c12["cy"]))
        g = plane(d2["frame"]); d = d2
        out["profiles"].append(profile(g, "armed"))

        d, g = pad(sess, d, g, 39)
        out["profiles"].append(profile(g, "hop"))

        for i in range(5):
            g0 = g
            d, g = pad(sess, d, g, 15)
            out["profiles"].append(profile(g, f"up{i}"))
            if abs(sprite(g)["body"]["cy"] - sprite(g0)["body"]["cy"]) < 0.1:
                break

        # rare color clicks at ceiling
        print("\n=== rare colors at ceil")
        skip = {0, 1, 3, 4, 9, 11}  # dig/air/body/pads/accent; still click 5,7,12 etc
        coords = []
        for val in (5, 7, 8, 2, 10, 12, 13, 14, 15):
            for y, x in np.argwhere(g == val):
                if 20 <= x <= 50 and 28 <= y <= 55:
                    coords.append((int(x), int(y), val))
        # dedupe nearby
        seen = set()
        for x, y, val in coords[:40]:
            key = (x // 3, y // 3, val)
            if key in seen:
                continue
            seen.add(key)
            g0 = g
            d2 = click(sess, x, y)
            if d2 is None:
                break
            g2 = plane(d2["frame"])
            nd = body_ndiff(g0, g2)
            if nd:
                ch = body_changes(g0, g2)
                print(f"rare c{val}({x},{y}) nd={nd} ch={ch} lv={d2.get('levels_completed')}")
                out["rare"].append({"c": val, "xy": (x, y), "nd": nd, "ch": ch, "lv": d2.get("levels_completed")})
                g = g2; d = d2
                if int(d2.get("levels_completed") or 0) >= 4:
                    print("CLEAR")
                    break

        # after rare, retry up
        d, g = pad(sess, d, g, 15)
        out["profiles"].append(profile(g, "after_rare_up"))
        print("final lv", d.get("levels_completed"), "mid12", [c for c in components(g, 12, 1, 80) if c["cx"] > 20])

        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
