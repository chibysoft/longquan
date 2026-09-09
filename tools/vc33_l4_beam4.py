"""L4: break beam under mid (27-29,46) for 4-connect dig; step-watch dig through y45."""
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
from tools.vc33_l4_pad_map import components, enter_l4, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_beam4.json"


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
        return d, g, {}
    g2 = plane(d2["frame"])
    s0, s1 = sprite(g), sprite(g2)
    info = {
        "dx": (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0,
        "dy": (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0,
        "cy": s1["body"]["cy"] if s1 else None,
        "mid12": bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20]),
        "lv": d2.get("levels_completed"),
        "beam": {(x, y): int(g2[y, x]) for x in (26, 27, 28, 29) for y in (45, 46)},
        "n4": n4_zero_to_mid(g2),
    }
    print(f"{tag}x{x0} Δ=({info['dx']},{info['dy']}) cy={info['cy']} "
          f"beam46={[info['beam'][(x,46)] for x in (26,27,28,29)]} n4={info['n4']} "
          f"mid12={info['mid12']} lv={info['lv']}")
    return d2, g2, info


def n4_zero_to_mid(g):
    """Count color0 cells that are 4-adjacent to any mid color1 cell."""
    mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
    if not mid:
        return 0
    m = mid[0]
    n = 0
    for y in range(m["y0"], m["y1"] + 1):
        for x in range(m["x0"], m["x1"] + 1):
            if int(g[y, x]) != 1:
                continue
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < 64 and 0 <= yy < 64 and int(g[yy, xx]) == 0:
                    n += 1
    return n


def maybe_clear(d, sess):
    if int(d.get("levels_completed") or 0) < 4:
        return False
    print("CLEAR")
    (ROOT / "tests/fixtures/vc33_l4_clear_frame.json").write_text(
        json.dumps({"frame": d["frame"], "levels": d.get("levels_completed")}, indent=2),
        encoding="utf-8",
    )
    d1 = sess.action("ACTION1")
    (ROOT / "tests/fixtures/vc33_l5_frame_live.json").write_text(
        json.dumps({"frame": d1["frame"], "levels": d1.get("levels_completed")}, indent=2),
        encoding="utf-8",
    )
    return True


def main():
    key = _api_key()
    sess = Sess(key)
    hits = []
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g, _ = pad(sess, d, g, 15, "s ")
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        d, g, _ = pad(sess, d, g, 39, "hz ")

        # A: at floor with c12, click beam under mid + env
        print("\n==== A floor c12 beam clicks")
        print("n4", n4_zero_to_mid(g), "beam", {(x, y): int(g[y, x]) for x in (27, 28, 29) for y in (45, 46)})
        for x, y in [(27, 46), (28, 46), (29, 46), (27, 47), (28, 45), (26, 45)]:
            g0 = g
            d2 = click(sess, x, y)
            if d2 is None:
                break
            g2 = plane(d2["frame"])
            nd = body_ndiff(g0, g2)
            n4 = n4_zero_to_mid(g2)
            if nd or n4 or int(g2[46, 27]) != 5:
                print(f"  ({x},{y}) nd={nd} ch={body_changes(g0,g2)} n4={n4} "
                      f"beam27_46={int(g2[46,27])} mid12={bool([c for c in components(g2,12,1,80) if c['cx']>20])}")
                hits.append({"floor_beam": (x, y), "nd": nd, "n4": n4})
            g = g2; d = d2
            if maybe_clear(d, sess):
                return
        for e in (39, 45, 51, 57):
            d, g, info = pad(sess, d, g, e, "Ae ")
            if info["n4"] or info["beam"][(27, 46)] != 5:
                hits.append({"env_beam": info})

        # B: climb step-by-step watching n4 and (26,45)
        print("\n==== B climb n4 watch")
        for i in range(6):
            d, g, info = pad(sess, d, g, 15, f"up{i} ")
            c2645 = int(g[45, 26])
            print(f"  (26,45)={c2645} n4={info['n4']} dig_band_y45="
                  f"{sum(1 for x in range(15, 27) if int(g[45,x])==0)}")
            if info["n4"] or c2645 == 0 or info["mid12"]:
                hits.append({"climb": info, "c2645": c2645})
            if abs(info.get("dy") or 0) < 0.1:
                break
            if maybe_clear(d, sess):
                return

        # C: at ceil, click beam again + mid after
        print("\n==== C ceil beam + mid")
        print("ceil n4", n4_zero_to_mid(g), "crit",
              {(x, y): int(g[y, x]) for x, y in [(26, 45), (26, 46), (27, 45), (27, 46)]})
        for x, y in [(27, 46), (28, 46), (29, 46), (26, 45), (27, 45)]:
            g0 = g
            d2 = click(sess, x, y)
            if d2 is None:
                break
            g2 = plane(d2["frame"])
            nd = body_ndiff(g0, g2)
            n4 = n4_zero_to_mid(g2)
            mid12 = bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20])
            if nd or n4 or mid12 or int(g2[46, 27]) != int(g0[46, 27]):
                print(f"  ({x},{y}) nd={nd} n4={n4} mid12={mid12} beam={int(g2[46,27])}")
                hits.append({"ceil": (x, y), "n4": n4, "mid12": mid12})
            g = g2; d = d2
            if maybe_clear(d, sess):
                return

        # D: geometric note — left convert n4 at pre frame
        print("\n==== D left convert n4 control")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        d, g, _ = pad(sess, d, g, 15, "p ")
        left = [c for c in components(g, 1, 4, 80) if c["cx"] < 20][0]
        # count 0 adjacent to left win
        n = 0
        for y in range(left["y0"], left["y1"] + 1):
            for x in range(left["x0"], left["x1"] + 1):
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < 64 and 0 <= yy < 64 and int(g[yy, xx]) == 0:
                        n += 1
        print("pre-convert left n4_zero", n)
        d, g, _ = pad(sess, d, g, 15, "c ")
        print("post h12", int((g == 12).sum()))

        OUT.write_text(json.dumps({"hits": hits, "final_lv": d.get("levels_completed")}, indent=2, default=str), encoding="utf-8")
        print("done hits", hits, "lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
