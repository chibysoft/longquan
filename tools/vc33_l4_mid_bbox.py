"""L4 H40: morph mid window bbox (y1>=46) so dig@46 falls inside window y."""
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

OUT = ROOT / "tests/fixtures/vc33_l4_mid_bbox.json"
CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 11: "A", 12: "C"}


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def mid_info(g):
    mids = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
    if not mids:
        c12 = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
        return {"kind": "c12", "wins": c12}
    m = mids[0]
    return {
        "kind": "c1",
        "x0": m["x0"], "x1": m["x1"], "y0": m["y0"], "y1": m["y1"],
        "n": m["n"],
        "below": [int(g[m["y1"] + 1, x]) for x in range(m["x0"], m["x1"] + 1)] if m["y1"] + 1 < 64 else [],
        "row46": [int(g[46, x]) for x in range(m["x0"] - 1, m["x1"] + 2)],
    }


def dig_top(g, x0=15, x1=26):
    ys = [int(y) for y, x in np.argwhere(g == 0) if x0 <= x <= x1]
    return min(ys) if ys else None


def snap(g, d=None, tag=""):
    sp = sprite(g)
    mi = mid_info(g)
    info = {
        "tag": tag,
        "cy": sp["body"]["cy"] if sp else None,
        "y0": sp["body"]["y0"] if sp else None,
        "acc_y1": sp["accent"]["y1"] if sp else None,
        "dig": dig_top(g),
        "mid": mi,
        "mid12": mi.get("kind") == "c12" and bool(mi.get("wins")),
        "lv": d.get("levels_completed") if d else None,
        "h1": int((g == 1).sum()),
        "h12": int((g == 12).sum()),
    }
    print(
        f"[{tag}] cy={info['cy']} dig={info['dig']} mid={mi} "
        f"h1={info['h1']} h12={info['h12']} lv={info['lv']}"
    )
    return info


def pad(sess, d, g, x0, tag=""):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    g0 = g
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g, {}
    g2 = plane(d2["frame"])
    s0, s1 = sprite(g0), sprite(g2)
    m0, m1 = mid_info(g0), mid_info(g2)
    bbox_ch = m0 != m1
    info = {
        "dx": (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0,
        "dy": (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0,
        "bbox_ch": bbox_ch,
        "mid0": m0,
        "mid1": m1,
        "nd": body_ndiff(g0, g2),
        "ch": body_changes(g0, g2) if bbox_ch or body_ndiff(g0, g2) else {},
        "lv": d2.get("levels_completed"),
        "mid12": bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20]),
    }
    if bbox_ch or info["mid12"] or int(info["lv"] or 0) >= 4:
        print(f"{tag}x{x0} BBOX_CH mid {m0} -> {m1} mid12={info['mid12']} lv={info['lv']}")
    return d2, g2, info


def xy(sess, d, g, x, y, tag=""):
    g0 = g
    d2 = click(sess, x, y)
    if d2 is None:
        return d, g, {}
    g2 = plane(d2["frame"])
    m0, m1 = mid_info(g0), mid_info(g2)
    nd = body_ndiff(g0, g2)
    info = {
        "bbox_ch": m0 != m1,
        "mid0": m0,
        "mid1": m1,
        "nd": nd,
        "ch": body_changes(g0, g2) if nd or m0 != m1 else {},
        "lv": d2.get("levels_completed"),
        "mid12": bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20]),
    }
    if info["bbox_ch"] or info["mid12"] or nd or int(info["lv"] or 0) >= 4:
        print(f"{tag}({x},{y}) bbox_ch={info['bbox_ch']} mid={m1} nd={nd} ch={info['ch']} "
              f"mid12={info['mid12']} lv={info['lv']}")
    return d2, g2, info


def to_ceil(sess):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        d, g, _ = pad(sess, d, g, 15, "s ")
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"]); d = d2
    d, g, _ = pad(sess, d, g, 39, "hz ")
    for i in range(5):
        d, g, info = pad(sess, d, g, 15, f"up{i} ")
        if abs(info.get("dy") or 0) < 0.1:
            break
    return d, g


def maybe_clear(d, sess):
    if int(d.get("levels_completed") or 0) < 4:
        return False
    print("CLEAR", d.get("levels_completed"))
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
    log = []
    hits = []
    try:
        sess.open()

        # A: track mid bbox from enter through hop/climb/env
        print("\n==== A mid bbox timeline")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        log.append(snap(g, d, "enter"))
        while int((g == 12).sum()) == 0:
            d, g, info = pad(sess, d, g, 15, "s ")
            if info.get("bbox_ch"):
                hits.append({"sink_bbox": info})
        log.append(snap(g, d, "converted"))
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        log.append(snap(g, d, "armed"))
        d, g, info = pad(sess, d, g, 39, "hz ")
        if info.get("bbox_ch"):
            hits.append({"hop_bbox": info})
        log.append(snap(g, d, "hop"))
        for i in range(5):
            d, g, info = pad(sess, d, g, 15, f"up{i} ")
            log.append(snap(g, d, f"up{i}"))
            if info.get("bbox_ch"):
                hits.append({"climb_bbox": info})
            if abs(info.get("dy") or 0) < 0.1:
                break
        for e in (39, 45, 51, 57, 39, 45):
            d, g, info = pad(sess, d, g, e, "e ")
            log.append(snap(g, d, f"env{e}"))
            if info.get("bbox_ch") or info.get("mid12"):
                hits.append({"env_bbox": info})
            if maybe_clear(d, sess):
                return

        # B: at ceil, click mid edges / below / extend targets
        print("\n==== B click to extend mid y1")
        d, g = to_ceil(sess)
        log.append(snap(g, d, "ceil"))
        mi = mid_info(g)
        targets = []
        # bottom edge and one row below (beam)
        for x in range(mi["x0"] - 1, mi["x1"] + 2):
            targets.append((x, mi["y1"], "bot"))
            targets.append((x, mi["y1"] + 1, "below"))
            targets.append((x, 46, "y46"))
        # top edge expand up
        for x in range(mi["x0"], mi["x1"] + 1):
            targets.append((x, mi["y0"], "top"))
            targets.append((x, mi["y0"] - 1, "above"))
        # side expand
        for y in range(mi["y0"], mi["y1"] + 1):
            targets.append((mi["x0"] - 1, y, "L"))
            targets.append((mi["x1"] + 1, y, "R"))
        seen = set()
        for x, y, tag in targets:
            if (x, y) in seen or not (0 <= x < 64 and 0 <= y < 64):
                continue
            seen.add((x, y))
            d, g, info = xy(sess, d, g, x, y, tag)
            if info.get("bbox_ch") or info.get("mid12") or int(info.get("lv") or 0) >= 4:
                hits.append({"click": (x, y, tag), **info})
            if maybe_clear(d, sess):
                return

        # C: left convert style — at ceil with dig@46, does "contact" alone ever flip if we spam mid?
        print("\n==== C spam mid at ceil with dig contact")
        for i in range(8):
            mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
            if not mid:
                break
            d, g, info = xy(sess, d, g, round(mid[0]["cx"]), round(mid[0]["cy"]), f"spam{i}")
            if info.get("mid12") or info.get("bbox_ch"):
                hits.append({"spam": info})
            if maybe_clear(d, sess):
                return

        # D: dn to cy45 (dig drops), env, up — watch mid y1
        print("\n==== D phase mid y1")
        d, g, _ = pad(sess, d, g, 9, "dn ")
        log.append(snap(g, d, "dn"))
        for e in (39, 45, 51):
            d, g, info = pad(sess, d, g, e, "de ")
            if info.get("bbox_ch"):
                hits.append({"de": info})
        d, g, info = pad(sess, d, g, 15, "reup ")
        log.append(snap(g, d, "reup"))
        if info.get("bbox_ch") or info.get("mid12"):
            hits.append({"reup": info})

        # E: compare left window bbox morph on convert — mid never morphs?
        print("\n==== E left win bbox on convert (control)")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        left = [c for c in components(g, 1, 4, 80) if c["cx"] < 20][0]
        print("left enter", left)
        d, g, _ = pad(sess, d, g, 15, "p ")
        left = [c for c in components(g, 1, 4, 80) if c["cx"] < 20][0]
        print("left pre", left)
        d, g, _ = pad(sess, d, g, 15, "c ")
        left12 = components(g, 12, 1, 80)[0]
        print("left post12", left12, "same bbox?", 
              left12["x0"] == left["x0"] and left12["y1"] == left["y1"])

        OUT.write_text(json.dumps({"log": log, "hits": hits, "final_lv": d.get("levels_completed")}, indent=2, default=str), encoding="utf-8")
        print("done hits", len(hits), "lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
