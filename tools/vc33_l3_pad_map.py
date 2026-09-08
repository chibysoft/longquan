"""vc33 L3 pad→sprite delta map only (fast)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l3_probe import (  # noqa: E402
    OUT,
    Sess,
    body_changes,
    body_ndiff,
    enter_l3,
    gaps_on_beams,
    pads_sorted,
    plane,
    small_sprites,
    sprite_signature,
    summarize,
)


def main():
    key = _api_key()
    sess = Sess(key)
    out = {"pad_map": []}
    try:
        sess.open()
        out["game_id"] = sess.game_id
        ent = enter_l3(sess)
        out["enter"] = {"sync_diff": ent["sync_diff"], "summary": ent["summary"]}
        print("sprites", sprite_signature(ent["summary"]["sprites"]))
        print("gaps", ent["summary"]["gaps"])
        n = len(ent["summary"]["pads"])
        for i in range(n):
            ent_i = enter_l3(sess)
            g0 = ent_i["frame"]
            pads = pads_sorted(g0)
            pad = pads[i]
            xy = (int(round(pad["cx"])), int(round(pad["cy"])))
            sp0 = small_sprites(g0)
            d = sess.click(*xy)
            g1 = plane(d["frame"])
            sp1 = small_sprites(g1)
            deltas = []
            for s0 in sp0:
                ac = s0["accent"]["color"] if s0["accent"] else None
                mates = [
                    s
                    for s in sp1
                    if (s["accent"]["color"] if s["accent"] else None) == ac
                ]
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
                    "acc_ddx": round(s1["accent"]["cx"] - s0["accent"]["cx"], 3)
                    if s0["accent"] and s1["accent"]
                    else None,
                    "acc_ddy": round(s1["accent"]["cy"] - s0["accent"]["cy"], 3)
                    if s0["accent"] and s1["accent"]
                    else None,
                })
            # gap movement?
            g0gaps, g1gaps = gaps_on_beams(g0), gaps_on_beams(g1)
            gap_d = []
            for a in g0gaps:
                mates = [b for b in g1gaps if b["color"] == a["color"]]
                if not mates:
                    continue
                b = mates[0]
                gap_d.append({
                    "color": a["color"],
                    "ddx": round(b["cx"] - a["cx"], 3),
                    "ddy": round(b["cy"] - a["cy"], 3),
                })
            row = {
                "pad_i": i,
                "x0": pad["x0"],
                "xy": list(xy),
                "body_ndiff": body_ndiff(g0, g1),
                "changes": body_changes(g0, g1),
                "deltas": deltas,
                "gap_deltas": gap_d,
                "levels": int(d.get("levels_completed") or 0),
            }
            out["pad_map"].append(row)
            moved = [x for x in deltas if abs(x["ddx"]) + abs(x["ddy"]) > 0.1]
            print(
                f"PAD[{i}] x0={pad['x0']} body={row['body_ndiff']} "
                f"spr={moved} gaps={gap_d} lv={row['levels']}"
            )
    finally:
        sess.close()
    path = ROOT / "tests" / "fixtures" / "vc33_l3_pad_map.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("saved", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
