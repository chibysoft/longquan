"""L4: enter-frame color map; click all color7 clusters; pad-semantics after c7."""
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

OUT = ROOT / "tests/fixtures/vc33_l4_c7_scan.json"
CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 7: "U", 9: "P", 11: "A", 12: "C"}


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
    info = {
        "dx": (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0,
        "dy": (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0,
        "cy": s1["body"]["cy"] if s1 else None,
        "cx": s1["body"]["cx"] if s1 else None,
        "nd": body_ndiff(g0, g2),
        "ch": body_changes(g0, g2),
        "lv": d2.get("levels_completed"),
        "acts": d2.get("available_actions"),
        "h12": int((g2 == 12).sum()),
    }
    print(
        f"{tag}x{x0} Δ=({info['dx']},{info['dy']}) cy={info['cy']} "
        f"nd={info['nd']} ch={info['ch']} lv={info['lv']} acts={info['acts']}"
    )
    return d2, g2, info


def color_clusters(g, color, min_n=1):
    return components(g, color, min_n=min_n, max_n=10**9)


def dump_full(g, y0=0, y1=63, x0=0, x1=63):
    for y in range(y0, y1 + 1):
        row = "".join(CHARS.get(int(g[y, x]), str(int(g[y, x]))[-1]) for x in range(x0, x1 + 1))
        # only print rows with non-blank interest
        if any(ch not in ". " for ch in row):
            print(f"{y:02d}|{row}")


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
    out = {"enter": {}, "c7_clicks": [], "post_c7_pads": [], "hits": []}
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        u, c = np.unique(g, return_counts=True)
        hist = {int(k): int(v) for k, v in zip(u, c)}
        print("ENTER hist", hist, "acts", d.get("available_actions"), "lv", d.get("levels_completed"))
        print("sum", summarize(g))
        # all components by color
        comps = {}
        for col in sorted(hist):
            if col in (3,):  # skip air
                continue
            comps[col] = color_clusters(g, col, min_n=1 if col != 0 else 4)
            print(f"  color{col} n_comp={len(comps[col])} "
                  f"sample={comps[col][:6]}")
        out["enter"] = {
            "hist": hist,
            "acts": d.get("available_actions"),
            "lv": d.get("levels_completed"),
            "comps": {str(k): v[:12] for k, v in comps.items()},
            "sprite": sprite(g),
            "gap": gap11(g),
        }
        print("\nfull non-empty rows (0-20):")
        dump_full(g, 0, 20)
        print("...")
        dump_full(g, 28, 63)

        # ---- A: click every color7 component centroid + corners ----
        print("\n==== A color7 clicks")
        c7s = comps.get(7, [])
        print("c7 components", c7s)
        for i, c7 in enumerate(c7s):
            targets = [
                (round(c7["cx"]), round(c7["cy"])),
                (c7["x0"], c7["y0"]),
                (c7["x1"], c7["y0"]),
                (c7["x0"], c7["y1"]),
                (c7["x1"], c7["y1"]),
            ]
            for x, y in targets:
                g0 = g
                d2 = click(sess, int(x), int(y))
                if d2 is None:
                    break
                g2 = plane(d2["frame"])
                nd = body_ndiff(g0, g2)
                ch = body_changes(g0, g2) if nd else {}
                info = {
                    "c7_i": i,
                    "xy": (int(x), int(y)),
                    "nd": nd,
                    "ch": ch,
                    "lv": d2.get("levels_completed"),
                    "acts": d2.get("available_actions"),
                    "hist7": int((g2 == 7).sum()),
                    "hist4": int((g2 == 4).sum()),
                }
                if nd or info["acts"] != d.get("available_actions") or info["lv"] != d.get("levels_completed"):
                    print(f"  c7({x},{y}) nd={nd} ch={ch} acts={info['acts']} lv={info['lv']} "
                          f"h7={info['hist7']} h4={info['hist4']}")
                    out["c7_clicks"].append(info)
                    out["hits"].append(info)
                g = g2
                d = d2
                if maybe_clear(d, sess):
                    return

        # ---- B: after c7 clicks, rematerialize pad map — did semantics change? ----
        print("\n==== B pad map after c7 (still at enter height)")
        base = []
        for x0 in (9, 15, 39, 45, 51, 57):
            d, g, info = pad(sess, d, g, x0, "B ")
            base.append({"x0": x0, **info})
            out["post_c7_pads"].append({"x0": x0, **info})
            if maybe_clear(d, sess):
                return
            # if moved down from 15, one up to stabilize? keep going for map
        print("pad effects after c7", [(p["x0"], p["dx"], p["dy"], p["ch"]) for p in base])

        # ---- C: H47 — at bay1 ceiling, does env ever paint y44-45 x30+? ----
        print("\n==== C env paint y44-45 x30+")
        # get to bay1 ceil fresh-ish from current or reenter
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g, _ = pad(sess, d, g, 15, "s ")
        c = components(g, 12, 1, 80)[0]
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        d, g, _ = pad(sess, d, g, 39, "hz ")
        for _ in range(5):
            g0 = g
            d, g, info = pad(sess, d, g, 15, "up ")
            if abs(info.get("dy") or 0) < 0.1:
                break
        for e in (39, 45, 51, 57) * 4:
            g0 = g
            d, g, info = pad(sess, d, g, e, "e ")
            zeros = [(int(x), int(y)) for y in (44, 45) for x in range(30, 48) if int(g[y, x]) == 0]
            if zeros:
                print("H47 HIT zeros y44-45", zeros)
                out["hits"].append({"H47": zeros})
            to0 = np.argwhere((g0 == 3) & (g == 0))
            hi = [(int(x), int(y)) for y, x in to0 if y <= 45 and x >= 30]
            if hi:
                print("H47 to0 high", hi)
                out["hits"].append({"H47_to0": hi})
        print("C final y44-45 x30-47", 
              {y: [int(g[y, x]) for x in range(30, 48)] for y in (44, 45)})

        # ---- D: H45 — left c12 rhythm: convert, arm, hop, return, rearm, hop×N watch levels ----
        print("\n==== D left-gate rhythm")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g, _ = pad(sess, d, g, 15, "s ")
        for cycle in range(6):
            if int((g == 12).sum()) == 0:
                # sink to reconvert
                while int((g == 12).sum()) == 0 and sprite(g)["body"]["cy"] < 54:
                    d, g, _ = pad(sess, d, g, 15 if sprite(g)["body"]["cy"] < 51 else 9, "rc ")
                    if abs(sprite(g)["body"]["cy"] - 51) < 1 and int((g == 12).sum()) == 0:
                        break
            if int((g == 12).sum()) == 0:
                print("no c12 cycle", cycle)
                break
            c = [x for x in components(g, 12, 1, 80) if x["cx"] < 20]
            if not c:
                c = components(g, 12, 1, 80)
            d2 = click(sess, round(c[0]["cx"]), round(c[0]["cy"]))
            g = plane(d2["frame"]); d = d2
            d, g, info = pad(sess, d, g, 39, f"D{cycle} ")
            print(f"  cycle{cycle} cx={info.get('cx')} lv={info.get('lv')} acts={info.get('acts')}")
            if maybe_clear(d, sess):
                return
            # hop back if in bay1
            if (info.get("cx") or 0) > 15:
                if int((g == 12).sum()):
                    c = components(g, 12, 1, 80)[0]
                    d2 = click(sess, round(c["cx"]), round(c["cy"]))
                    g = plane(d2["frame"]); d = d2
                d, g, info = pad(sess, d, g, 39, f"Db{cycle} ")

        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("done hits", len(out["hits"]), "lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
