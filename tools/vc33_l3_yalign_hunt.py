"""vc33 L3: Y-align each accent to same-color gap; watch levels."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l3_probe import (  # noqa: E402
    FIXTURE_L3_CLEAR,
    FIXTURE_L4,
    Sess,
    body_ndiff,
    enter_l3,
    gaps_on_beams,
    pads_sorted,
    plane,
    small_sprites,
    summarize,
)

OUT = ROOT / "tests" / "fixtures" / "vc33_l3_yalign_hunt.json"


def accent_gap_pairs(g):
    sps = small_sprites(g)
    gaps = {gp["color"]: gp for gp in gaps_on_beams(g)}
    pairs = []
    for s in sps:
        if not s["accent"]:
            continue
        ac = s["accent"]["color"]
        if ac not in gaps:
            continue
        gp = gaps[ac]
        pairs.append({
            "color": ac,
            "acc": s["accent"],
            "body": s["body"],
            "gap": gp,
            "dy": s["accent"]["cy"] - gp["cy"],
            "dx": s["accent"]["cx"] - gp["cx"],
            "y_aligned": s["accent"]["y0"] <= gp["cy"] <= s["accent"]["y1"]
            or abs(s["accent"]["cy"] - gp["cy"]) < 1.0,
            # L1-style: same y range? gaps are 1-row; check accent covers gap y
            "y_match": s["accent"]["y0"] <= gp["y0"] <= s["accent"]["y1"],
            "x_match": s["accent"]["x0"] == gp["x0"] and s["accent"]["x1"] == gp["x1"],
        })
    return pairs


def click_pad_x(sess, g, x0):
    pad = next(p for p in pads_sorted(g) if p["x0"] == x0)
    xy = (int(round(pad["cx"])), int(round(pad["cy"])))
    d = sess.click(*xy)
    return d, plane(d["frame"]), list(xy)


def main():
    # From pad_map:
    # 14: x12=-y, x16=+y
    # 15: x34=+y, x38=-y
    # 11: unsure; x46 gave +y on 11 (and -y on 15?)
    # env: x24, x28; noop x50
    key = _api_key()
    sess = Sess(key)
    out = {}
    try:
        sess.open()
        ent = enter_l3(sess)
        d, g = ent["data"], ent["frame"]
        print("start pairs", accent_gap_pairs(g))

        # Build control map by re-measure once
        controls = {}  # color -> {+y: x0, -y: x0}
        pads = pads_sorted(g)
        # use known from map for speed
        controls[14] = {"-y": 12, "+y": 16}
        controls[15] = {"-y": 38, "+y": 34}
        controls[11] = {"+y": 46}  # need -y still

        # Probe remaining pads for 11 -y and env, from current? better fresh
        # Try x50 after moving 11? first find 11 -y
        # Measure all pads that affect 11 by scanning from fresh once more via saved map:
        # PAD6: 11 +y; need a pad for 11 -y — maybe none at start because at top?
        # Sprite11 at y~27 is near top of playfield; -y might be blocked; +y toward gap y=47 is correct direction!

        steps = []
        # Align each color: while |dy|>1 click appropriate pad
        for _ in range(40):
            pairs = accent_gap_pairs(g)
            lv = int(d.get("levels_completed") or 0)
            print("pairs", [(p["color"], round(p["dy"], 2), p["y_match"], p["x_match"]) for p in pairs], "lv", lv)
            if lv >= 3:
                break
            # pick farthest |dy|
            need = [p for p in pairs if abs(p["dy"]) > 1.0]
            if not need:
                print("all y close; try env pads")
                for x0 in (24, 28, 50):
                    g0 = g
                    d, g, xy = click_pad_x(sess, g, x0)
                    steps.append({"xy": xy, "x0": x0, "role": "env", "levels": int(d.get("levels_completed") or 0),
                                  "body": body_ndiff(g0, g), "pairs": accent_gap_pairs(g)})
                    print("env", x0, "body", steps[-1]["body"], "lv", steps[-1]["levels"])
                    if int(d.get("levels_completed") or 0) >= 3:
                        break
                else:
                    # maybe need x alignment somehow — stuck
                    break
                if int(d.get("levels_completed") or 0) >= 3:
                    break
                continue

            need.sort(key=lambda p: -abs(p["dy"]))
            tgt = need[0]
            direction = "-y" if tgt["dy"] > 0 else "+y"  # if accent below gap (dy>0? cy_acc - cy_gap: if acc y > gap y, need -y)
            # dy = acc.cy - gap.cy; if dy>0 accent is below gap, need -y (up)
            x0 = controls.get(tgt["color"], {}).get(direction)
            if x0 is None:
                print("no control", tgt["color"], direction, "try all pads")
                # try every pad, pick one that reduces |dy| for this color
                best = None
                path = [s["xy"] for s in steps]
                for pad in pads_sorted(g):
                    # can't easily restore without re-enter; do live speculative with re-enter
                    pass
                # live: click each pad from re-enter+path — expensive; instead try x50,24,28,46
                for cand_x in (50, 24, 28, 46, 34, 38, 12, 16):
                    ent2 = enter_l3(sess)
                    gg = ent2["frame"]
                    dd = ent2["data"]
                    for xy in path:
                        dd = sess.click(*xy)
                        gg = plane(dd["frame"])
                    # measure dy before
                    before = next(p for p in accent_gap_pairs(gg) if p["color"] == tgt["color"])
                    dd2, gg2, xy = click_pad_x(sess, gg, cand_x)
                    after_pairs = accent_gap_pairs(gg2)
                    after = next((p for p in after_pairs if p["color"] == tgt["color"]), None)
                    if not after:
                        continue
                    score = abs(before["dy"]) - abs(after["dy"])
                    print(f"  probe x{cand_x} score={score} dy {before['dy']}->{after['dy']}")
                    if best is None or score > best["score"]:
                        best = {"x0": cand_x, "score": score, "xy": xy}
                if best is None or best["score"] <= 0:
                    print("cannot reduce", tgt)
                    break
                x0 = best["x0"]
                # apply via re-enter
                ent3 = enter_l3(sess)
                g = ent3["frame"]
                d = ent3["data"]
                for xy in path:
                    d = sess.click(*xy)
                    g = plane(d["frame"])

            g0 = g
            d, g, xy = click_pad_x(sess, g, x0)
            entry = {
                "xy": xy,
                "x0": x0,
                "color": tgt["color"],
                "dir": direction,
                "body": body_ndiff(g0, g),
                "levels": int(d.get("levels_completed") or 0),
                "pairs": [
                    {"c": p["color"], "dy": p["dy"], "ym": p["y_match"], "xm": p["x_match"]}
                    for p in accent_gap_pairs(g)
                ],
            }
            steps.append(entry)
            print("move", entry["color"], entry["dir"], "x", x0, "lv", entry["levels"], entry["pairs"])
            if entry["levels"] >= 3:
                break
            if entry["body"] == 0:
                print("noop move")
                # invalidate control and search
                controls.get(tgt["color"], {}).pop(direction, None)
                continue

        out["steps"] = steps
        out["cleared"] = int(d.get("levels_completed") or 0) >= 3
        out["final"] = summarize(g)
        out["final_pairs"] = accent_gap_pairs(g)
        print("CLEARED", out["cleared"], "lv", d.get("levels_completed"))

        if out["cleared"]:
            FIXTURE_L3_CLEAR.write_text(
                json.dumps(
                    {
                        "game_id": sess.game_id,
                        "meta": {
                            "levels_completed": d.get("levels_completed"),
                            "state": d.get("state"),
                            "available_actions": d.get("available_actions"),
                            "win_levels": d.get("win_levels"),
                        },
                        "steps": steps,
                        "summary": summarize(g),
                        "frame": g.tolist(),
                    },
                    indent=2,
                    default=float,
                ),
                encoding="utf-8",
            )
            stale = g
            d4 = sess.action("ACTION1")
            g4 = plane(d4["frame"])
            import numpy as np
            diff = int(np.sum(stale != g4))
            FIXTURE_L4.write_text(
                json.dumps(
                    {
                        "game_id": sess.game_id,
                        "meta": {
                            "levels_completed": d4.get("levels_completed"),
                            "state": d4.get("state"),
                            "available_actions": d4.get("available_actions"),
                            "win_levels": d4.get("win_levels"),
                        },
                        "sync": {"action": "ACTION1", "pixel_diff_from_stale": diff},
                        "summary": summarize(g4),
                        "frame": g4.tolist(),
                    },
                    indent=2,
                    default=float,
                ),
                encoding="utf-8",
            )
            print("saved clear+L4", diff)
    finally:
        sess.close()
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("saved", OUT)
    return 0 if out.get("cleared") else 1


if __name__ == "__main__":
    raise SystemExit(main())
