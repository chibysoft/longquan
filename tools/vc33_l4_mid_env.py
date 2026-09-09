"""L4: at bay1 ceiling beside mid, spam env for 1→12; then gate +x."""
from __future__ import annotations

import json
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


def dump(g, y0=34, y1=52, x0=0, x1=50):
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
    mid = [c for c in components(g2, 12, 1, 80) if c["cx"] > 20]
    print(
        f"{tag}x{x0} nd={body_ndiff(g0,g2)} Δ=({dx},{dy}) cy={s1['body']['cy'] if s1 else None} "
        f"h12={int((g2==12).sum())} mid12={mid} ch={body_changes(g0,g2)} lv={d2.get('levels_completed')}"
    )
    return d2, g2, dx, dy


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g, _, _ = pad(sess, d, g, 15, tag="sink ")
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"])
        d = d2
        d, g, dx, _ = pad(sess, d, g, 39, tag="hz ")
        assert abs(dx) > 1

        for i in range(5):
            d, g, _, dy = pad(sess, d, g, 15, tag=f"up{i} ")
            if abs(dy) < 0.1:
                break

        print("CEILING")
        dump(g)

        # env sequence variants
        seqs = [
            [39],
            [45],
            [51],
            [57],
            [39, 45],
            [45, 39],
            [39, 39],
            [45, 45],
            [39, 45, 51, 57],
            [57, 51, 45, 39],
            [39, 15, 39],
            [45, 9, 45],
        ]
        # We can't restore between seqs without re-enter. Do cumulative but watch mid12.
        print("\nENV cumulative at ceiling")
        for x0 in (39, 45, 51, 57, 39, 45, 51, 57, 39, 45):
            d, g, dx, dy = pad(sess, d, g, x0, tag="env ")
            if any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("MID CONVERTED")
                dump(g)
                break
            if abs(dx) > 0.1:
                print("unexpected hz", dx)
                dump(g)
                break

        # try one step down into mid bottom band
        print("\nOne down then env")
        d, g, _, _ = pad(sess, d, g, 9, tag="dn ")
        dump(g)
        for x0 in (39, 45, 51, 57, 39, 45):
            d, g, dx, dy = pad(sess, d, g, x0, tag="env2 ")
            if any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("MID CONVERTED at cy45")
                dump(g)
                break
            if int((g == 12).sum()):
                print("some c12", components(g, 12, 1, 80))

        # alternate env with tiny vertical wiggle
        print("\nWiggle env")
        for i in range(6):
            d, g, _, _ = pad(sess, d, g, 15, tag="wup ")
            d, g, _, _ = pad(sess, d, g, 39, tag="we ")
            d, g, _, _ = pad(sess, d, g, 9, tag="wdn ")
            d, g, _, _ = pad(sess, d, g, 45, tag="we2 ")
            if any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("MID via wiggle")
                dump(g)
                break
            if summarize(g)["aligned"] or int(d.get("levels_completed") or 0) >= 4:
                print("CLEAR", d.get("levels_completed"))
                break

        print("final", summarize(g))
        dump(g)
        (ROOT / "tests/fixtures/vc33_l4_mid_env.json").write_text(
            json.dumps({"final": summarize(g), "levels": d.get("levels_completed")}, indent=2, default=float),
            encoding="utf-8",
        )
    finally:
        sess.close()


if __name__ == "__main__":
    main()
