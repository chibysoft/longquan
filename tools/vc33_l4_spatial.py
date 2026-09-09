"""One L4 enter: dump where env pads change pixels; try up+env path."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import enter_l4, gap11, sprite, summarize  # noqa: E402


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        print("start", sprite(g), gap11(g))

        def click_x(x0):
            nonlocal d, g
            pad = next(p for p in pads_sorted(g) if p["x0"] == x0)
            xy = (int(round(pad["cx"])), int(round(pad["cy"])))
            g0 = g
            d = sess.click(*xy)
            g = plane(d["frame"])
            diff = np.argwhere(g0[1:] != g[1:])
            cells = [(int(x), int(y + 1), int(g0[y + 1, x]), int(g[y + 1, x])) for y, x in diff[:40]]
            sp = sprite(g)
            print(f"x{x0} ndiff={len(diff)} lv={d.get('levels_completed')} sp={sp}")
            # bbox of changes
            if len(diff):
                ys = diff[:, 0] + 1
                xs = diff[:, 1]
                print(f"  change_bbox x[{xs.min()}-{xs.max()}] y[{ys.min()}-{ys.max()}] sample={cells[:8]}")
            return len(diff)

        # env spatial
        for x0 in (39, 45, 51, 57):
            ent = enter_l4(sess)
            d, g = ent["data"], ent["frame"]
            click_x(x0)

        # climb: 9 until stuck, 39, 9, ...
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        for i in range(30):
            sp0 = sprite(g)
            nd = click_x(9)
            sp1 = sprite(g)
            if sp0 and sp1 and abs(sp1["body"]["cy"] - sp0["body"]["cy"]) < 0.1:
                print("stuck up, try envs")
                for e in (39, 45, 51, 57):
                    click_x(e)
                    sp2 = sprite(g)
                    click_x(9)
                    sp3 = sprite(g)
                    if sp2 and sp3 and abs(sp3["body"]["cy"] - sp2["body"]["cy"]) > 0.1:
                        print("unblocked via", e)
                        break
                else:
                    # try horizontal? click all
                    print("still stuck", sprite(g), "try all pads for dx")
                    for x0 in [p["x0"] for p in pads_sorted(g)]:
                        sp_a = sprite(g)
                        click_x(x0)
                        sp_b = sprite(g)
                        if sp_a and sp_b:
                            dx = sp_b["body"]["cx"] - sp_a["body"]["cx"]
                            dy = sp_b["body"]["cy"] - sp_a["body"]["cy"]
                            if abs(dx) + abs(dy) > 0.1:
                                print(f"  MOVE x{x0} Δ=({dx},{dy})")
                    break
            if int(d.get("levels_completed") or 0) >= 4:
                print("CLEARED")
                break
            if summarize(g)["aligned"]:
                print("ALIGNED")
                break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
