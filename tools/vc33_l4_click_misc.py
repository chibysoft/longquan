"""L4: try clicking color1 / gap / non-pads; also shift c1 somehow."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import enter_l4, gap11, sprite, summarize, components  # noqa: E402
from tools.vc33_l2_probe import body_ndiff  # noqa: E402


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        print("start", summarize(g))

        targets = []
        # color1 centers
        for c in components(g, 1, min_n=4, max_n=80):
            targets.append(("c1", int(round(c["cx"])), int(round(c["cy"]))))
        gp = gap11(g)
        if gp:
            targets.append(("gap", int(round(gp["cx"])), int(round(gp["cy"]))))
        sp = sprite(g)
        if sp:
            targets.append(("body", int(round(sp["body"]["cx"])), int(round(sp["body"]["cy"]))))
            if sp.get("accent"):
                targets.append(("acc", int(round(sp["accent"]["cx"])), int(round(sp["accent"]["cy"]))))
        # empty above sprite
        targets.append(("above", 5, 35))
        # color5 beam
        targets.append(("beam", 13, 35))

        for label, x, y in targets:
            ent = enter_l4(sess)
            d, g = ent["data"], ent["frame"]
            g0 = g
            sp0 = sprite(g)
            c1_0 = components(g, 1, min_n=4, max_n=80)
            d = sess.click(x, y)
            g = plane(d["frame"])
            bd = body_ndiff(g0, g)
            sp1 = sprite(g)
            c1_1 = components(g, 1, min_n=4, max_n=80)
            ddx = (sp1["body"]["cx"] - sp0["body"]["cx"]) if sp0 and sp1 else None
            ddy = (sp1["body"]["cy"] - sp0["body"]["cy"]) if sp0 and sp1 else None
            print(f"{label} ({x},{y}) body={bd} sprΔ=({ddx},{ddy}) lv={d.get('levels_completed')}")
            if c1_0 != c1_1:
                print("  c1 CHANGED", c1_0, "->", c1_1)

        # After one up, click c1
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        pad9 = next(p for p in pads_sorted(g) if p["x0"] == 9)
        d = sess.click(int(round(pad9["cx"])), int(round(pad9["cy"])))
        g = plane(d["frame"])
        print("after one up", sprite(g))
        for c in components(g, 1, min_n=4, max_n=80):
            x, y = int(round(c["cx"])), int(round(c["cy"]))
            g0 = g
            sp0 = sprite(g)
            d = sess.click(x, y)
            g = plane(d["frame"])
            print(f"post-up click c1 ({x},{y}) body={body_ndiff(g0,g)} sp={sprite(g)} c1={components(g,1,min_n=4,max_n=80)}")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
