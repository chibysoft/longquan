"""vc33 L3: perceive small sprites, map 8 pads, hunt levels 2→3.

tags=["vc33_recon"]. Frame-derived. Reuses L1/L2 clear policies.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import (  # noqa: E402
    Sess,
    body_changes,
    body_ndiff,
    c9_blocks,
    enter_l2,
    plane,
)
from tools.vc33_recon_probe import TAGS  # noqa: E402

OUT = ROOT / "tests" / "fixtures" / "vc33_l3_probe_result.json"
FIXTURE_L3 = ROOT / "tests" / "fixtures" / "vc33_l3_frame_live.json"
FIXTURE_L3_CLEAR = ROOT / "tests" / "fixtures" / "vc33_l3_clear_frame.json"
FIXTURE_L4 = ROOT / "tests" / "fixtures" / "vc33_l4_frame_live.json"

ACCENT_COLORS = (11, 14, 15)


def components(g: np.ndarray, color: int, min_n: int = 1, max_n: int = 10**9):
    H, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(H):
        for x in range(W):
            if seen[y, x] or int(g[y, x]) != color:
                continue
            stack = [(x, y)]
            seen[y, x] = True
            cells = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (
                        0 <= nx < W
                        and 0 <= ny < H
                        and not seen[ny, nx]
                        and int(g[ny, nx]) == color
                    ):
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            if min_n <= len(cells) <= max_n:
                xs = [c[0] for c in cells]
                ys = [c[1] for c in cells]
                out.append({
                    "n": len(cells),
                    "x0": min(xs),
                    "y0": min(ys),
                    "x1": max(xs),
                    "y1": max(ys),
                    "cx": sum(xs) / len(xs),
                    "cy": sum(ys) / len(ys),
                    "color": color,
                })
    out.sort(key=lambda b: (b["y0"], b["x0"]))
    return out


def small_sprites(g: np.ndarray):
    """Color4 blobs with n<=16 (exclude frame border). Attach nearby accent."""
    bodies = components(g, 4, min_n=1, max_n=16)
    accents = []
    for c in ACCENT_COLORS:
        accents.extend(components(g, c, min_n=1, max_n=8))
    sprites = []
    for b in bodies:
        # nearest accent within chebyshev 4 of body bbox
        best = None
        best_d = 99
        for a in accents:
            dx = 0
            if a["x1"] < b["x0"]:
                dx = b["x0"] - a["x1"]
            elif a["x0"] > b["x1"]:
                dx = a["x0"] - b["x1"]
            dy = 0
            if a["y1"] < b["y0"]:
                dy = b["y0"] - a["y1"]
            elif a["y0"] > b["y1"]:
                dy = a["y0"] - b["y1"]
            d = max(dx, dy)
            if d < best_d:
                best_d = d
                best = a
        sprites.append({
            "body": b,
            "accent": best,
            "accent_dist": best_d,
            "key": (
                best["color"] if best else -1,
                round(b["cx"], 1),
                round(b["cy"], 1),
            ),
        })
    sprites.sort(key=lambda s: (s["body"]["x0"], s["body"]["y0"]))
    return sprites


def gaps_on_beams(g: np.ndarray):
    """Small accent-color marks that sit on/near color5 vertical beams."""
    gaps = []
    for c in ACCENT_COLORS:
        for a in components(g, c, min_n=1, max_n=4):
            # check neighbors for color5
            x0, x1, y0, y1 = a["x0"], a["x1"], a["y0"], a["y1"]
            band = g[max(0, y0 - 1) : y1 + 2, max(0, x0 - 1) : x1 + 2]
            if np.any(band == 5):
                gaps.append({**a, "role": "gap"})
    gaps.sort(key=lambda b: (b["color"], b["y0"], b["x0"]))
    return gaps


def pads_sorted(g):
    return sorted(c9_blocks(g), key=lambda b: (b["y0"], b["x0"]))


def summarize(g):
    return {
        "sprites": small_sprites(g),
        "gaps": gaps_on_beams(g),
        "pads": pads_sorted(g),
        "hist": {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))},
    }


def clear_l2_on_board(sess: Sess, d, g):
    """Assume already on L2. Alternate env y=24 and plus y=44."""
    steps = []
    while int(d.get("levels_completed") or 0) < 2 and len(steps) < 16:
        for y0 in (24, 44):
            pad = next(p for p in pads_sorted(g) if p["y0"] == y0)
            xy = (int(round(pad["cx"])), int(round(pad["cy"])))
            d = sess.click(*xy)
            g = plane(d["frame"])
            steps.append({"xy": list(xy), "y0": y0, "levels": int(d.get("levels_completed") or 0)})
            if int(d.get("levels_completed") or 0) >= 2:
                break
        else:
            continue
        break
    return d, g, steps


def enter_l3(sess: Sess):
    ent = enter_l2(sess)
    d, g = ent["data"], ent["frame"]
    d, g, l2steps = clear_l2_on_board(sess, d, g)
    assert int(d.get("levels_completed") or 0) >= 2, l2steps
    stale = g.copy()
    d = sess.action("ACTION1")
    g = plane(d["frame"])
    diff = int(np.sum(stale != g))
    print("L3 enter sync", diff, "lv", d.get("levels_completed"))
    return {"data": d, "frame": g, "sync_diff": diff, "summary": summarize(g)}


def sprite_signature(sprites):
    """Stable-ish signature: list of (accent_color, body_cx, body_cy)."""
    out = []
    for s in sprites:
        ac = s["accent"]["color"] if s["accent"] else -1
        b = s["body"]
        out.append((ac, round(b["cx"], 2), round(b["cy"], 2), b["x0"], b["y0"]))
    return out


def main():
    key = _api_key()
    sess = Sess(key)
    out = {}
    try:
        sess.open()
        out["game_id"] = sess.game_id
        out["card_id"] = sess.card_id

        ent = enter_l3(sess)
        out["l3_enter"] = {
            "sync_diff": ent["sync_diff"],
            "summary": ent["summary"],
        }
        FIXTURE_L3.write_text(
            json.dumps(
                {
                    "game_id": sess.game_id,
                    "meta": {
                        "levels_completed": ent["data"].get("levels_completed"),
                        "state": ent["data"].get("state"),
                        "available_actions": ent["data"].get("available_actions"),
                        "win_levels": ent["data"].get("win_levels"),
                    },
                    "sync": {"action": "ACTION1", "pixel_diff_from_stale": ent["sync_diff"]},
                    "summary": ent["summary"],
                    "frame": ent["frame"].tolist(),
                },
                indent=2,
                default=float,
            ),
            encoding="utf-8",
        )
        print("saved", FIXTURE_L3)
        print("sprites", sprite_signature(ent["summary"]["sprites"]))
        print("gaps", ent["summary"]["gaps"])
        print("pads", [(p["x0"], p["y0"]) for p in ent["summary"]["pads"]])

        # Map each pad from fresh L3
        pad_map = []
        n_pads = len(ent["summary"]["pads"])
        for i in range(n_pads):
            ent_i = enter_l3(sess)
            g0 = ent_i["frame"]
            pads = pads_sorted(g0)
            pad = pads[i]
            xy = (int(round(pad["cx"])), int(round(pad["cy"])))
            sp0 = small_sprites(g0)
            sig0 = sprite_signature(sp0)
            d = sess.click(*xy)
            g1 = plane(d["frame"])
            sp1 = small_sprites(g1)
            sig1 = sprite_signature(sp1)
            # match sprites by accent color
            deltas = []
            for s0 in sp0:
                ac = s0["accent"]["color"] if s0["accent"] else None
                mates = [s for s in sp1 if (s["accent"]["color"] if s["accent"] else None) == ac]
                if not mates:
                    continue
                s1 = min(
                    mates,
                    key=lambda s: abs(s["body"]["cx"] - s0["body"]["cx"])
                    + abs(s["body"]["cy"] - s0["body"]["cy"]),
                )
                deltas.append({
                    "accent": ac,
                    "ddx": round(s1["body"]["cx"] - s0["body"]["cx"], 3),
                    "ddy": round(s1["body"]["cy"] - s0["body"]["cy"], 3),
                    "before": s0["body"],
                    "after": s1["body"],
                })
            row = {
                "pad_i": i,
                "pad": pad,
                "xy": list(xy),
                "body_ndiff": body_ndiff(g0, g1),
                "changes": body_changes(g0, g1),
                "sig0": sig0,
                "sig1": sig1,
                "deltas": deltas,
                "levels": int(d.get("levels_completed") or 0),
            }
            pad_map.append(row)
            moved = [d for d in deltas if abs(d["ddx"]) + abs(d["ddy"]) > 0.1]
            print(
                f"PAD[{i}] x={pad['x0']} xy={xy} body={row['body_ndiff']} "
                f"moved={moved} lv={row['levels']}"
            )
        out["pad_map"] = pad_map

        # Hunt: greedy — click pad that reduces sum of |accent_xy - matching_gap_xy|
        def cost(g):
            sps = small_sprites(g)
            gaps = gaps_on_beams(g)
            total = 0.0
            detail = []
            for s in sps:
                if not s["accent"]:
                    continue
                ac = s["accent"]["color"]
                # gap: accent-colored mark on beam; sprite accent is the "pointer"
                # align sprite accent x,y to gap of same color?
                cands = [gp for gp in gaps if gp["color"] == ac]
                if not cands:
                    continue
                # use accent bbox center vs gap center
                ax, ay = s["accent"]["cx"], s["accent"]["cy"]
                gp = min(cands, key=lambda t: abs(t["cx"] - ax) + abs(t["cy"] - ay))
                # L1/L2 used x-range equality of accent vs gap; here try Manhattan of centers
                # also try aligning accent x0..x1 with gap x0..x1 and same for y
                dx = abs(s["accent"]["x0"] - gp["x0"]) + abs(s["accent"]["x1"] - gp["x1"])
                dy = abs(s["accent"]["y0"] - gp["y0"]) + abs(s["accent"]["y1"] - gp["y1"])
                # prefer matching the axis that differs — use L1-style: x band OR y band?
                # cost = min distance on either full match or manhatten of centers
                c = abs(ax - gp["cx"]) + abs(ay - gp["cy"])
                detail.append({"accent": ac, "cost": c, "dx_band": dx, "dy_band": dy, "gap": gp, "acc": s["accent"]})
                total += c
            return total, detail

        ent_h = enter_l3(sess)
        d = ent_h["data"]
        g = ent_h["frame"]
        hunt = []
        for step in range(24):
            lv = int(d.get("levels_completed") or 0)
            if lv >= 3:
                break
            c0, det0 = cost(g)
            pads = pads_sorted(g)
            path = [h["xy"] for h in hunt]
            best = None
            for pi, pad in enumerate(pads):
                # restore
                ent2 = enter_l3(sess)
                gg = ent2["frame"]
                dd = ent2["data"]
                for xy in path:
                    dd = sess.click(*xy)
                    gg = plane(dd["frame"])
                xy = (int(round(pad["cx"])), int(round(pad["cy"])))
                dd2 = sess.click(*xy)
                gg2 = plane(dd2["frame"])
                c1, det1 = cost(gg2)
                cand = {
                    "pad_i": pi,
                    "xy": list(xy),
                    "score": c0 - c1,
                    "cost_after": c1,
                    "body_ndiff": body_ndiff(gg, gg2),
                    "levels": int(dd2.get("levels_completed") or 0),
                    "deltas": None,
                }
                # also record sprite deltas
                sp0, sp1 = small_sprites(gg), small_sprites(gg2)
                moved = []
                for s0 in sp0:
                    ac = s0["accent"]["color"] if s0["accent"] else None
                    mates = [s for s in sp1 if (s["accent"]["color"] if s["accent"] else None) == ac]
                    if not mates:
                        continue
                    s1 = mates[0]
                    moved.append({
                        "accent": ac,
                        "ddx": round(s1["body"]["cx"] - s0["body"]["cx"], 3),
                        "ddy": round(s1["body"]["cy"] - s0["body"]["cy"], 3),
                    })
                cand["moved"] = moved
                if best is None or cand["score"] > best["score"] or (
                    abs(cand["score"] - best["score"]) < 1e-9 and cand["body_ndiff"] > best["body_ndiff"]
                ):
                    best = cand
            # apply best
            ent3 = enter_l3(sess)
            g = ent3["frame"]
            d = ent3["data"]
            for xy in path:
                d = sess.click(*xy)
                g = plane(d["frame"])
            d = sess.click(*best["xy"])
            g = plane(d["frame"])
            c_now, det_now = cost(g)
            entry = {
                **best,
                "levels": int(d.get("levels_completed") or 0),
                "cost": c_now,
                "detail": det_now,
                "sprites": sprite_signature(small_sprites(g)),
            }
            hunt.append(entry)
            print(
                f"HUNT s{step} pad{entry['pad_i']} {entry['xy']} score={entry['score']:.2f} "
                f"cost={entry['cost']:.2f} lv={entry['levels']} moved={entry['moved']}"
            )
            if entry["levels"] >= 3:
                break
            if entry["body_ndiff"] == 0 and entry["score"] <= 0:
                print("stuck")
                break

        out["hunt"] = {
            "steps": hunt,
            "cleared": any(h["levels"] >= 3 for h in hunt),
            "final_levels": int(d.get("levels_completed") or 0),
            "final": summarize(g),
        }
        print("CLEARED", out["hunt"]["cleared"], "lv", out["hunt"]["final_levels"])

        if out["hunt"]["cleared"]:
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
                        "steps": hunt,
                        "summary": summarize(g),
                        "frame": g.tolist(),
                    },
                    indent=2,
                    default=float,
                ),
                encoding="utf-8",
            )
            print("saved", FIXTURE_L3_CLEAR)
            stale = g
            d4 = sess.action("ACTION1")
            g4 = plane(d4["frame"])
            diff = int(np.sum(stale != g4))
            print("L4 sync", diff, summarize(g4))
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
            print("saved", FIXTURE_L4)
    finally:
        sess.close()

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("saved", OUT)
    return 0 if out.get("hunt", {}).get("cleared") else 1


if __name__ == "__main__":
    raise SystemExit(main())
