"""L4 H58 (e): left-convert side effects — grow color0 toward mid at y45.

Known: convert paints flanks (10/16,45) AND deep dig x15-26 @ y55-57.
Stuck: y45 never gets color0 at x>=20. Prior flank_east couldn't expand post-convert.

New knives:
  A) pre-path variants before convert — compare y45 zeros + deep zeros
  B) post-convert: grow dig UP from (26,55) toward y45 by clicking column 26
  C) post-convert: east chain click (16..26, 45) unarmed
  D) double-convert (sink past 12→1, re-convert) — flank set change?
  E) one-up then sink-convert — dig trail at convert moment

Hit: y45 xmax>=20 OR (26,45)==0 OR mid12 OR levels>=4.
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

OUT = ROOT / "tests/fixtures/vc33_l4_flank_grow.json"


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad(sess, g, x0):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    return click(sess, int(round(p["cx"])), int(round(p["cy"])))


def zeros_y(g, y):
    return sorted(int(x) for x in range(64) if int(g[y, x]) == 0)


def zeros_band(g, y0, y1):
    return sorted(
        (int(x), int(y)) for y, x in np.argwhere(g == 0) if y0 <= y <= y1
    )


def flank_snap(g, d=None):
    z45 = zeros_y(g, 45)
    z44 = zeros_y(g, 44)
    deep = zeros_band(g, 55, 57)
    mid12 = bool([c for c in components(g, 12, 1, 80) if c["cx"] > 20])
    sp = sprite(g)
    return {
        "cy": sp["body"]["cy"] if sp else None,
        "cx": sp["body"]["cx"] if sp else None,
        "h12": int((g == 12).sum()),
        "lv": None if d is None else d.get("levels_completed"),
        "z45": z45,
        "z44": z44,
        "xmax45": max(z45) if z45 else None,
        "deep": deep,
        "deep_xmax": max((x for x, _ in deep), default=None),
        "c26_45": int(g[45, 26]),
        "c26_46": int(g[46, 26]),
        "c26_54": int(g[54, 26]),
        "c26_55": int(g[55, 26]),
        "mid12": mid12,
        "z_le45": zeros_band(g, 0, 45),
    }


def is_hit(s):
    return bool(
        (s.get("xmax45") or 0) >= 20
        or s.get("c26_45") == 0
        or s.get("mid12")
        or (s.get("lv") or 0) >= 4
        or any(x >= 20 for x, y in s.get("z_le45") or [] if y == 45)
    )


def enter(sess):
    ent = enter_l4(sess)
    return ent["data"], ent["frame"]


def sink_until_c12(sess, d, g, limit=10):
    pre = None
    for _ in range(limit):
        if int((g == 12).sum()) > 0:
            return d, g, pre
        pre = g.copy()
        d2 = pad(sess, g, 15)
        if d2 is None:
            break
        g = plane(d2["frame"]); d = d2
    return d, g, pre


def convert_delta_zeros(g_pre, g_post):
    cells = []
    for y in range(64):
        for x in range(64):
            a, b = int(g_pre[y, x]), int(g_post[y, x])
            if a != b:
                cells.append((x, y, a, b))
    z30 = [(x, y) for x, y, a, b in cells if a == 3 and b == 0]
    return {
        "n_diff": len(cells),
        "n_3to0": len(z30),
        "z30_y45": sorted((x, y) for x, y in z30 if y == 45),
        "z30_xmax_y45": max((x for x, y in z30 if y == 45), default=None),
        "z30_deep": sorted((x, y) for x, y in z30 if y >= 55),
        "z30_xmax": max((x for x, y in z30), default=None),
        "z30_ymin": min((y for x, y in z30), default=None),
    }


def main():
    key = _api_key()
    sess = Sess(key)
    rows = []
    hits = []
    try:
        sess.open()

        # ---- A: plain convert ----
        def trial_convert(label, prep_fn):
            d, g = enter(sess)
            d, g = prep_fn(sess, d, g)
            d, g, pre = sink_until_c12(sess, d, g)
            assert int((g == 12).sum()) > 0, label
            post = flank_snap(g, d)
            delta = convert_delta_zeros(pre, g) if pre is not None else None
            row = {"label": label, "post": post, "delta": delta, "hit": is_hit(post)}
            rows.append(row)
            print(
                f"| {label:28s} | xmax45={post['xmax45']} z45={post['z45']} "
                f"deep_xmax={post['deep_xmax']} c26_45={post['c26_45']} "
                f"c26_55={post['c26_55']} | delta_y45={delta['z30_y45'] if delta else None}"
            )
            if row["hit"]:
                hits.append(row)
                print("*** HIT", label)
            return d, g, pre

        def prep_plain(s, d, g):
            return d, g

        def prep_oneup(s, d, g):
            d2 = pad(s, g, 9)
            return d2, plane(d2["frame"])

        def prep_env(s, d, g):
            for x0 in (39, 45, 51, 57):
                d2 = pad(s, g, x0)
                if d2:
                    g = plane(d2["frame"]); d = d2
            return d, g

        def prep_wiggle(s, d, g):
            d2 = pad(s, g, 9)
            g = plane(d2["frame"]); d = d2
            d2 = pad(s, g, 15)
            g = plane(d2["frame"]); d = d2
            d2 = pad(s, g, 9)
            return d2, plane(d2["frame"])

        print("\n## A convert pre-path variants")
        trial_convert("A/plain", prep_plain)
        trial_convert("A/oneup", prep_oneup)
        trial_convert("A/env_pre", prep_env)
        trial_convert("A/wiggle", prep_wiggle)

        # ---- D: double convert ----
        print("\n## D double convert")
        d, g = enter(sess)
        d, g, _ = sink_until_c12(sess, d, g)
        # sink past clear
        for _ in range(4):
            if int((g == 12).sum()) == 0:
                break
            d2 = pad(sess, g, 15)
            if d2 is None:
                break
            g = plane(d2["frame"]); d = d2
        # climb/sink back to convert
        for _ in range(6):
            if int((g == 12).sum()) > 0:
                break
            # may need pad9 then pad15
            cy = sprite(g)["body"]["cy"]
            if cy > 51.5:
                d2 = pad(sess, g, 9)  # up toward 51
            else:
                d2 = pad(sess, g, 15)
            if d2 is None:
                break
            g = plane(d2["frame"]); d = d2
        # if still no c12, sink
        d, g, pre2 = sink_until_c12(sess, d, g)
        post = flank_snap(g, d)
        delta = convert_delta_zeros(pre2, g) if pre2 is not None else None
        row = {"label": "D/double", "post": post, "delta": delta, "hit": is_hit(post)}
        rows.append(row)
        print(
            f"| D/double                     | xmax45={post['xmax45']} z45={post['z45']} "
            f"deep_xmax={post['deep_xmax']} c26_45={post['c26_45']} | y45={delta['z30_y45'] if delta else None}"
        )
        if row["hit"]:
            hits.append(row)

        # ---- B: grow dig UP column 26 ----
        print("\n## B grow dig UP col26 (post plain convert)")
        d, g = enter(sess)
        d, g, _ = sink_until_c12(sess, d, g)
        base = flank_snap(g, d)
        print(f"  base xmax45={base['xmax45']} c26_55={base['c26_55']} c26_45={base['c26_45']}")
        # click upward from deep toward mid
        for y in range(57, 43, -1):
            for x in (26, 25, 24, 20, 18, 16):
                if int(g[y, x]) not in (0, 3):
                    continue
                g0 = g.copy()
                s0 = flank_snap(g, d)
                d2 = click(sess, x, y)
                if d2 is None:
                    continue
                g2 = plane(d2["frame"])
                s1 = flank_snap(g2, d2)
                ch = body_changes(g0, g2) if body_ndiff(g0, g2) else {}
                grew = (s1["xmax45"] or -1) > (s0["xmax45"] or -1) or s1["c26_45"] != s0["c26_45"]
                if body_ndiff(g0, g2) or grew:
                    print(
                        f"  click({x},{y}) col={int(g0[y,x])} nd={body_ndiff(g0,g2)} "
                        f"xmax45 {s0['xmax45']}->{s1['xmax45']} c26_45 {s0['c26_45']}->{s1['c26_45']} "
                        f"h12 {s0['h12']}->{s1['h12']} ch={ch}"
                    )
                row = {
                    "label": f"B/up_{x}_{y}",
                    "post": s1,
                    "grew": grew,
                    "hit": is_hit(s1),
                    "ch": ch,
                }
                rows.append(row)
                if row["hit"]:
                    hits.append(row)
                    print("*** HIT", row["label"])
                g = g2; d = d2
                if int((g == 12).sum()) == 0 and s0["h12"] > 0:
                    print("  c12 cleared — stop B")
                    break
            else:
                continue
            break

        # ---- C: east chain on y45 ----
        print("\n## C east chain y45 (fresh convert)")
        d, g = enter(sess)
        d, g, _ = sink_until_c12(sess, d, g)
        print(f"  start z45={zeros_y(g, 45)}")
        for x in range(16, 28):
            g0 = g.copy()
            s0 = flank_snap(g, d)
            d2 = click(sess, x, 45)
            if d2 is None:
                continue
            g2 = plane(d2["frame"])
            s1 = flank_snap(g2, d2)
            nd = body_ndiff(g0, g2)
            if nd or s1["xmax45"] != s0["xmax45"]:
                print(
                    f"  click({x},45) was={int(g0[45,x])} nd={nd} "
                    f"xmax45 {s0['xmax45']}->{s1['xmax45']} z45={s1['z45']} "
                    f"c26_45={s1['c26_45']} h12={s1['h12']}"
                )
            row = {
                "label": f"C/chain_{x}",
                "post": s1,
                "hit": is_hit(s1),
                "nd": nd,
            }
            rows.append(row)
            if row["hit"]:
                hits.append(row)
                print("*** HIT", row["label"])
            g = g2; d = d2

        # ---- E: oneup convert then immediately B-lite on col26 ----
        print("\n## E oneup-convert then col26 up-clicks")
        d, g = enter(sess)
        d2 = pad(sess, g, 9)
        g = plane(d2["frame"]); d = d2
        d, g, pre = sink_until_c12(sess, d, g)
        post = flank_snap(g, d)
        print(f"  oneup convert xmax45={post['xmax45']} deep_xmax={post['deep_xmax']} c26_55={post['c26_55']}")
        rows.append({
            "label": "E/oneup_convert",
            "post": post,
            "delta": convert_delta_zeros(pre, g) if pre is not None else None,
            "hit": is_hit(post),
        })
        for y in (55, 54, 53, 52, 51, 50, 49, 48, 47, 46, 45):
            d2 = click(sess, 26, y)
            if d2 is None:
                continue
            g2 = plane(d2["frame"])
            s1 = flank_snap(g2, d2)
            if s1["c26_45"] == 0 or (s1["xmax45"] or 0) >= 20:
                print(f"*** HIT E click(26,{y})", s1)
                hits.append({"label": f"E/26_{y}", "post": s1, "hit": True})
            g = g2; d = d2

        reading = "FLANK_GROW_HIT" if hits else "NO_FLANK_GROW"
        # summarize A deltas
        a_sum = {
            r["label"]: {
                "xmax45": r["post"]["xmax45"],
                "z45": r["post"]["z45"],
                "deep_xmax": r["post"]["deep_xmax"],
                "delta_y45": (r.get("delta") or {}).get("z30_y45"),
            }
            for r in rows if r["label"].startswith("A/") or r["label"].startswith("D/")
        }
        out = {
            "hits": hits,
            "reading": reading,
            "a_summary": a_sum,
            "n_rows": len(rows),
            "rows_signal": [r for r in rows if r.get("hit") or r.get("grew")],
            "hypothesis": "H58 convert flank/dig grow toward mid y45",
        }
        print("\n## Summary")
        print("a_summary", json.dumps(a_sum, indent=2))
        print("hits", len(hits))
        print("READING:", reading)
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
