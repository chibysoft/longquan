"""L4: ceiling env raise x30; click gap11; map env bbox by height; one-enter."""
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
from tools.vc33_l4_pad_map import components, enter_l4, gap11, sprite, summarize  # noqa: E402

CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 11: "A", 12: "C"}
OUT = ROOT / "tests/fixtures/vc33_l4_ceil_env.json"


def dump(g, y0=28, y1=55, x0=15, x1=50):
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
        return d, g, 0.0, 0.0, {}
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0.0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0.0
    to0 = np.argwhere((g0 == 3) & (g2 == 0))
    to3 = np.argwhere((g0 == 0) & (g2 == 3))
    def bb(a):
        if len(a) == 0:
            return None
        return [int(a[:, 1].min()), int(a[:, 1].max()), int(a[:, 0].min()), int(a[:, 0].max())]
    info = {"3to0": bb(to0), "0to3": bb(to3), "nd": body_ndiff(g0, g2)}
    print(
        f"{tag}x{x0} nd={info['nd']} Δ=({dx},{dy}) cy={s1['body']['cy'] if s1 else None} "
        f"3→0={info['3to0']} 0→3={info['0to3']} lv={d2.get('levels_completed')}"
    )
    return d2, g2, dx, dy, info


def tops(g, xs=(24, 25, 26, 30, 31, 32)):
    o = {}
    for x in xs:
        ys = [y for y in range(34, 56) if int(g[y, x]) == 0]
        o[x] = min(ys) if ys else None
    return o


def mid0(g):
    return [(x, y) for x in (24, 25, 26, 30, 31, 32) for y in range(34, 46) if int(g[y, x]) == 0]


def main():
    key = _api_key()
    sess = Sess(key)
    out = {}
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g, _, _, _ = pad(sess, d, g, 15, "s ")
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        d, g, _, _, _ = pad(sess, d, g, 39, "hz ")
        d, g, _, _, _ = pad(sess, d, g, 15, "kill ")

        # climb to cy45, env map, then ceiling
        d, g, _, _, _ = pad(sess, d, g, 15, "to45 ")
        print("AT45", tops(g), "mid0", mid0(g))
        dump(g)
        at45 = {}
        for e in (39, 45, 51, 57):
            d, g, _, _, info = pad(sess, d, g, e, f"45e ")
            at45[e] = {"tops": tops(g), "mid0": mid0(g), **info}
            print("  tops", tops(g), "mid0", mid0(g))
        out["at45"] = at45

        d, g, _, dy, _ = pad(sess, d, g, 15, "to42 ")
        if abs(dy) < 0.1:
            # maybe need another
            pass
        print("AT42", tops(g), sprite(g))
        dump(g)

        # spam pad39 at ceiling
        ceil_log = []
        for i in range(8):
            d, g, _, _, info = pad(sess, d, g, 39, f"c39_{i} ")
            row = {"i": i, "tops": tops(g), "mid0": mid0(g), **info}
            print("  ", row["tops"], row["mid0"])
            ceil_log.append(row)
            if mid0(g) or any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                print("HIT mid0/12")
                dump(g)
                break
        # also try 45/51/57 a few times
        for e in (45, 51, 57, 45, 39):
            d, g, _, _, info = pad(sess, d, g, e, f"c{e} ")
            print("  tops", tops(g), "mid0", mid0(g))
            ceil_log.append({"pad": e, "tops": tops(g), "mid0": mid0(g), **info})
            if mid0(g):
                print("HIT")
                dump(g)
                break
        out["ceil"] = ceil_log

        # click gap11
        gp = gap11(g)
        print("gap", gp)
        if gp:
            for y in range(gp["y0"], gp["y1"] + 1):
                for x in range(gp["x0"], gp["x1"] + 1):
                    g0 = g
                    d2 = click(sess, x, y)
                    if d2 is None:
                        break
                    g2 = plane(d2["frame"])
                    nd = body_ndiff(g0, g2)
                    print(f"gapclick({x},{y}) nd={nd} ch={body_changes(g0,g2)} lv={d2.get('levels_completed')}")
                    if nd:
                        g = g2; d = d2
        # click beam under mid y46
        for x in range(27, 30):
            g0 = g
            d2 = click(sess, x, 46)
            if d2:
                g2 = plane(d2["frame"])
                nd = body_ndiff(g0, g2)
                print(f"beam({x},46) nd={nd} ch={body_changes(g0,g2)}")
                if nd:
                    g = g2; d = d2

        # last ditch: go down to 51, c12 on, arm, hop west, climb left to max,
        # sink exactly to convert with mid-watching — already known
        # instead: from ceiling go to 51, keep trying mid convert by overlapping
        print("\nSink to 51 watch mid")
        for i in range(6):
            d, g, _, dy, _ = pad(sess, d, g, 9, f"dn{i} ")
            print("  cy", sprite(g)["body"]["cy"], "c12", components(g, 12, 1, 80), "mid0", mid0(g))
            if abs(dy) < 0.1:
                break
        dump(g, 40, 56, 0, 50)

        out["final"] = summarize(g)
        out["levels"] = d.get("levels_completed")
        OUT.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
        print("wrote", OUT, "lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
