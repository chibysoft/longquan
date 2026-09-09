"""L4 H56 (c): hunt MICRO-x / east beyond bay1 WITHOUT assuming mid12.

Prior art locked hop to cx≤20.5. This knife looks for OTHER east primitives:
  A) deep bay1 (cy≥54) after env paint — click color0 east of body
  B) ceiling frontier — click every cell on the east face / seam to mid
  C) pad CORNER clicks (not center) at floor + ceiling
  D) bay0 ceiling east face (no hop)

Success: any |dx| not in {0, 3, 15} OR cx>20.5 OR body.x1>23 OR levels≥4.
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
from tools.vc33_l4_pad_map import components, enter_l4, gap11, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_micro_east.json"
HOP_DX = {0.0, 3.0, -3.0, 15.0, -15.0}


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad_c(sess, g, x0):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    return click(sess, int(round(p["cx"])), int(round(p["cy"])))


def pad_corner(sess, g, x0, which="tl"):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    if which == "tl":
        return click(sess, p["x0"], p["y0"])
    if which == "tr":
        return click(sess, p["x1"], p["y0"])
    if which == "bl":
        return click(sess, p["x0"], p["y1"])
    return click(sess, p["x1"], p["y1"])


def mid_kind(g):
    m12 = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
    if m12:
        return 12
    m1 = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
    return 1 if m1 else None


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
        # one up clears 12
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


def try_click(sess, d, g, x, y, rows, tag, stats):
    sp0 = sprite(g)
    if not sp0:
        return d, g, False
    cx0, cy0 = sp0["body"]["cx"], sp0["body"]["cy"]
    x1_0 = sp0["body"]["x1"]
    lv0 = d.get("levels_completed")
    d2 = click(sess, x, y)
    if d2 is None:
        rows.append({"tag": tag, "xy": (x, y), "ok": False})
        return d, g, False
    g2 = plane(d2["frame"])
    sp1 = sprite(g2)
    dx = (sp1["body"]["cx"] - cx0) if sp1 else 0
    dy = (sp1["body"]["cy"] - cy0) if sp1 else 0
    lv1 = d2.get("levels_completed")
    odd = abs(dx) > 0.05 and round(abs(dx), 1) not in {3.0, 15.0}
    hit = {
        "tag": tag,
        "xy": (int(x), int(y)),
        "dx": dx,
        "dy": dy,
        "cx0": cx0,
        "cx1": sp1["body"]["cx"] if sp1 else None,
        "x1_0": x1_0,
        "x1_1": sp1["body"]["x1"] if sp1 else None,
        "cy0": cy0,
        "cy1": sp1["body"]["cy"] if sp1 else None,
        "h12": int((g2 == 12).sum()),
        "mid": mid_kind(g2),
        "lv0": lv0,
        "lv1": lv1,
        "odd_dx": odd,
        "nd": body_ndiff(g, g2),
        "ch": body_changes(g, g2) if body_ndiff(g, g2) else {},
    }
    rows.append(hit)
    stats["max_cx"] = max(stats["max_cx"], hit["cx1"] or 0)
    stats["max_x1"] = max(stats["max_x1"], hit["x1_1"] or 0)
    if odd or (hit["cx1"] or 0) > 20.5 + 0.1 or (lv1 or 0) > (lv0 or 0):
        print(f"*** HIT {tag} xy=({x},{y}) d=({dx:+.2f},{dy:+.2f}) "
              f"cx {cx0}->{hit['cx1']} lv {lv0}->{lv1} odd={odd}")
        stats["hits"].append(hit)
        return d2, g2, True
    if abs(dx) + abs(dy) > 0.1:
        print(f"  move {tag} ({x},{y}) d=({dx:+.1f},{dy:+.1f}) cx={hit['cx1']} cy={hit['cy1']}")
    return d2, g2, False


def color0_east(g, body):
    """color0 cells with x > body.x1, in a band near body cy."""
    y0 = max(0, body["y0"] - 4)
    y1 = min(63, body["y1"] + 8)
    cells = []
    for y, x in np.argwhere(g == 0):
        x, y = int(x), int(y)
        if x > body["x1"] and y0 <= y <= y1:
            cells.append((x, y))
    cells.sort(key=lambda t: (t[0], t[1]))
    return cells


def frontier_cells(body, mid_x0=27):
    """Cells immediately east of body / accent toward mid."""
    cells = []
    x_lo = body["x1"] + 1
    x_hi = min(63, mid_x0 + 2)
    for x in range(x_lo, x_hi + 1):
        for y in range(body["y0"] - 1, body["y1"] + 3):
            if 0 <= y <= 63:
                cells.append((x, y))
    return cells


def main():
    key = _api_key()
    sess = Sess(key)
    rows = []
    stats = {"max_cx": 0.0, "max_x1": 0, "hits": []}
    hard = False
    try:
        sess.open()

        # ---- A: deep bay1 + env + click east color0 ----
        print("\n## A deep bay1 env + east color0")
        d, g = setup_bay1(sess, clear_climb=False, sink_extra=2)
        sp = sprite(g)
        print(f"  base cx={sp['body']['cx']} cy={sp['body']['cy']} h12={int((g==12).sum())}")
        for x0 in (39, 45, 51, 57, 39, 45):
            d2 = pad_c(sess, g, x0)
            if d2:
                g = plane(d2["frame"]); d = d2
        sp = sprite(g)
        zeros = color0_east(g, sp["body"])
        print(f"  east color0 n={len(zeros)} sample={zeros[:12]}")
        # also click some env-painted cells further east
        for x, y in zeros[:40]:
            d, g, hard = try_click(sess, d, g, x, y, rows, "A/c0", stats)
            if hard:
                break
        if not hard:
            # scan a grid east even if not color0
            bx1 = int(sprite(g)["body"]["x1"])
            by0 = int(sprite(g)["body"]["y0"])
            for x in range(bx1 + 1, min(64, bx1 + 18)):
                for y in range(by0, min(64, by0 + 10)):
                    if int(g[y, x]) in (0, 3, 5, 1):
                        d, g, hard = try_click(sess, d, g, x, y, rows, f"A/grid{int(g[y,x])}", stats)
                        if hard:
                            break
                if hard:
                    break

        # ---- B: ceiling frontier ----
        if not hard:
            print("\n## B ceiling frontier")
            d, g = setup_bay1(sess, clear_climb=True, sink_extra=0)
            sp = sprite(g)
            print(f"  ceil cx={sp['body']['cx']} cy={sp['body']['cy']} "
                  f"x1={sp['body']['x1']} y0={sp['body']['y0']} h12={int((g==12).sum())}")
            for x0 in (39, 45, 51, 57):
                d2 = pad_c(sess, g, x0)
                if d2:
                    g = plane(d2["frame"]); d = d2
            front = frontier_cells(sprite(g)["body"])
            print(f"  frontier n={len(front)}")
            for x, y in front:
                col = int(g[y, x])
                d, g, hard = try_click(sess, d, g, x, y, rows, f"B/f{col}", stats)
                if hard:
                    break
            if not hard:
                # accent east face
                acc = sprite(g)["accent"]
                if acc:
                    for x in range(acc["x1"] + 1, acc["x1"] + 6):
                        for y in range(acc["y0"], acc["y1"] + 1):
                            d, g, hard = try_click(sess, d, g, x, y, rows, "B/acc_e", stats)
                            if hard:
                                break
                        if hard:
                            break

        # ---- C: pad corners floor + ceil ----
        if not hard:
            print("\n## C pad corners @ deep")
            d, g = setup_bay1(sess, clear_climb=False, sink_extra=2)
            for x0 in (9, 15, 39, 45, 51, 57):
                for which in ("tl", "tr", "bl", "br"):
                    sp0 = sprite(g)
                    cx0 = sp0["body"]["cx"]
                    d2 = pad_corner(sess, g, x0, which)
                    if d2 is None:
                        continue
                    g2 = plane(d2["frame"])
                    sp1 = sprite(g2)
                    dx = sp1["body"]["cx"] - cx0
                    dy = sp1["body"]["cy"] - sp0["body"]["cy"]
                    odd = abs(dx) > 0.05 and round(abs(dx), 1) not in {3.0, 15.0}
                    row = {
                        "tag": f"C/pad{x0}_{which}",
                        "dx": dx, "dy": dy,
                        "cx1": sp1["body"]["cx"], "cy1": sp1["body"]["cy"],
                        "lv": d2.get("levels_completed"), "odd_dx": odd,
                    }
                    rows.append(row)
                    stats["max_cx"] = max(stats["max_cx"], sp1["body"]["cx"])
                    stats["max_x1"] = max(stats["max_x1"], sp1["body"]["x1"])
                    if odd or sp1["body"]["cx"] > 20.6 or (d2.get("levels_completed") or 0) >= 4:
                        print("*** HIT", row)
                        stats["hits"].append(row)
                        hard = True
                        break
                    if abs(dx) + abs(dy) > 0.1:
                        print(f"  {row['tag']} d=({dx:+.1f},{dy:+.1f}) cx={sp1['body']['cx']}")
                    g = g2; d = d2
                if hard:
                    break

        if not hard:
            print("\n## C2 pad corners @ ceiling")
            d, g = setup_bay1(sess, clear_climb=True)
            for x0 in (9, 15, 39, 45, 51, 57):
                for which in ("tl", "tr", "bl", "br"):
                    sp0 = sprite(g)
                    cx0 = sp0["body"]["cx"]
                    d2 = pad_corner(sess, g, x0, which)
                    if d2 is None:
                        continue
                    g2 = plane(d2["frame"])
                    sp1 = sprite(g2)
                    dx = sp1["body"]["cx"] - cx0
                    dy = sp1["body"]["cy"] - sp0["body"]["cy"]
                    odd = abs(dx) > 0.05 and round(abs(dx), 1) not in {3.0, 15.0}
                    row = {
                        "tag": f"C2/pad{x0}_{which}",
                        "dx": dx, "dy": dy,
                        "cx1": sp1["body"]["cx"], "cy1": sp1["body"]["cy"],
                        "lv": d2.get("levels_completed"), "odd_dx": odd,
                    }
                    rows.append(row)
                    stats["max_cx"] = max(stats["max_cx"], sp1["body"]["cx"])
                    if odd or sp1["body"]["cx"] > 20.6 or (d2.get("levels_completed") or 0) >= 4:
                        print("*** HIT", row)
                        stats["hits"].append(row)
                        hard = True
                        break
                    if abs(dx) + abs(dy) > 0.1:
                        print(f"  {row['tag']} d=({dx:+.1f},{dy:+.1f}) cx={sp1['body']['cx']}")
                    g = g2; d = d2
                    # if climbed away from ceil, stop corner spam for this pad
                if hard:
                    break

        # ---- D: bay0 ceiling east face (never hop) ----
        if not hard:
            print("\n## D bay0 ceiling east (no hop)")
            ent = enter_l4(sess)
            d, g = ent["data"], ent["frame"]
            # climb without convert if possible — or convert then climb (clears)
            # one-up then stuck; or sink convert then climb clears
            d2 = pad_c(sess, g, 9)  # up once
            g = plane(d2["frame"]); d = d2
            sp = sprite(g)
            print(f"  one-up cx={sp['body']['cx']} cy={sp['body']['cy']} y0={sp['body']['y0']}")
            for x0 in (39, 45, 51, 57):
                d2 = pad_c(sess, g, x0)
                if d2:
                    g = plane(d2["frame"]); d = d2
            front = frontier_cells(sprite(g)["body"], mid_x0=14)  # toward left window/east a bit
            # actually want east toward mid from bay0 — mid is far; click x up to 26
            body = sprite(g)["body"]
            for x in range(body["x1"] + 1, 28):
                for y in range(body["y0"], body["y1"] + 2):
                    d, g, hard = try_click(sess, d, g, x, y, rows, "D/east", stats)
                    if hard:
                        break
                if hard:
                    break

        reading = (
            "EAST_MICRO_FOUND" if stats["hits"]
            else (
                "NO_MICRO_EAST"
                if stats["max_cx"] <= 20.5 + 0.05
                else "CX_EXTENDED"
            )
        )
        out = {
            "rows_n": len(rows),
            "rows_moves": [r for r in rows if abs(r.get("dx") or 0) + abs(r.get("dy") or 0) > 0.1],
            "odd_or_hit": stats["hits"],
            "max_cx": stats["max_cx"],
            "max_x1": stats["max_x1"],
            "reading": reading,
            "hypothesis": "H56 micro-east / odd-dx without mid12",
            # keep full rows but trim noop noise for size
            "rows_nonzero_nd": [r for r in rows if (r.get("nd") or 0) > 0 or abs(r.get("dx") or 0) > 0.05],
        }
        print("\n## Summary")
        print("max_cx", stats["max_cx"], "max_x1", stats["max_x1"], "hits", len(stats["hits"]))
        print("READING:", reading)
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("wrote", OUT, "rows", len(rows))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
