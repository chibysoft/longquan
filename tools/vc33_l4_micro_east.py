"""L4 H56 (c): lean micro-east hunt — NO flood clicks (avoid HTTP400).

A) deep bay1 + env: click up to 12 eastmost color0 cells
B) ceiling: thin east face (x=body.x1+1 only, body y-band)
C) pad corners floor + ceiling
D) bay0 one-up: thin east face toward mid

Success: odd |dx|∉{0,3,15} OR cx>20.5 OR levels≥4.
"""
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

OUT = ROOT / "tests/fixtures/vc33_l4_micro_east.json"


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad_c(sess, g, x0):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    return click(sess, int(round(p["cx"])), int(round(p["cy"])))


def pad_corner(sess, g, x0, which):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    pts = {
        "tl": (p["x0"], p["y0"]),
        "tr": (p["x1"], p["y0"]),
        "bl": (p["x0"], p["y1"]),
        "br": (p["x1"], p["y1"]),
    }
    x, y = pts[which]
    return click(sess, x, y)


def setup_bay1(sess, clear_climb=False, sink_extra=0):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    for _ in range(8):
        if int((g == 12).sum()) > 0:
            break
        d2 = pad_c(sess, g, 15)
        g = plane(d2["frame"]); d = d2
    c = [x for x in components(g, 12, 1, 80) if x["cx"] < 20][0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"]); d = d2
    d2 = pad_c(sess, g, 39)
    g = plane(d2["frame"]); d = d2
    if clear_climb:
        d2 = pad_c(sess, g, 15)
        g = plane(d2["frame"]); d = d2
        for _ in range(6):
            cy0 = sprite(g)["body"]["cy"]
            d2 = pad_c(sess, g, 15)
            g2 = plane(d2["frame"])
            if abs(sprite(g2)["body"]["cy"] - cy0) < 0.1:
                g = g2; d = d2
                break
            g = g2; d = d2
    for _ in range(sink_extra):
        d2 = pad_c(sess, g, 9)
        if d2 is None:
            break
        g = plane(d2["frame"]); d = d2
    return d, g


def record_move(tag, sp0, sp1, d0, d1, g0, g1, xy=None):
    dx = (sp1["body"]["cx"] - sp0["body"]["cx"]) if sp0 and sp1 else 0
    dy = (sp1["body"]["cy"] - sp0["body"]["cy"]) if sp0 and sp1 else 0
    odd = abs(dx) > 0.05 and round(abs(dx), 1) not in {3.0, 15.0}
    return {
        "tag": tag,
        "xy": xy,
        "dx": dx,
        "dy": dy,
        "cx0": sp0["body"]["cx"] if sp0 else None,
        "cx1": sp1["body"]["cx"] if sp1 else None,
        "x1_1": sp1["body"]["x1"] if sp1 else None,
        "cy0": sp0["body"]["cy"] if sp0 else None,
        "cy1": sp1["body"]["cy"] if sp1 else None,
        "lv0": d0.get("levels_completed"),
        "lv1": d1.get("levels_completed") if d1 else None,
        "h12": int((g1 == 12).sum()) if g1 is not None else None,
        "odd_dx": odd,
        "nd": body_ndiff(g0, g1) if g1 is not None else 0,
        "ch": body_changes(g0, g1) if g1 is not None and body_ndiff(g0, g1) else {},
    }


def is_hit(row):
    return bool(
        row.get("odd_dx")
        or (row.get("cx1") or 0) > 20.55
        or (row.get("lv1") or 0) > (row.get("lv0") or 0)
    )


def main():
    key = _api_key()
    sess = Sess(key)
    rows = []
    hits = []
    max_cx = 0.0
    max_x1 = 0
    http400 = 0
    try:
        sess.open()

        # A deep + env + few color0
        print("\n## A deep + east color0 (cap 12)")
        d, g = setup_bay1(sess, clear_climb=False, sink_extra=2)
        sp = sprite(g)
        print(f"  base cx={sp['body']['cx']} cy={sp['body']['cy']} h12={int((g==12).sum())}")
        max_cx = max(max_cx, sp["body"]["cx"])
        for x0 in (39, 45, 51, 57):
            d2 = pad_c(sess, g, x0)
            if d2:
                g = plane(d2["frame"]); d = d2
        body = sprite(g)["body"]
        zeros = sorted(
            ((int(x), int(y)) for y, x in np.argwhere(g == 0)
             if int(x) > body["x1"] and body["y0"] - 2 <= int(y) <= body["y1"] + 6),
            key=lambda t: (t[0], t[1]),
        )
        # unique by x (eastmost per column)
        by_x = {}
        for x, y in zeros:
            by_x.setdefault(x, y)
        targets = [(x, by_x[x]) for x in sorted(by_x)[:12]]
        print(f"  targets={targets}")
        for x, y in targets:
            sp0 = sprite(g)
            d2 = click(sess, x, y)
            if d2 is None:
                http400 += 1
                if http400 >= 5:
                    print("  too many 400 — skip rest of A")
                    break
                continue
            http400 = 0
            g2 = plane(d2["frame"])
            row = record_move("A/c0", sp0, sprite(g2), d, d2, g, g2, (x, y))
            rows.append(row)
            max_cx = max(max_cx, row["cx1"] or 0)
            max_x1 = max(max_x1, row["x1_1"] or 0)
            if abs(row["dx"]) + abs(row["dy"]) > 0.1:
                print(f"  move ({x},{y}) d=({row['dx']:+.1f},{row['dy']:+.1f}) cx={row['cx1']}")
            if is_hit(row):
                print("*** HIT", row)
                hits.append(row)
            g = g2; d = d2

        # B ceiling thin face
        print("\n## B ceiling east face")
        d, g = setup_bay1(sess, clear_climb=True)
        for x0 in (39, 45, 51, 57):
            d2 = pad_c(sess, g, x0)
            if d2:
                g = plane(d2["frame"]); d = d2
        body = sprite(g)["body"]
        print(f"  ceil cx={body['cx']} cy={body['cy']} x1={body['x1']} y0={body['y0']}")
        max_cx = max(max_cx, body["cx"])
        x = body["x1"] + 1
        for y in range(body["y0"], body["y1"] + 3):
            for xx in (x, x + 1, x + 2):
                if xx > 40:
                    continue
                sp0 = sprite(g)
                d2 = click(sess, xx, y)
                if d2 is None:
                    http400 += 1
                    continue
                http400 = 0
                g2 = plane(d2["frame"])
                row = record_move("B/face", sp0, sprite(g2), d, d2, g, g2, (xx, y))
                rows.append(row)
                max_cx = max(max_cx, row["cx1"] or 0)
                max_x1 = max(max_x1, row["x1_1"] or 0)
                if abs(row["dx"]) + abs(row["dy"]) > 0.1:
                    print(f"  move ({xx},{y}) d=({row['dx']:+.1f},{row['dy']:+.1f})")
                if is_hit(row):
                    print("*** HIT", row)
                    hits.append(row)
                g = g2; d = d2

        # C pad corners
        for label, clear, sink in (("C/floor", False, 2), ("C/ceil", True, 0)):
            print(f"\n## {label} pad corners")
            d, g = setup_bay1(sess, clear_climb=clear, sink_extra=sink)
            print(f"  cy={sprite(g)['body']['cy']} cx={sprite(g)['body']['cx']}")
            for x0 in (9, 15, 39, 45, 51, 57):
                for which in ("tl", "tr", "bl", "br"):
                    sp0 = sprite(g)
                    d2 = pad_corner(sess, g, x0, which)
                    if d2 is None:
                        continue
                    g2 = plane(d2["frame"])
                    row = record_move(f"{label}/pad{x0}_{which}", sp0, sprite(g2), d, d2, g, g2)
                    rows.append(row)
                    max_cx = max(max_cx, row["cx1"] or 0)
                    max_x1 = max(max_x1, row["x1_1"] or 0)
                    if abs(row["dx"]) + abs(row["dy"]) > 0.1:
                        print(f"  {row['tag']} d=({row['dx']:+.1f},{row['dy']:+.1f}) cx={row['cx1']}")
                    if is_hit(row):
                        print("*** HIT", row)
                        hits.append(row)
                    g = g2; d = d2

        # D bay0 one-up east
        print("\n## D bay0 one-up east face")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        d2 = pad_c(sess, g, 9)
        g = plane(d2["frame"]); d = d2
        body = sprite(g)["body"]
        print(f"  cx={body['cx']} cy={body['cy']} x1={body['x1']}")
        max_cx = max(max_cx, body["cx"])
        for xx in range(body["x1"] + 1, min(28, body["x1"] + 8)):
            for y in range(body["y0"], body["y1"] + 1):
                sp0 = sprite(g)
                d2 = click(sess, xx, y)
                if d2 is None:
                    continue
                g2 = plane(d2["frame"])
                row = record_move("D/east", sp0, sprite(g2), d, d2, g, g2, (xx, y))
                rows.append(row)
                max_cx = max(max_cx, row["cx1"] or 0)
                if abs(row["dx"]) + abs(row["dy"]) > 0.1:
                    print(f"  move ({xx},{y}) d=({row['dx']:+.1f},{row['dy']:+.1f})")
                if is_hit(row):
                    print("*** HIT", row)
                    hits.append(row)
                g = g2; d = d2

        reading = "EAST_MICRO_FOUND" if hits else "NO_MICRO_EAST"
        out = {
            "n_rows": len(rows),
            "moves": [r for r in rows if abs(r.get("dx") or 0) + abs(r.get("dy") or 0) > 0.1],
            "hits": hits,
            "max_cx": max_cx,
            "max_x1": max_x1,
            "reading": reading,
            "hypothesis": "H56 micro-east without mid12 (lean)",
        }
        print("\n## Summary")
        print("max_cx", max_cx, "max_x1", max_x1, "hits", len(hits), "moves", len(out["moves"]))
        print("READING:", reading)
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
