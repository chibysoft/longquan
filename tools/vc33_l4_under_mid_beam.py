"""L4: can env open/kill beam under mid (x27-29 y46+)? then retry convert."""
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
from tools.vc33_l4_pad_map import components, enter_l4, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_under_mid_beam.json"
CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 11: "A", 12: "C"}


def dump_mid(g):
    for y in range(40, 52):
        row = "".join(CHARS.get(int(g[y, x]), str(int(g[y, x]))[-1]) for x in range(22, 36))
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
        return d, g, {}
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    under = {(x, y): int(g2[y, x]) for x in range(26, 32) for y in range(45, 51)}
    ch5 = np.argwhere(((g0 == 5) & (g2 != 5)) | ((g0 != 5) & (g2 == 5)))
    ch5 = [(int(x), int(y), int(g0[y, x]), int(g2[y, x])) for y, x in ch5 if 24 <= x <= 35]
    info = {
        "dx": (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0,
        "dy": (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0,
        "cy": s1["body"]["cy"] if s1 else None,
        "under": under,
        "beam_ch": ch5,
        "mid12": bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20]),
        "lv": d2.get("levels_completed"),
        "nd": body_ndiff(g0, g2),
    }
    if ch5 or info["mid12"] or abs(info["dx"]) + abs(info["dy"]) > 0.1:
        print(f"{tag}x{x0} Δ=({info['dx']},{info['dy']}) beam_ch={ch5[:8]} mid12={info['mid12']} lv={info['lv']}")
    return d2, g2, info


def main():
    key = _api_key()
    sess = Sess(key)
    log = []
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        print("ENTER under mid")
        dump_mid(g)

        while int((g == 12).sum()) == 0:
            d, g, _ = pad(sess, d, g, 15, "s ")
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        d, g, _ = pad(sess, d, g, 39, "hz ")

        print("\nFLOOR env vs under-mid beam")
        dump_mid(g)
        for e in [39, 45, 51, 57, 39, 45, 51, 57, 39, 45]:
            d, g, info = pad(sess, d, g, e, "e ")
            if info.get("beam_ch"):
                log.append(info)
                dump_mid(g)

        print("\nCLIMB + env interleaved")
        for i in range(4):
            d, g, info = pad(sess, d, g, 15, f"up{i} ")
            if abs(info.get("dy") or 0) < 0.1:
                break
            dump_mid(g)
            for e in (39, 45, 51):
                d, g, info = pad(sess, d, g, e, f"ue{i} ")
                if info.get("beam_ch") or info.get("mid12"):
                    log.append(info)
                    print("HIT", info.get("beam_ch"), info.get("mid12"))
                    dump_mid(g)

        print("\nCEIL final")
        dump_mid(g)
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
        print("mid", mid, "lv", d.get("levels_completed"))

        # click beam cells under mid
        for x, y in [(28, 46), (27, 46), (29, 46), (28, 47), (30, 46)]:
            g0 = g
            d2 = click(sess, x, y)
            if d2 is None:
                break
            g2 = plane(d2["frame"])
            nd = body_ndiff(g0, g2)
            if nd:
                print(f"click beam({x},{y}) nd={nd}")
                log.append({"click": (x, y), "nd": nd})
                g = g2; d = d2

        OUT.write_text(json.dumps({"log": log, "lv": d.get("levels_completed")}, indent=2, default=str), encoding="utf-8")
        print("done", d.get("levels_completed"), "logn", len(log))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
