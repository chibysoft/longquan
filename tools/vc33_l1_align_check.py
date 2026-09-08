"""Confirm L1 clear = sprite color11 aligns under beam gap; grab post-clear frame."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import BASE, _api_key  # noqa: E402
from tools.vc33_l1_clear_hunt import Sess, beam_gap, pad_xy, summarize  # noqa: E402
from tools.vc33_recon_probe import TAGS, c9_blocks, plane, sprite_cc  # noqa: E402

FIXTURE_CLEAR = ROOT / "tests" / "fixtures" / "vc33_l1_clear_frame.json"
FIXTURE_L2 = ROOT / "tests" / "fixtures" / "vc33_l2_frame_live.json"


def accent_bbox(g: np.ndarray):
    """Color-11 cells belonging to sprite CC (y>32 to skip beam gap)."""
    sp = sprite_cc(g)
    if not sp:
        return None
    # restrict to sprite AABB
    sub = g[sp["y0"] : sp["y1"] + 1, sp["x0"] : sp["x1"] + 1]
    ys, xs = np.where(sub == 11)
    if len(xs) == 0:
        return None
    return {
        "n": int(len(xs)),
        "x0": int(xs.min() + sp["x0"]),
        "x1": int(xs.max() + sp["x0"]),
        "y0": int(ys.min() + sp["y0"]),
        "y1": int(ys.max() + sp["y0"]),
        "cx": float(xs.mean() + sp["x0"]),
        "cy": float(ys.mean() + sp["y0"]),
    }


def aligned(g) -> bool:
    acc = accent_bbox(g)
    gap = beam_gap(g)
    if not acc or not gap:
        return False
    return acc["x0"] == gap["x0"] and acc["x1"] == gap["x1"]


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        d = sess.reset()
        g = plane(d["frame"])
        rows = []
        for step in range(0, 6):
            acc = accent_bbox(g)
            gap = beam_gap(g)
            row = {
                "step": step,
                "levels": int(d.get("levels_completed") or 0),
                "sprite": sprite_cc(g),
                "accent": acc,
                "gap": gap,
                "aligned": aligned(g),
            }
            rows.append(row)
            print(
                f"s{step} lv={row['levels']} aligned={row['aligned']} "
                f"acc={acc} gap={gap}"
            )
            if row["levels"] > 0:
                break
            pads = c9_blocks(g)
            d = sess.click(*pad_xy(pads, "lower"))
            g = plane(d["frame"])

        assert rows[-1]["levels"] == 1, rows
        assert rows[-1]["aligned"] is True
        # step before clear should NOT be aligned
        assert rows[-2]["aligned"] is False
        print("ALIGN_RULE OK: clear iff accent x-range == gap x-range")

        FIXTURE_CLEAR.write_text(
            json.dumps(
                {
                    "game_id": sess.game_id,
                    "meta": {
                        "levels_completed": 1,
                        "state": d.get("state"),
                        "available_actions": d.get("available_actions"),
                        "win_levels": d.get("win_levels"),
                    },
                    "summary": summarize(g),
                    "accent": accent_bbox(g),
                    "align_rule": "sprite color11 AABB x0..x1 == beam gap x0..x1",
                    "timeline": rows,
                    "frame": g.tolist(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print("saved", FIXTURE_CLEAR)

        # sync into L2? try ACTION1 like ft09/ls20
        stale = g.copy()
        for sync_name in ("ACTION1", "ACTION6"):
            if sync_name == "ACTION6":
                # click blank
                r = sess.s.post(
                    f"{BASE}/api/cmd/ACTION6",
                    headers={
                        "X-API-Key": key,
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    json={
                        "game_id": sess.game_id,
                        "guid": sess.guid,
                        "x": 10,
                        "y": 10,
                    },
                    timeout=30,
                )
                data = r.json()
            else:
                r = sess.s.post(
                    f"{BASE}/api/cmd/ACTION1",
                    headers={
                        "X-API-Key": key,
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    json={"game_id": sess.game_id, "guid": sess.guid},
                    timeout=30,
                )
                data = r.json()
            sess.guid = data.get("guid", sess.guid)
            g2 = plane(data["frame"])
            diff = int(np.sum(stale != g2))
            print(
                f"sync {sync_name}: diff={diff} lv={data.get('levels_completed')} "
                f"actions={data.get('available_actions')} state={data.get('state')}"
            )
            print("  sum", summarize(g2))
            if diff > 100:
                FIXTURE_L2.write_text(
                    json.dumps(
                        {
                            "game_id": sess.game_id,
                            "meta": {
                                "levels_completed": data.get("levels_completed"),
                                "state": data.get("state"),
                                "available_actions": data.get("available_actions"),
                                "win_levels": data.get("win_levels"),
                            },
                            "sync": {"action": sync_name, "pixel_diff_from_stale": diff},
                            "summary": summarize(g2),
                            "frame": g2.tolist(),
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                print("saved L2", FIXTURE_L2)
                break
            stale = g2
    finally:
        sess.close()


if __name__ == "__main__":
    main()
