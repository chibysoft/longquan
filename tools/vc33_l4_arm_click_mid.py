"""L4: after arm left gate, click MID window — hop distance/dir?"""
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

CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 11: "A", 12: "C"}


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
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g
    return d2, plane(d2["frame"])


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g = pad(sess, d, g, 15, "s")
        left = components(g, 12, 1, 80)[0]
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]
        print("left12", left, "mid1", mid)
        # ARM only
        d2 = click(sess, round(left["cx"]), round(left["cy"]))
        g = plane(d2["frame"]); d = d2
        print("armed", sprite(g), body_changes)
        # click MID (still color1)
        g0, s0 = g, sprite(g)
        d2 = click(sess, round(mid["cx"]), round(mid["cy"]))
        g = plane(d2["frame"]); d = d2
        s1 = sprite(g)
        dx = s1["body"]["cx"] - s0["body"]["cx"]
        dy = s1["body"]["cy"] - s0["body"]["cy"]
        print(f"click MID nd={body_ndiff(g0,g)} Δ=({dx},{dy}) ch={body_changes(g0,g)} "
              f"sp={s1} h12={int((g==12).sum())} lv={d.get('levels_completed')}")
        dump(g)
        if int(d.get("levels_completed") or 0) >= 4:
            print("CLEAR")
            return

        # if hopped to bay1 or further, continue: arm/click path toward gap
        for i in range(20):
            sm = summarize(g)
            print(f"nav{i} cx={sm['sprite']['body']['cx']} cy={sm['sprite']['body']['cy']} "
                  f"h12={int((g==12).sum())} al={sm['aligned']} lv={d.get('levels_completed')}")
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
                print("L5", d1.get("levels_completed"))
                return
            # prefer: convert/click gates, climb, hop
            c12s = components(g, 12, 1, 80)
            if c12s:
                # click nearest c12
                sp = sprite(g)
                c = min(c12s, key=lambda t: abs(t["cx"] - sp["body"]["cx"]))
                g0, s0 = g, sprite(g)
                d2 = click(sess, round(c["cx"]), round(c["cy"]))
                if d2 is None:
                    break
                g = plane(d2["frame"]); d = d2
                s1 = sprite(g)
                print(f"  click12 Δ=({s1['body']['cx']-s0['body']['cx']},{s1['body']['cy']-s0['body']['cy']})")
                continue
            # try mid click
            mids = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
            if mids:
                g0, s0 = g, sprite(g)
                d2 = click(sess, round(mids[0]["cx"]), round(mids[0]["cy"]))
                if d2:
                    g2 = plane(d2["frame"])
                    s1 = sprite(g2)
                    dx = s1["body"]["cx"] - s0["body"]["cx"]
                    if abs(dx) > 0.1 or body_ndiff(g, g2):
                        print(f"  click mid1 Δ=({dx},{s1['body']['cy']-s0['body']['cy']}) ch={body_changes(g,g2)}")
                        g = g2; d = d2
                        continue
            # vertical toward gap y
            moved = False
            for x0 in (15, 9, 39, 45):
                p = next(p for p in pads_sorted(g) if p["x0"] == x0)
                g0, s0 = g, sprite(g)
                d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
                if d2 is None:
                    break
                g = plane(d2["frame"]); d = d2
                s1 = sprite(g)
                dx = s1["body"]["cx"] - s0["body"]["cx"]
                dy = s1["body"]["cy"] - s0["body"]["cy"]
                print(f"  pad{x0} Δ=({dx},{dy})")
                if abs(dx) + abs(dy) > 0.1:
                    moved = True
                    break
            if not moved:
                print("stuck"); dump(g); break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
