"""vc33 L4: pad map + align hunt (accent11 → gap11).

tags=["vc33_recon"]. Enter via L1–L3 clears + ACTION1.
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
from tools.vc33_l3_clear_v5 import ensure_14, ensure_15, do as l3_do  # noqa: E402
from tools.vc33_l3_probe import Sess, enter_l3, pads_sorted, plane  # noqa: E402
from tools.vc33_recon_probe import TAGS  # noqa: E402

OUT = ROOT / "tests" / "fixtures" / "vc33_l4_probe_result.json"
FIXTURE_L4 = ROOT / "tests" / "fixtures" / "vc33_l4_frame_live.json"
FIXTURE_L4_CLEAR = ROOT / "tests" / "fixtures" / "vc33_l4_clear_frame.json"
FIXTURE_L5 = ROOT / "tests" / "fixtures" / "vc33_l5_frame_live.json"


def components(g, color, min_n=1, max_n=10**9):
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


def sprite(g):
    """L4: color4 body n<=32 + nearby color11 accent (prefer below/adjacent)."""
    bodies = components(g, 4, min_n=4, max_n=32)
    accents = components(g, 11, min_n=2, max_n=20)
    if not bodies:
        return None
    # pick body not on border frame — L4 body is left playfield
    bodies = [b for b in bodies if b["x0"] > 0 or b["y0"] > 1]
    if not bodies:
        bodies = components(g, 4, min_n=4, max_n=32)
    b = min(bodies, key=lambda t: (t["x0"], t["y0"]))
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
    return {"body": b, "accent": best, "accent_dist": best_d}


def gap11(g):
    """Color11 marks adjacent to color5, not the sprite accent."""
    sp = sprite(g)
    accents = components(g, 11, min_n=2, max_n=20)
    gaps = []
    for a in accents:
        if sp and sp["accent"] and a["x0"] == sp["accent"]["x0"] and a["y0"] == sp["accent"]["y0"]:
            continue
        band = g[max(0, a["y0"] - 1) : a["y1"] + 2, max(0, a["x0"] - 1) : a["x1"] + 2]
        if np.any(band == 5):
            gaps.append(a)
    gaps.sort(key=lambda t: (t["y0"], t["x0"]))
    return gaps[0] if gaps else None


def summarize(g):
    sp = sprite(g)
    gp = gap11(g)
    aligned = False
    if sp and sp.get("accent") and gp:
        aligned = (
            sp["accent"]["x0"] == gp["x0"]
            and sp["accent"]["x1"] == gp["x1"]
            and sp["accent"]["y0"] == gp["y0"]
            and sp["accent"]["y1"] == gp["y1"]
        )
    return {
        "sprite": sp,
        "gap": gp,
        "pads": pads_sorted(g),
        "c1": components(g, 1, min_n=1, max_n=80),
        "aligned": aligned,
        "hist": {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))},
    }


def clear_l3_on_board(sess, d, g):
    steps = []
    # same as v5 main phases
    d, g, _ = ensure_15(sess, d, g, steps, limit=4)
    for _ in range(16):
        from tools.vc33_l3_clear_v5 import pairs as l3pairs
        ps = l3pairs(g)
        if ps.get(11, {}).get("aligned"):
            break
        if ps.get(11, {}).get("dy", 0) >= 0:
            break
        d, g, ok, err = l3_do(sess, d, g, 46, "11", steps)
        if err == "GAME_OVER" or int(d.get("levels_completed") or 0) >= 3:
            break
        d, g, _ = ensure_15(sess, d, g, steps, limit=8)
    d, g, _ = ensure_14(sess, d, g, steps)
    d, g, _ = ensure_15(sess, d, g, steps)
    d, g, _ = ensure_14(sess, d, g, steps)
    return d, g, steps


def enter_l4(sess):
    ent = enter_l3(sess)
    d, g = ent["data"], ent["frame"]
    d, g, _ = clear_l3_on_board(sess, d, g)
    assert int(d.get("levels_completed") or 0) >= 3, d.get("levels_completed")
    stale = g.copy()
    d = sess.action("ACTION1")
    g = plane(d["frame"])
    diff = int(np.sum(stale != g))
    print("L4 enter sync", diff, "lv", d.get("levels_completed"), summarize(g))
    return {"data": d, "frame": g, "sync_diff": diff, "summary": summarize(g)}


def click_pad(sess, g, pad):
    xy = (int(round(pad["cx"])), int(round(pad["cy"])))
    try:
        d = sess.click(*xy)
    except requests.HTTPError as e:
        return None, g, list(xy), str(e)
    return d, plane(d["frame"]), list(xy), None


def main():
    key = _api_key()
    sess = Sess(key)
    out = {"pad_map": []}
    try:
        sess.open()
        out["game_id"] = sess.game_id
        ent = enter_l4(sess)
        out["enter"] = {"sync_diff": ent["sync_diff"], "summary": ent["summary"]}
        FIXTURE_L4.write_text(
            json.dumps({
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
            }, indent=2, default=float),
            encoding="utf-8",
        )
        print("saved", FIXTURE_L4)

        n = len(ent["summary"]["pads"])
        for i in range(n):
            ent_i = enter_l4(sess)
            g0 = ent_i["frame"]
            pads = pads_sorted(g0)
            pad = pads[i]
            sp0 = sprite(g0)
            gp0 = gap11(g0)
            c1_0 = components(g0, 1, min_n=1, max_n=80)
            d, g1, xy, err = click_pad(sess, g0, pad)
            if err or d is None:
                print("PAD err", i, err)
                continue
            sp1 = sprite(g1)
            gp1 = gap11(g1)
            c1_1 = components(g1, 1, min_n=1, max_n=80)
            row = {
                "pad_i": i,
                "x0": pad["x0"],
                "xy": xy,
                "body_ndiff": body_ndiff(g0, g1),
                "changes": body_changes(g0, g1),
                "sprite_ddx": None if not (sp0 and sp1) else round(sp1["body"]["cx"] - sp0["body"]["cx"], 3),
                "sprite_ddy": None if not (sp0 and sp1) else round(sp1["body"]["cy"] - sp0["body"]["cy"], 3),
                "acc_ddx": None
                if not (sp0 and sp1 and sp0.get("accent") and sp1.get("accent"))
                else round(sp1["accent"]["cx"] - sp0["accent"]["cx"], 3),
                "acc_ddy": None
                if not (sp0 and sp1 and sp0.get("accent") and sp1.get("accent"))
                else round(sp1["accent"]["cy"] - sp0["accent"]["cy"], 3),
                "gap_moved": None if not (gp0 and gp1) else (gp0["x0"] != gp1["x0"] or gp0["y0"] != gp1["y0"]),
                "c1_before": c1_0,
                "c1_after": c1_1,
                "levels": int(d.get("levels_completed") or 0),
                "aligned": summarize(g1)["aligned"],
            }
            out["pad_map"].append(row)
            print(
                f"PAD[{i}] x0={pad['x0']} body={row['body_ndiff']} "
                f"sprΔ=({row['sprite_ddx']},{row['sprite_ddy']}) "
                f"accΔ=({row['acc_ddx']},{row['acc_ddy']}) gap_moved={row['gap_moved']} "
                f"lv={row['levels']}"
            )
        out["roles"] = {
            "movers": [
                p for p in out["pad_map"]
                if (abs(p.get("sprite_ddx") or 0) + abs(p.get("sprite_ddy") or 0)) > 0.1
            ],
            "env": [
                p for p in out["pad_map"]
                if (abs(p.get("sprite_ddx") or 0) + abs(p.get("sprite_ddy") or 0)) < 0.1
                and p["body_ndiff"] > 0
            ],
        }
        print("movers", [(p["x0"], p["sprite_ddx"], p["sprite_ddy"]) for p in out["roles"]["movers"]])
        print("env", [p["x0"] for p in out["roles"]["env"]])
    finally:
        sess.close()
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
