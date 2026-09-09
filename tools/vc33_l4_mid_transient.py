"""L4 H42: at ceiling, rapid dn/up interleaved with mid click — dig↔mid 4-neighbor transient."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_changes, body_ndiff  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_mid_transient.json"


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
    mid12 = [c for c in components(g2, 12, 1, 80) if c["cx"] > 20]
    info = {
        "dx": (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0,
        "dy": (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0,
        "cy": s1["body"]["cy"] if s1 else None,
        "crit": {(x, y): int(g2[y, x]) for x, y in [(26, 45), (26, 46), (27, 45), (27, 46)]},
        "mid12": bool(mid12),
        "lv": d2.get("levels_completed"),
        "h12": int((g2 == 12).sum()),
        "nd": body_ndiff(g0, g2),
    }
    print(f"{tag}x{x0} Δ=({info['dx']},{info['dy']}) cy={info['cy']} crit={info['crit']} "
          f"mid12={info['mid12']} lv={info['lv']}")
    return d2, g2, info


def mid_click(sess, d, g, tag=""):
    mids = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
    if not mids:
        mids = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
    if not mids:
        return d, g, {}
    m = mids[0]
    g0 = g
    # click bottom-left corner of mid (closest to dig 26,46)
    xy = (m["x0"], m["y1"])
    d2 = click(sess, *xy)
    if d2 is None:
        return d, g, {}
    g2 = plane(d2["frame"])
    mid12 = [c for c in components(g2, 12, 1, 80) if c["cx"] > 20]
    info = {
        "xy": xy,
        "nd": body_ndiff(g0, g2),
        "ch": body_changes(g0, g2),
        "mid12": bool(mid12),
        "lv": d2.get("levels_completed"),
        "crit": {(x, y): int(g2[y, x]) for x, y in [(26, 45), (26, 46), (27, 45), (27, 46)]},
        "cy": sprite(g2)["body"]["cy"] if sprite(g2) else None,
        "cx": sprite(g2)["body"]["cx"] if sprite(g2) else None,
    }
    if info["nd"] or info["mid12"] or int(info["lv"] or 0) >= 4 or abs((info["cx"] or 0) - (sprite(g0)["body"]["cx"] if sprite(g0) else 0)) > 0.1:
        print(f"{tag}mid{xy} nd={info['nd']} ch={info['ch']} mid12={info['mid12']} "
              f"cx={info['cx']} cy={info['cy']} lv={info['lv']} crit={info['crit']}")
    return d2, g2, info


def setup_ceil(sess):
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
        d, g = setup_ceil(sess)
        print("CEIL", sprite(g), "crit", {(x, y): int(g[y, x]) for x, y in [(26, 45), (26, 46), (27, 45)]})

        # Pattern A: dn, midclick, up  × N
        print("\n==== A dn-mid-up")
        for i in range(10):
            d, g, info = pad(sess, d, g, 9, f"A{i}dn ")
            d, g, info = mid_click(sess, d, g, f"A{i}")
            if info.get("mid12") or int(info.get("lv") or 0) >= 4:
                hits.append({"A_mid": info})
            if maybe_clear(d, sess):
                return
            # also click dig and seam
            for x, y in [(26, 46), (26, 45), (27, 45)]:
                g0 = g
                d2 = click(sess, x, y)
                if d2 is None:
                    break
                g2 = plane(d2["frame"])
                if body_ndiff(g0, g2) or bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20]):
                    print(f"A{i}cell({x},{y}) nd={body_ndiff(g0,g2)} mid12="
                          f"{bool([c for c in components(g2,12,1,80) if c['cx']>20])} lv={d2.get('levels_completed')}")
                    hits.append({"cell": (x, y)})
                g = g2; d = d2
                if maybe_clear(d, sess):
                    return
            d, g, info = pad(sess, d, g, 15, f"A{i}up ")
            if info.get("mid12") or int(info.get("lv") or 0) >= 4:
                hits.append({"A_up": info})
            if maybe_clear(d, sess):
                return
            # ensure back at ceil
            if abs(info.get("dy") or 0) < 0.1 and (info.get("cy") or 0) > 42.5:
                d, g, _ = pad(sess, d, g, 15, "fix ")

        # Pattern B: midclick WHILE at ceil (dig adjacent), then dn, then up immediately
        print("\n==== B mid-dn-up burst")
        d, g = setup_ceil(sess)
        for i in range(8):
            d, g, info = mid_click(sess, d, g, f"B{i}a")
            d, g, info = pad(sess, d, g, 9, f"B{i}dn ")
            d, g, info = mid_click(sess, d, g, f"B{i}b")
            d, g, info = pad(sess, d, g, 15, f"B{i}up ")
            if info.get("mid12") or int(info.get("lv") or 0) >= 4:
                hits.append({"B": info})
            if maybe_clear(d, sess):
                return

        # Pattern C: at ceil, click (26,46) then mid corner then pad15 (noop) then pad9
        print("\n==== C dig-mid-pad order")
        d, g = setup_ceil(sess)
        for i in range(6):
            for x, y, tag in [(26, 46, "dig"), (27, 45, "mid"), (26, 45, "seam")]:
                g0 = g
                d2 = click(sess, x, y)
                if d2 is None:
                    break
                g2 = plane(d2["frame"])
                nd = body_ndiff(g0, g2)
                mid12 = bool([c for c in components(g2, 12, 1, 80) if c["cx"] > 20])
                if nd or mid12 or d2.get("levels_completed") != d.get("levels_completed"):
                    print(f"C{i}{tag} nd={nd} mid12={mid12} lv={d2.get('levels_completed')} ch={body_changes(g0,g2)}")
                    hits.append({"C": tag, "nd": nd, "mid12": mid12})
                g = g2; d = d2
                if maybe_clear(d, sess):
                    return
            d, g, _ = pad(sess, d, g, 9, f"C{i}dn ")
            d, g, _ = pad(sess, d, g, 15, f"C{i}up ")

        OUT.write_text(json.dumps({"hits": hits, "final_lv": d.get("levels_completed")}, indent=2, default=str), encoding="utf-8")
        print("done hits", hits, "lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
