"""L4: bay1 re-arm left c12, then click MID — second hop east?"""
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
    s0 = sprite(g)
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g, 0, 0
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
    print(f"{tag}x{x0} Δ=({dx},{dy}) cx={s1['body']['cx'] if s1 else None} cy={s1['body']['cy'] if s1 else None} h12={int((g2==12).sum())}")
    return d2, g2, dx, dy


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g, _, _ = pad(sess, d, g, 15, "s ")
        left = components(g, 12, 1, 80)[0]
        # arm + hop via pad39 (keeps c12)
        d2 = click(sess, round(left["cx"]), round(left["cy"]))
        g = plane(d2["frame"]); d = d2
        d, g, _, _ = pad(sess, d, g, 39, "hz ")
        print("bay1", sprite(g), "c12", components(g, 12, 1, 80))

        # re-arm left c12
        left = [c for c in components(g, 12, 1, 80) if c["cx"] < 20][0]
        g0 = g
        d2 = click(sess, round(left["cx"]), round(left["cy"]))
        g = plane(d2["frame"]); d = d2
        print(f"rearm nd={body_ndiff(g0,g)} ch={body_changes(g0,g)} sp={sprite(g)}")

        # click MID
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]
        g0, s0 = g, sprite(g)
        d2 = click(sess, round(mid["cx"]), round(mid["cy"]))
        g = plane(d2["frame"]); d = d2
        s1 = sprite(g)
        print(
            f"click MID Δ=({s1['body']['cx']-s0['body']['cx']},{s1['body']['cy']-s0['body']['cy']}) "
            f"ch={body_changes(g0,g)} cx={s1['body']['cx']} cy={s1['body']['cy']} "
            f"h12={int((g==12).sum())} lv={d.get('levels_completed')}"
        )
        dump(g)

        if s1["body"]["cx"] > 25:
            print("PAST MID!")
            for i in range(25):
                sm = summarize(g)
                print(f"nav{i}", sm["sprite"], sm["aligned"], d.get("levels_completed"))
                if int(d.get("levels_completed") or 0) >= 4:
                    print("CLEAR")
                    (ROOT / "tests/fixtures/vc33_l4_clear_frame.json").write_text(
                        __import__("json").dumps({"frame": d["frame"], "levels": d.get("levels_completed")}, indent=2),
                        encoding="utf-8",
                    )
                    d1 = sess.action("ACTION1")
                    print("L5", d1.get("levels_completed"))
                    return
                # try climb / hop
                c12s = components(g, 12, 1, 80)
                if c12s:
                    c = c12s[0]
                    d2 = click(sess, round(c["cx"]), round(c["cy"]))
                    if d2:
                        g = plane(d2["frame"]); d = d2
                        print("  gated", sprite(g))
                        continue
                moved = False
                for x0 in (15, 9, 39, 45, 51, 57):
                    d, g, dx, dy = pad(sess, d, g, x0, "n ")
                    if abs(dx) + abs(dy) > 0.1:
                        moved = True
                        break
                if not moved:
                    mid1 = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
                    if mid1:
                        d2 = click(sess, round(mid1[0]["cx"]), round(mid1[0]["cy"]))
                        if d2:
                            g2 = plane(d2["frame"])
                            if body_ndiff(g, g2):
                                g = g2; d = d2
                                print("  midclick", sprite(g))
                                continue
                    print("stuck"); dump(g); break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
