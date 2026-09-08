"""vc33 L2 fast probe: pad deltas + rightward align clear + L3 grab.

tags=["vc33_recon"]. Frame-derived pad choice by measured delta toward gap.
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
    FIXTURE_L2_CLEAR,
    FIXTURE_L3,
    OUT,
    Sess,
    aligned,
    body_changes,
    body_ndiff,
    c9_blocks,
    clear_l1,
    enter_l2,
    pick_gap,
    plane,
    sprite_bundle,
    summarize,
)


def one_pad_effect(sess: Sess, pad_index: int) -> dict:
    ent = enter_l2(sess)
    g0 = ent["frame"]
    pads = sorted(c9_blocks(g0), key=lambda b: b["y0"])
    pad = pads[pad_index]
    xy = (int(round(pad["cx"])), int(round(pad["cy"])))
    sp0 = sprite_bundle(g0)
    gap0 = pick_gap(g0)
    d = sess.click(*xy)
    g1 = plane(d["frame"])
    sp1 = sprite_bundle(g1)
    gap1 = pick_gap(g1)
    return {
        "pad_index_by_y": pad_index,
        "pad_y0": pad["y0"],
        "xy": list(xy),
        "body_ndiff": body_ndiff(g0, g1),
        "changes_top": body_changes(g0, g1),
        "sprite_ddx": None if not (sp0 and sp1) else round(sp1["cx"] - sp0["cx"], 3),
        "sprite_ddy": None if not (sp0 and sp1) else round(sp1["cy"] - sp0["cy"], 3),
        "accent_ddx": None
        if not (sp0 and sp1 and sp0.get("accent") and sp1.get("accent"))
        else round(sp1["accent"]["cx"] - sp0["accent"]["cx"], 3),
        "accent_ddy": None
        if not (sp0 and sp1 and sp0.get("accent") and sp1.get("accent"))
        else round(sp1["accent"]["cy"] - sp0["accent"]["cy"], 3),
        "gap_before": gap0,
        "gap_after": gap1,
        "gap_moved": None
        if not (gap0 and gap1)
        else (gap0["x0"] != gap1["x0"] or gap0["y0"] != gap1["y0"]),
        "levels": int(d.get("levels_completed") or 0),
        "aligned": aligned(g1),
        "sprite_after": sp1,
    }


def clear_l2_greedy(sess: Sess) -> dict:
    """At each step click the pad whose one-step effect most reduces |accent-gap|."""
    ent = enter_l2(sess)
    d = ent["data"]
    g = ent["frame"]
    steps = []
    for i in range(16):
        lv0 = int(d.get("levels_completed") or 0)
        if lv0 >= 2:
            break
        pads = sorted(c9_blocks(g), key=lambda b: b["y0"])
        sp0 = sprite_bundle(g)
        gap0 = pick_gap(g)
        if not sp0 or not sp0.get("accent") or not gap0:
            raise RuntimeError("perceive fail")
        # score pads without full re-enter: click, measure, then undo via re-enter+replay
        path = [s["xy"] for s in steps]
        scored = []
        for pi, pad in enumerate(pads):
            # restore to current path end
            ent2 = enter_l2(sess)
            gg = ent2["frame"]
            dd = ent2["data"]
            for xy in path:
                dd = sess.click(*xy)
                gg = plane(dd["frame"])
            xy = (int(round(pad["cx"])), int(round(pad["cy"])))
            s_before = sprite_bundle(gg)
            g_before = pick_gap(gg)
            dd2 = sess.click(*xy)
            gg2 = plane(dd2["frame"])
            s_after = sprite_bundle(gg2)
            g_after = pick_gap(gg2)
            if not (s_before and s_after and s_before.get("accent") and s_after.get("accent") and g_before and g_after):
                continue
            before = abs(s_before["accent"]["cx"] - g_before["cx"])
            after = abs(s_after["accent"]["cx"] - g_after["cx"])
            scored.append({
                "pad_i": pi,
                "xy": list(xy),
                "score": before - after,
                "ddx": round(s_after["cx"] - s_before["cx"], 3),
                "ddy": round(s_after["cy"] - s_before["cy"], 3),
                "body_ndiff": body_ndiff(gg, gg2),
                "levels": int(dd2.get("levels_completed") or 0),
                "aligned": aligned(gg2),
            })
        if not scored:
            raise RuntimeError("no scores")
        scored.sort(key=lambda c: (-c["score"], -c["body_ndiff"]))
        best = scored[0]
        # if best doesn't improve x-distance, still take positive body move toward gap sign
        if best["score"] <= 0:
            # prefer any with ddx toward gap
            desire = 1 if gap0["cx"] > sp0["accent"]["cx"] else -1
            alt = [c for c in scored if (c["ddx"] or 0) * desire > 0]
            if alt:
                best = alt[0]
        # apply best
        ent3 = enter_l2(sess)
        g = ent3["frame"]
        d = ent3["data"]
        for xy in path:
            d = sess.click(*xy)
            g = plane(d["frame"])
        d = sess.click(*best["xy"])
        g = plane(d["frame"])
        entry = {
            **best,
            "levels": int(d.get("levels_completed") or 0),
            "aligned": aligned(g),
            "accent": sprite_bundle(g)["accent"] if sprite_bundle(g) else None,
            "gap": pick_gap(g),
            "all_scores": scored,
        }
        steps.append(entry)
        print(
            f"L2 s{i} pick pad{entry['pad_i']} {entry['xy']} score={entry['score']} "
            f"Δ=({entry['ddx']},{entry['ddy']}) lv={entry['levels']} aligned={entry['aligned']} "
            f"acc={entry['accent']}"
        )
        if entry["levels"] >= 2:
            break
        if entry["body_ndiff"] == 0 and entry["score"] <= 0:
            print("stuck")
            break
    return {
        "steps": steps,
        "levels": int(d.get("levels_completed") or 0),
        "frame": g,
        "data": d,
        "summary": summarize(g),
        "cleared": int(d.get("levels_completed") or 0) >= 2,
    }


def clear_l2_direct(sess: Sess) -> dict:
    """After pad map known: click +x pad until aligned / levels>=2."""
    ent = enter_l2(sess)
    d = ent["data"]
    g = ent["frame"]
    steps = []
    for i in range(12):
        if int(d.get("levels_completed") or 0) >= 2:
            break
        pads = sorted(c9_blocks(g), key=lambda b: b["y0"])
        sp = sprite_bundle(g)
        gap = pick_gap(g)
        # pick pad by live one-step microtest without full L1 (same board)
        # save guid/path: try each pad from clones via reset-enter is expensive;
        # use measured map: among pads, choose max score via speculative clicks + re-enter once
        desire_dx = gap["cx"] - sp["accent"]["cx"]
        # click candidate: pad with y0==44 was +4, y0==36 was -4 in map phase
        # re-measure quickly: only test pads, restore by re-enter+replay of steps so far
        path = [s["xy"] for s in steps]
        best = None
        for pi, pad in enumerate(pads):
            ent2 = enter_l2(sess)
            gg = ent2["frame"]
            dd = ent2["data"]
            for xy in path:
                dd = sess.click(*xy)
                gg = plane(dd["frame"])
            xy = (int(round(pad["cx"])), int(round(pad["cy"])))
            s0 = sprite_bundle(gg)
            g0 = pick_gap(gg)
            dd2 = sess.click(*xy)
            gg2 = plane(dd2["frame"])
            s1 = sprite_bundle(gg2)
            g1 = pick_gap(gg2)
            score = abs(s0["accent"]["cx"] - g0["cx"]) - abs(s1["accent"]["cx"] - g1["cx"])
            cand = {
                "pad_i": pi,
                "xy": list(xy),
                "score": score,
                "ddx": round(s1["cx"] - s0["cx"], 3),
                "ddy": round(s1["cy"] - s0["cy"], 3),
                "body_ndiff": body_ndiff(gg, gg2),
            }
            if best is None or cand["score"] > best["score"]:
                best = cand
        ent3 = enter_l2(sess)
        g = ent3["frame"]
        d = ent3["data"]
        for xy in path:
            d = sess.click(*xy)
            g = plane(d["frame"])
        d = sess.click(*best["xy"])
        g = plane(d["frame"])
        entry = {
            **best,
            "levels": int(d.get("levels_completed") or 0),
            "aligned": aligned(g),
            "accent": (sprite_bundle(g) or {}).get("accent"),
            "gap": pick_gap(g),
        }
        steps.append(entry)
        print(
            f"L2direct s{i} pad{entry['pad_i']} {entry['xy']} score={entry['score']} "
            f"Δ=({entry['ddx']},{entry['ddy']}) lv={entry['levels']} aligned={entry['aligned']}"
        )
        if entry["levels"] >= 2:
            break
        if entry["score"] <= 0 and entry["body_ndiff"] == 0:
            break
    return {
        "steps": steps,
        "levels": int(d.get("levels_completed") or 0),
        "frame": g,
        "data": d,
        "summary": summarize(g),
        "cleared": int(d.get("levels_completed") or 0) >= 2,
    }


def clear_l2_fast(sess: Sess, pad_map: list) -> dict:
    """Use pad_map: pick pad with accent_ddx toward gap; click until clear."""
    # find +x and -x pads
    plus = next((p for p in pad_map if (p.get("accent_ddx") or 0) > 0), None)
    minus = next((p for p in pad_map if (p.get("accent_ddx") or 0) < 0), None)
    ent = enter_l2(sess)
    d = ent["data"]
    g = ent["frame"]
    steps = []
    for i in range(12):
        if int(d.get("levels_completed") or 0) >= 2:
            break
        sp = sprite_bundle(g)
        gap = pick_gap(g)
        pads = sorted(c9_blocks(g), key=lambda b: b["y0"])
        # choose direction
        if sp["accent"]["cx"] < gap["cx"]:
            target = plus
        elif sp["accent"]["cx"] > gap["cx"]:
            target = minus
        else:
            # already same cx center — maybe need exact x0 match; keep moving plus if not aligned
            target = plus
        # locate live pad by y0
        pad = next(p for p in pads if p["y0"] == target["pad_y0"])
        xy = (int(round(pad["cx"])), int(round(pad["cy"])))
        g0 = g
        d = sess.click(*xy)
        g = plane(d["frame"])
        entry = {
            "xy": list(xy),
            "pad_y0": pad["y0"],
            "body_ndiff": body_ndiff(g0, g),
            "levels": int(d.get("levels_completed") or 0),
            "aligned": aligned(g),
            "accent": (sprite_bundle(g) or {}).get("accent"),
            "gap": pick_gap(g),
        }
        steps.append(entry)
        print(
            f"L2fast s{i} y0={pad['y0']} {xy} body={entry['body_ndiff']} "
            f"lv={entry['levels']} aligned={entry['aligned']} acc={entry['accent']}"
        )
        if entry["levels"] >= 2:
            break
        if entry["body_ndiff"] == 0:
            break
    return {
        "steps": steps,
        "levels": int(d.get("levels_completed") or 0),
        "frame": g,
        "data": d,
        "summary": summarize(g),
        "cleared": int(d.get("levels_completed") or 0) >= 2,
    }


def main():
    key = _api_key()
    sess = Sess(key)
    out = {}
    try:
        sess.open()
        out["game_id"] = sess.game_id
        out["card_id"] = sess.card_id

        # pad map
        pad_map = []
        for i in range(4):
            row = one_pad_effect(sess, i)
            pad_map.append(row)
            print(
                f"MAP[{i}] y0={row['pad_y0']} body={row['body_ndiff']} "
                f"sprΔ=({row['sprite_ddx']},{row['sprite_ddy']}) "
                f"accΔ=({row['accent_ddx']},{row['accent_ddy']}) gap_moved={row['gap_moved']} "
                f"changes={row['changes_top']}"
            )
        out["pad_map"] = pad_map

        cleared = clear_l2_fast(sess, pad_map)
        out["l2_clear"] = {
            "cleared": cleared["cleared"],
            "levels": cleared["levels"],
            "steps": [
                {k: v for k, v in s.items() if k != "all_scores"}
                for s in cleared["steps"]
            ],
            "summary": cleared["summary"],
        }
        print("CLEARED", cleared["cleared"], "lv", cleared["levels"])

        if cleared["cleared"]:
            FIXTURE_L2_CLEAR.write_text(
                json.dumps(
                    {
                        "game_id": sess.game_id,
                        "meta": {
                            "levels_completed": cleared["data"].get("levels_completed"),
                            "state": cleared["data"].get("state"),
                            "available_actions": cleared["data"].get("available_actions"),
                            "win_levels": cleared["data"].get("win_levels"),
                        },
                        "summary": cleared["summary"],
                        "steps": out["l2_clear"]["steps"],
                        "frame": cleared["frame"].tolist(),
                    },
                    indent=2,
                    default=float,
                ),
                encoding="utf-8",
            )
            print("saved", FIXTURE_L2_CLEAR)
            stale = cleared["frame"]
            d3 = sess.action("ACTION1")
            g3 = plane(d3["frame"])
            diff = int(np.sum(stale != g3))
            print("L3 sync", diff, summarize(g3))
            out["l3_enter"] = {"sync_diff": diff, "summary": summarize(g3)}
            if diff > 100:
                FIXTURE_L3.write_text(
                    json.dumps(
                        {
                            "game_id": sess.game_id,
                            "meta": {
                                "levels_completed": d3.get("levels_completed"),
                                "state": d3.get("state"),
                                "available_actions": d3.get("available_actions"),
                                "win_levels": d3.get("win_levels"),
                            },
                            "sync": {"action": "ACTION1", "pixel_diff_from_stale": diff},
                            "summary": summarize(g3),
                            "frame": g3.tolist(),
                        },
                        indent=2,
                        default=float,
                    ),
                    encoding="utf-8",
                )
                print("saved", FIXTURE_L3)
    finally:
        sess.close()

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("saved", OUT)
    return 0 if out.get("l2_clear", {}).get("cleared") else 1


if __name__ == "__main__":
    raise SystemExit(main())
