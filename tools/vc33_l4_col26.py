"""L4: after hop, each climb step log x26 column + try force mid convert."""
from __future__ import annotations

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_ndiff  # noqa: E402
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
    g0, s0 = g, sprite(g)
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g, 0, 0
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
    print(f"{tag}x{x0} Δ=({dx},{dy}) cy={s1['body']['cy'] if s1 else None} h12={int((g2==12).sum())}")
    return d2, g2, dx, dy


def col(g, x, y0=34, y1=54):
    return [(y, int(g[y, x])) for y in range(y0, y1 + 1)]


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        for hop in (39, 15):
            print(f"\n==== hop pad{hop}")
            ent = enter_l4(sess)
            d, g = ent["data"], ent["frame"]
            while int((g == 12).sum()) == 0:
                d, g, _, _ = pad(sess, d, g, 15, tag="sink ")
            c = components(g, 12, 1, 80)[0]
            d2 = click(sess, round(c["cx"]), round(c["cy"]))
            g = plane(d2["frame"]); d = d2
            d, g, _, _ = pad(sess, d, g, hop, tag="hz ")
            print("x26", col(g, 26))
            print("x25", col(g, 25))
            print("x24", col(g, 24))
            print("mid", [c for c in components(g, 1, 4, 80) if c["cx"] > 20])

            for i in range(6):
                d, g, dx, dy = pad(sess, d, g, 15, tag=f"up{i} ")
                print("  x26", col(g, 26))
                print("  accent", sprite(g)["accent"] if sprite(g) else None)
                mid12 = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
                if mid12:
                    print("  MID12!", mid12)
                    d2 = click(sess, round(mid12[0]["cx"]), round(mid12[0]["cy"]))
                    g = plane(d2["frame"]); d = d2
                    for e in (9, 15, 39, 45, 51, 57):
                        d, g, dx, dy = pad(sess, d, g, e, tag="go ")
                        if abs(dx) > 0.1:
                            print("HOP2", dx, sprite(g))
                            # climb toward gap
                            for j in range(15):
                                sm = summarize(g)
                                print(f"nav{j}", sm["sprite"], "lv", d.get("levels_completed"))
                                if int(d.get("levels_completed") or 0) >= 4:
                                    print("CLEAR")
                                    (ROOT / "tests/fixtures/vc33_l4_clear_frame.json").write_text(
                                        __import__("json").dumps({"frame": d["frame"], "levels": d.get("levels_completed")}, indent=2),
                                        encoding="utf-8",
                                    )
                                    d1 = sess.action("ACTION1")
                                    (ROOT / "tests/fixtures/vc33_l5_frame_live.json").write_text(
                                        __import__("json").dumps({"frame": d1["frame"], "levels": d1.get("levels_completed")}, indent=2),
                                        encoding="utf-8",
                                    )
                                    return
                                moved = False
                                for x0 in (15, 9, 39, 45, 51, 57):
                                    d, g, dx, dy = pad(sess, d, g, x0, tag="n ")
                                    if abs(dx) + abs(dy) > 0.1:
                                        moved = True
                                        break
                                if not moved:
                                    break
                            break
                    break
                if abs(dy) < 0.1:
                    # try down into band with color0
                    print("  blocked; try dn/up wiggle")
                    d, g, _, _ = pad(sess, d, g, 9, tag="dn ")
                    print("  x26", col(g, 26))
                    d, g, _, _ = pad(sess, d, g, 15, tag="up ")
                    print("  x26", col(g, 26))
                    break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
