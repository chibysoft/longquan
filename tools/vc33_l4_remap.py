"""L4 cheap: after N downs, sequential pad scan for Δx; also wiggle up/down."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_ndiff  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import enter_l4, gap11, sprite, summarize  # noqa: E402


def scan(sess, label: str, data, grid):
    rows = []
    print(f"\n=== {label} start {summarize(grid)}")
    for pad in pads_sorted(grid):
        g0 = grid
        s0 = sprite(g0)
        d = sess.click(int(round(pad["cx"])), int(round(pad["cy"])))
        g1 = plane(d["frame"])
        s1 = sprite(g1)
        ddx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
        ddy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
        bd = body_ndiff(g0, g1)
        row = {
            "x0": pad["x0"],
            "body": bd,
            "dx": ddx,
            "dy": ddy,
            "levels": d.get("levels_completed"),
            "sp": summarize(g1)["sprite"],
        }
        rows.append(row)
        print(f"  pad{pad['x0']} body={bd} Δ=({ddx},{ddy}) lv={row['levels']} {row['sp']}")
        data, grid = d, g1
        if d.get("levels_completed", 0) >= 4:
            print("  CLEAR!")
            break
    return data, grid, rows


def main():
    key = _api_key()
    sess = Sess(key)
    out = {}
    try:
        sess.open()
        # after 1 down
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        pad15 = next(p for p in pads_sorted(g) if p["x0"] == 15)
        d = sess.click(int(round(pad15["cx"])), int(round(pad15["cy"])))
        g = plane(d["frame"])
        d, g, out["after_1_down"] = scan(sess, "after_1_down", d, g)

        # fresh: 2 downs then scan
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        for _ in range(2):
            pad15 = next(p for p in pads_sorted(g) if p["x0"] == 15)
            d = sess.click(int(round(pad15["cx"])), int(round(pad15["cy"])))
            g = plane(d["frame"])
        d, g, out["after_2_down"] = scan(sess, "after_2_down", d, g)

        # fresh: up then down then env then pads
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        for x0 in (9, 15, 39, 9, 15, 45, 9):
            pad = next(p for p in pads_sorted(g) if p["x0"] == x0)
            s0 = sprite(g)
            d = sess.click(int(round(pad["cx"])), int(round(pad["cy"])))
            g = plane(d["frame"])
            s1 = sprite(g)
            ddx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0
            ddy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0
            print(f"wiggle pad{x0} Δ=({ddx},{ddy}) {summarize(g)['sprite']} lv={d.get('levels_completed')}")
            if d.get("levels_completed", 0) >= 4:
                print("CLEAR")
                break
        out["wiggle"] = summarize(g)

        (ROOT / "tests/fixtures/vc33_l4_remap.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    finally:
        sess.close()


if __name__ == "__main__":
    main()
