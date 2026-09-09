"""L4: falsify mid-gate necessity — soft align / gap ticks / mid bbox morph."""
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
from tools.vc33_l4_pad_map import components, enter_l4, gap11, sprite, summarize  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_soft_clear.json"


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad(sess, d, g, x0, tag=""):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    s0 = sprite(g)
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g, 0, 0
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
    lv = d2.get("levels_completed")
    if abs(dx) + abs(dy) > 0.1 or lv != d.get("levels_completed"):
        print(f"{tag}x{x0} Δ=({dx},{dy}) cy={s1['body']['cy'] if s1 else None} lv={lv}")
    if lv and int(lv) >= 4:
        print("CLEAR via pad", x0)
    return d2, g2, dx, dy


def dist(g):
    sp, gp = sprite(g), gap11(g)
    if not sp or not sp.get("accent") or not gp:
        return 999
    a = sp["accent"]
    return abs(a["cx"] - gp["cx"]) + abs(a["cy"] - gp["cy"]), abs(a["cy"] - gp["cy"]), abs(a["cx"] - gp["cx"])


def mid_bbox(g):
    m = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
    m12 = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
    return m[0] if m else (m12[0] if m12 else None)


def arm_hop(sess, hop=39):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        d, g, _, _ = pad(sess, d, g, 15, "s ")
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"])
    d = d2
    d, g, _, _ = pad(sess, d, g, hop, "hz ")
    return d, g


def main():
    key = _api_key()
    sess = Sess(key)
    log = []
    try:
        sess.open()
        # A: minimize manhattan to gap; watch levels / mid morph / gap morph
        d, g = arm_hop(sess, 39)
        best = dist(g)
        print("start bay1", best, "mid", mid_bbox(g), "gap", gap11(g))
        # climb to ceiling (closest y to gap we'll get in pit)
        for i in range(5):
            d, g, _, dy = pad(sess, d, g, 15, f"up{i} ")
            dxy = dist(g)
            mb, gp = mid_bbox(g), gap11(g)
            print(f"up{i} dist={dxy} mid_y1={mb['y1'] if mb else None} gap={gp} lv={d.get('levels_completed')}")
            log.append({"step": f"up{i}", "dist": dxy, "mid": mb, "gap": gp, "lv": d.get("levels_completed")})
            if int(d.get("levels_completed") or 0) >= 4:
                break
            if abs(dy) < 0.1:
                break
        # at ceiling: click gap, mid, beam, accent, every pad
        gp = gap11(g)
        for xy, tag in [
            ((round(gp["cx"]), round(gp["cy"])), "gap"),
            ((43, 29), "gap2"),
            ((28, 40), "mid"),
            ((28, 45), "midbot"),
            ((26, 46), "c0"),
            ((20, 42), "body"),
            ((5, 45), "far"),
        ]:
            g0 = g
            lv0 = d.get("levels_completed")
            d2 = click(sess, *xy)
            if not d2:
                continue
            g = plane(d2["frame"])
            d = d2
            nd = body_ndiff(g0, g)
            if nd or d.get("levels_completed") != lv0:
                print(f"click {tag}{xy} nd={nd} ch={body_changes(g0,g)} lv={d.get('levels_completed')}")
            if int(d.get("levels_completed") or 0) >= 4:
                print("CLEAR click", tag)
                break

        # B: fresh — hop15 (higher land), climb, same
        print("\n=== hop15 path")
        d, g = arm_hop(sess, 15)
        print("land", dist(g), sprite(g))
        for i in range(4):
            d, g, _, dy = pad(sess, d, g, 15, f"hup{i} ")
            print(f"hup{i} dist={dist(g)} lv={d.get('levels_completed')} mid={mid_bbox(g)}")
            if abs(dy) < 0.1 or int(d.get("levels_completed") or 0) >= 4:
                break
        # wiggle at best y watching levels only
        for i in range(8):
            for x0 in (9, 15, 39, 45):
                lv0 = d.get("levels_completed")
                mb0 = mid_bbox(g)
                gp0 = gap11(g)
                d, g, dx, dy = pad(sess, d, g, x0, f"w{i} ")
                mb1, gp1 = mid_bbox(g), gap11(g)
                if mb0 and mb1 and (mb0["y0"], mb0["y1"]) != (mb1["y0"], mb1["y1"]):
                    print("MID MORPH", mb0, "->", mb1)
                if gp0 and gp1 and (gp0["y0"], gp0["x0"]) != (gp1["y0"], gp1["x0"]):
                    print("GAP MORPH", gp0, "->", gp1)
                if d.get("levels_completed") != lv0:
                    print("LEVEL CHANGE", lv0, "->", d.get("levels_completed"))
                if int(d.get("levels_completed") or 0) >= 4:
                    print("CLEAR")
                    break
            else:
                continue
            break

        # C: left bay only — climb ceiling, sink convert, arm, hop, never climb — just spam
        print("\n=== floor spam with c12")
        d, g = arm_hop(sess, 39)
        for i in range(12):
            lv0 = d.get("levels_completed")
            # alternate env without reverse: charge spent so env safe
            d, g, _, _ = pad(sess, d, g, 45, "e ")
            d, g, _, _ = pad(sess, d, g, 39, "e2 ")
            if d.get("levels_completed") != lv0:
                print("LEVEL", d.get("levels_completed"))
            # re-activate c12 by down-up around 51 if killed
            if int((g == 12).sum()) == 0:
                d, g, _, _ = pad(sess, d, g, 9, "dn ")
                if int((g == 12).sum()) == 0:
                    d, g, _, _ = pad(sess, d, g, 15, "up ")
            if int(d.get("levels_completed") or 0) >= 4:
                print("CLEAR floor")
                break

        out = {"log": log, "final": summarize(g), "levels": d.get("levels_completed"), "dist": dist(g)}
        OUT.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
        print("final", out["levels"], out["dist"])
        if int(d.get("levels_completed") or 0) >= 4:
            (ROOT / "tests/fixtures/vc33_l4_clear_frame.json").write_text(
                json.dumps({"frame": d["frame"], "levels": d.get("levels_completed")}, indent=2),
                encoding="utf-8",
            )
            d1 = sess.action("ACTION1")
            (ROOT / "tests/fixtures/vc33_l5_frame_live.json").write_text(
                json.dumps({"frame": d1["frame"], "levels": d1.get("levels_completed")}, indent=2),
                encoding="utf-8",
            )
            print("synced L5", d1.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
