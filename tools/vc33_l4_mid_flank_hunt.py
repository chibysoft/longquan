"""L4: at bay1 cy51 (post-hop, flanks live), env-hunt mid flanks at y45; H34 sink-onto-dig."""
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

OUT = ROOT / "tests/fixtures/vc33_l4_mid_flank_hunt.json"
CRIT = [(25, 45), (26, 45), (30, 45), (31, 45), (25, 44), (26, 44), (30, 44), (31, 44)]


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad(sess, d, g, x0, tag=""):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    g0 = g
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g, {}
    g2 = plane(d2["frame"])
    s0, s1 = sprite(g0), sprite(g2)
    to0 = np.argwhere((g0 == 3) & (g2 == 0))
    crit = {f"{x},{y}": int(g2[y, x]) for x, y in CRIT}
    info = {
        "dx": (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0,
        "dy": (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0,
        "cy": s1["body"]["cy"] if s1 else None,
        "crit": crit,
        "mid12": bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20]),
        "h12": int((g2 == 12).sum()),
        "lv": d2.get("levels_completed"),
        "to0_y45": [(int(x), int(y)) for y, x in to0 if y == 45],
        "to0_near_mid": [(int(x), int(y)) for y, x in to0 if 24 <= x <= 32 and y <= 45],
        "nd": body_ndiff(g0, g2),
    }
    flag = info["mid12"] or info["to0_near_mid"] or any(v == 0 for k, v in crit.items() if k.endswith(",45"))
    print(
        f"{tag}x{x0} Δ=({info['dx']},{info['dy']}) cy={info['cy']} "
        f"to0_y45={info['to0_y45']} near={info['to0_near_mid']} "
        f"crit45={[crit[k] for k in ('25,45','26,45','30,45','31,45')]} "
        f"mid12={info['mid12']} lv={info['lv']}{' ***' if flag else ''}"
    )
    return d2, g2, info


def setup_hop(sess):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        d, g, _ = pad(sess, d, g, 15, "s ")
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"]); d = d2
    d, g, _ = pad(sess, d, g, 39, "hz ")
    return d, g


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

        # A: floor env spam watching mid flanks
        print("\n==== A floor env mid-flank hunt")
        d, g = setup_hop(sess)
        print("post-hop zeros y45", [(int(x), int(y)) for y, x in np.argwhere(g == 0) if y == 45])
        for i, e in enumerate([39, 45, 51, 57] * 4):
            d, g, info = pad(sess, d, g, e, f"A{i} ")
            if info.get("to0_near_mid") or info.get("mid12") or any(
                info["crit"].get(k) == 0 for k in ("25,45", "26,45", "30,45", "31,45")
            ):
                hits.append({"A": info})
            if maybe_clear(d, sess):
                return

        # B: arm-clear dig at floor, env, rearm?, climb one watching y45
        print("\n==== B arm-clear then env then climb phase")
        d, g = setup_hop(sess)
        left = [c for c in components(g, 12, 1, 80) if c["cx"] < 20]
        if left:
            d2 = click(sess, round(left[0]["cx"]), round(left[0]["cy"]))
            g = plane(d2["frame"]); d = d2
            print("rearmed zeros y45", [(int(x), int(y)) for y, x in np.argwhere(g == 0) if y <= 45])
        for e in (39, 45, 51, 57, 39, 45):
            # charge may hop — catch it
            d, g, info = pad(sess, d, g, e, "B ")
            if abs(info.get("dx") or 0) > 0.1:
                print("hopped during B", info["dx"], "cy", info["cy"])
                # if back in bay0, re-hop
                if (info.get("dx") or 0) < 0:
                    if int((g == 12).sum()):
                        c = components(g, 12, 1, 80)[0]
                        d2 = click(sess, round(c["cx"]), round(c["cy"]))
                        g = plane(d2["frame"]); d = d2
                    d, g, info = pad(sess, d, g, 39, "Brehop ")
        # climb carefully
        for i in range(5):
            d, g, info = pad(sess, d, g, 15, f"Bup{i} ")
            z45 = [(int(x), int(y)) for y, x in np.argwhere(g == 0) if y == 45]
            print(f"  z45={z45} crit={info.get('crit')}")
            if info.get("mid12") or any(info.get("crit", {}).get(k) == 0 for k in ("25,45", "26,45")):
                hits.append({"Bup": info})
            if abs(info.get("dy") or 0) < 0.1:
                break
            if maybe_clear(d, sess):
                return

        # C: H34 — at ceiling, confirm sink exits mid y; try micro: click dig then up from cy45
        print("\n==== C ceiling sink exits mid (H34)")
        d, g = setup_hop(sess)
        for i in range(5):
            d, g, info = pad(sess, d, g, 15, f"Cup{i} ")
            if abs(info.get("dy") or 0) < 0.1:
                break
        sp = sprite(g)
        print("ceil accent", sp["accent"], "mid y1=45 dig46", int(g[46, 26]))
        # sink one
        d, g, info = pad(sess, d, g, 9, "Cdn ")
        sp = sprite(g)
        print("after sink accent", sp["accent"], "still in mid y?", sp["accent"]["y0"] <= 45,
              "crit", {f"{x},{y}": int(g[y, x]) for x, y in CRIT})

        # D: structural — can we get accent y1<=44 with dig at 45? needs y0<=39
        print("\n==== D force y0<40 attempts at ceil")
        # already at ceil; try pad15 corners + env + click above body
        for p in pads_sorted(g):
            if p["x0"] != 15:
                continue
            for corner in [(p["x0"], p["y0"]), (p["x1"], p["y0"]), (p["x0"], p["y1"]), (p["x1"], p["y1"])]:
                g0, s0 = g, sprite(g)
                d2 = click(sess, *corner)
                if d2 is None:
                    break
                g2 = plane(d2["frame"])
                s1 = sprite(g2)
                dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
                y0 = s1["body"]["y0"] if s1 else None
                if y0 is not None and y0 < 40:
                    print("BROKE CEILING", corner, y0)
                    hits.append({"broke": corner, "y0": y0})
                if abs(dy) > 0.1:
                    print("moved", corner, "dy", dy, "y0", y0)
                    # restore
                    d, g, _ = pad(sess, d, g, 15, "rest ")
                else:
                    g = g2; d = d2

        OUT.write_text(json.dumps({"hits": hits, "final_lv": d.get("levels_completed")}, indent=2, default=str), encoding="utf-8")
        print("done hits", hits, "lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
