"""L4: under-beam corridor — hop bay1, kill c12, dig down, hunt +x east."""
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

CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 9: "P", 11: "A", 12: "C"}


def dump(g, y0=45, y1=63, x0=0, x1=63):
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
    g0, s0 = g, sprite(g)
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g, 0, 0
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
    print(
        f"{tag}x{x0} Δ=({dx},{dy}) cx={s1['body']['cx'] if s1 else None} "
        f"cy={s1['body']['cy'] if s1 else None} h12={int((g2==12).sum())} "
        f"lv={d2.get('levels_completed')}"
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
            d, g, _, _ = pad(sess, d, g, 15, "s ")
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        d, g, _, _ = pad(sess, d, g, 39, "hz ")
        # kill c12 with one up so env won't reverse-hop
        d, g, _, _ = pad(sess, d, g, 15, "kill12 ")
        print("after kill12", sprite(g), "h12", int((g == 12).sum()))
        dump(g)

        # dig down
        for i in range(10):
            d, g, dx, dy = pad(sess, d, g, 9, f"dig{i} ")
            if abs(dx) > 0.1:
                print("UNEXPECTED HZ while digging")
                dump(g)
            if abs(dy) < 0.1:
                print("dig floor")
                break
        dump(g)
        print("at depth", sprite(g))

        # hunt +x with all pads; also env toggles
        for round_i in range(4):
            print(f"\nround {round_i}")
            for x0 in (39, 45, 51, 57, 15, 9):
                d, g, dx, dy = pad(sess, d, g, x0, f"r{round_i} ")
                if abs(dx) > 0.1:
                    print("GOT HZ", dx)
                    dump(g)
                    # if moved right, try climb toward gap
                    for j in range(20):
                        sm = summarize(g)
                        print(f"nav{j}", sm["sprite"], "lv", d.get("levels_completed"), "al", sm["aligned"])
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
                        for x1 in (15, 9, 39, 45, 51, 57):
                            d, g, dx2, dy2 = pad(sess, d, g, x1, "n ")
                            if abs(dx2) + abs(dy2) > 0.1:
                                moved = True
                                break
                        if not moved:
                            break
                    return
            dump(g, 50, 63, 0, 63)

        print("final", summarize(g))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
