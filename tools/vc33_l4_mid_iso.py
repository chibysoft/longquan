"""L4: pre-convert zero map; mid-isomorphic flank targets; sink-vs-climb convert."""
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

OUT = ROOT / "tests/fixtures/vc33_l4_convert_cmp.json"  # append mid_iso section
OUT2 = ROOT / "tests/fixtures/vc33_l4_mid_iso.json"
CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 11: "A", 12: "C"}


def dump(g, y0=40, y1=55, x0=0, x1=35):
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
        return d, g, {}
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    info = {
        "dx": (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0,
        "dy": (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0,
        "cy": s1["body"]["cy"] if s1 else None,
        "h12": int((g2 == 12).sum()),
        "mid12": bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20]),
        "lv": d2.get("levels_completed"),
        "nd": body_ndiff(g0, g2),
        "ch": body_changes(g0, g2),
    }
    print(
        f"{tag}x{x0} Δ=({info['dx']},{info['dy']}) cy={info['cy']} "
        f"h12={info['h12']} mid12={info['mid12']} lv={info['lv']}"
    )
    return d2, g2, info


def zeros(g, ymax=60):
    return sorted((int(x), int(y)) for y, x in np.argwhere(g == 0) if y <= ymax)


def flank_pair(win):
    # left convert used x0-2 and x1+2 at high y
    return (win["x0"] - 2, win["x1"] + 2)


def report_win(g, tag, win):
    lx, rx = flank_pair(win)
    col_l = [int(g[y, lx]) for y in range(win["y0"], win["y1"] + 1)]
    col_r = [int(g[y, rx]) for y in range(win["y0"], win["y1"] + 1)]
    gap_cols = {}
    for x in range(win["x0"] - 3, win["x1"] + 4):
        gap_cols[x] = [int(g[y, x]) for y in range(win["y0"], min(63, win["y1"] + 2) + 1)]
    z_in = [(x, y) for x, y in zeros(g, win["y1"]) if win["y0"] <= y <= win["y1"] and win["x0"] - 3 <= x <= win["x1"] + 3]
    print(f"\n[{tag}] win={win['x0']}-{win['x1']},{win['y0']}-{win['y1']} color={win.get('color')}")
    print(f"  flank_xs=({lx},{rx}) col_l={col_l[-6:]} col_r={col_r[-6:]}")
    print(f"  zeros_near_win_y={z_in}")
    print(f"  sprite={sprite(g)}")
    return {
        "flank_xs": (lx, rx),
        "col_l_tail": col_l[-6:],
        "col_r_tail": col_r[-6:],
        "zeros_near": z_in,
        "sprite": sprite(g),
        "win": win,
    }


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
    out = {}
    try:
        sess.open()

        # ---- A: frame-by-frame left convert ----
        print("\n==== A left convert frames")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        left = [c for c in components(g, 1, 4, 80) if c["cx"] < 20][0]
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]
        out["enter_left"] = report_win(g, "enter_left", left)
        out["enter_mid"] = report_win(g, "enter_mid", mid)
        dump(g)

        # one down (pre-convert)
        d, g, _ = pad(sess, d, g, 15, "pre ")
        left = [c for c in components(g, 1, 4, 80) if c["cx"] < 20][0]
        out["pre_convert"] = report_win(g, "pre_convert", left)
        print("all zeros y<=54", [(x, y) for x, y in zeros(g, 54) if x < 30])
        dump(g)

        # second down (convert)
        d, g, _ = pad(sess, d, g, 15, "cvt ")
        left12 = components(g, 12, 1, 80)[0]
        out["post_convert"] = report_win(g, "post_convert", {**left12, "color": 12})
        print("all zeros y<=54", [(x, y) for x, y in zeros(g, 54) if x < 30])
        dump(g)

        # ---- B: bay1 ceiling mid isomorphic report ----
        print("\n==== B bay1 ceiling mid iso")
        c = left12
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        d, g, _ = pad(sess, d, g, 39, "hz ")
        for i in range(5):
            d, g, info = pad(sess, d, g, 15, f"up{i} ")
            if abs(info.get("dy") or 0) < 0.1:
                break
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]
        out["ceil_mid"] = report_win(g, "ceil_mid", mid)
        lx, rx = flank_pair(mid)
        print(f"  mid flank cells: ({lx},45)={int(g[45,lx])} ({rx},45)={int(g[45,rx])}")
        print(f"  seam x24-26 y44-46: { {(x,y): int(g[y,x]) for x in (24,25,26) for y in (44,45,46)} }")
        dump(g, 34, 50, 15, 35)

        # ---- C: try induce mid flanks by clicking mid while dig at y46 touches ----
        print("\n==== C induce / alternate convert triggers")
        trials = []
        # C1: click mid bottom / flank targets / seam
        for x, y, tag in [
            (28, 45, "midbot"),
            (27, 45, "midL"),
            (29, 45, "midR"),
            (lx, 45, "flankL"),
            (rx, 45, "flankR"),
            (26, 45, "seam"),
            (26, 46, "dig"),
            (30, 45, "east"),
            (28, 44, "midin"),
        ]:
            g0 = g
            d2 = click(sess, x, y)
            if d2 is None:
                break
            g2 = plane(d2["frame"])
            nd = body_ndiff(g0, g2)
            mid12 = bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20])
            if nd or mid12 or d2.get("levels_completed") != d.get("levels_completed"):
                print(f"  {tag}({x},{y}) nd={nd} ch={body_changes(g0,g2)} mid12={mid12} lv={d2.get('levels_completed')}")
                trials.append({"tag": tag, "nd": nd, "mid12": mid12, "lv": d2.get("levels_completed")})
            g = g2; d = d2
            if maybe_clear(d, sess):
                return

        # C2: dn onto dig then immediately click mid / up
        d, g, _ = pad(sess, d, g, 9, "dn ")
        print("after dn crit", {(x, y): int(g[y, x]) for x in (24, 25, 26) for y in (44, 45, 46)})
        print("after dn mid", report_win(g, "dn_mid", [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0] if components(g, 1, 4, 80) else mid))
        for x, y, tag in [(28, 45, "mid"), (26, 46, "dig"), (26, 45, "seam")]:
            g0 = g
            d2 = click(sess, x, y)
            if d2 is None:
                break
            g2 = plane(d2["frame"])
            nd = body_ndiff(g0, g2)
            if nd or bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20]):
                print(f"  dn+{tag} nd={nd} mid12={[c for c in components(g2,12,1,80) if c['cx']>20]}")
            g = g2; d = d2
        d, g, info = pad(sess, d, g, 15, "up ")
        if info.get("mid12") or int(info.get("lv") or 0) >= 4:
            trials.append({"tag": "dn_up", **info})
        if maybe_clear(d, sess):
            return

        # ---- D: falsify — accent enter color1? measure overlap left vs mid ----
        print("\n==== D accent∩window cells")
        # re-enter path for left pre/post
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        d, g, _ = pad(sess, d, g, 15, "d1 ")
        sp = sprite(g)
        left = [c for c in components(g, 1, 4, 80) if c["cx"] < 20][0]
        # count accent cells inside left window bbox
        def overlap_count(g, win, color=11):
            n = 0
            for y in range(win["y0"], win["y1"] + 1):
                for x in range(win["x0"], win["x1"] + 1):
                    if int(g[y, x]) == color:
                        n += 1
            return n
        print("pre accent∩left", overlap_count(g, left), "accent", sp["accent"])
        d, g, _ = pad(sess, d, g, 15, "d2 ")
        left12 = components(g, 12, 1, 80)[0]
        print("post accent∩left12", overlap_count(g, left12), "accent∩c12", overlap_count(g, left12, 12))
        # hop climb mid
        d2 = click(sess, round(left12["cx"]), round(left12["cy"]))
        g = plane(d2["frame"]); d = d2
        d, g, _ = pad(sess, d, g, 39, "hz ")
        for _ in range(5):
            d, g, info = pad(sess, d, g, 15, "u ")
            if abs(info.get("dy") or 0) < 0.1:
                break
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]
        sp = sprite(g)
        print("ceil accent∩mid", overlap_count(g, mid), "accent", sp["accent"], "body", sp["body"])
        out["overlap"] = {
            "ceil_accent_in_mid": overlap_count(g, mid),
            "accent": sp["accent"],
        }

        # ---- E: at ceil, try to push accent into mid via env staircase on right then... ----
        print("\n==== E env xmax lift near mid then mid click")
        for e in (39, 39, 45, 45, 51):
            d, g, info = pad(sess, d, g, e, f"e{e} ")
            # track x30 y45
            print(f"  (30,45)={int(g[45,30])} (30,46)={int(g[46,30])} dig_xmax_y46="
                  f"{max([x for x in range(64) if int(g[46,x])==0] or [-1])}")
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
        if mid:
            d2 = click(sess, round(mid[0]["cx"]), round(mid[0]["cy"]))
            if d2:
                g2 = plane(d2["frame"])
                print("midclick after env nd", body_ndiff(g, g2), "mid12",
                      [c for c in components(g2, 12, 1, 80) if c["cx"] > 20],
                      "lv", d2.get("levels_completed"))
                g = g2; d = d2
        if maybe_clear(d, sess):
            return

        # ---- F: gap soft-clear from best y with env opening east ----
        print("\n==== F gap path")
        gp = gap11(g)
        if gp:
            d2 = click(sess, round(gp["cx"]), round(gp["cy"]))
            if d2:
                print("gap click lv", d2.get("levels_completed"), "nd", body_ndiff(g, plane(d2["frame"])))
                g = plane(d2["frame"]); d = d2

        out["trials"] = trials
        out["final_lv"] = d.get("levels_completed")
        OUT2.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("done lv", d.get("levels_completed"), "wrote", OUT2)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
